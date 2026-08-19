"""Long-running Google Sheets → market data → Supabase → Telegram agent."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Event, Thread
import traceback

from loguru import logger
from supabase import create_client
import telebot

from config import get_settings
from services.google_sheets import GoogleSheetsService
from services.market_data import MarketDataService, MarketPrice
from services.sheet_signal_source import load_authoritative_sheet_signal
from services.telegram_service import TelegramService


def deliver_pending_whatsapp_signals() -> None:
    """Import WhatsApp delivery lazily to avoid a circular module import."""
    from services.production_agents import (
        deliver_pending_whatsapp_signals as deliver,
    )

    deliver()


def _active_sheet_reversal_allowed(
    *,
    sheets: GoogleSheetsService,
    market_data: MarketDataService,
    candidate: object,
) -> bool:
    """Carry active daily bias across sessions; require two-bar proof to reverse."""
    from services.sheet_reversal_guard import (
        opposite_reversal_confirmed,
        signal_identity,
    )

    identity = signal_identity(
        {"external_key": getattr(candidate, "external_key", "")}
    )
    if identity is None:
        return True

    signal_date, session_name = identity
    try:
        response = (
            market_data._supabase.table("market_signals")
            .select("*")
            .in_("signal_type", ["BUY", "SELL"])
            .like("external_key", f"gsheet-session:{signal_date}:%")
            .order("signal_time", desc=True)
            .limit(10)
            .execute()
        )
    except Exception:
        logger.exception(
            "Active Sheet direction lookup failed; opposite candidate blocked."
        )
        return False

    active = None
    terminal = {
        "STOPPED", "CLOSED", "TARGET_HIT", "CANCELLED", "EXPIRED", "TRASHED"
    }
    for row in response.data or []:
        if str(row.get("lifecycle_status") or "DRAFT").upper() in terminal:
            continue
        active = row
        break

    if active is None:
        return True

    active_direction = str(active.get("signal_type") or "").strip().upper()
    candidate_direction = str(getattr(candidate, "direction", "")).strip().upper()
    if active_direction == candidate_direction:
        return True

    try:
        values = sheets._analysis_values()
        allowed = opposite_reversal_confirmed(
            values,
            signal_date=signal_date,
            session_name=session_name,
            from_direction=active_direction,
            to_direction=candidate_direction,
            now=datetime.now(timezone.utc),
        )
    except Exception:
        logger.exception(
            "Sheet reversal verification failed; opposite candidate blocked."
        )
        return False

    if not allowed:
        logger.warning(
            "Opposite Sheet candidate blocked pending two-bar confirmation: "
            "active={} candidate={} date={} session={}",
            active_direction,
            candidate_direction,
            signal_date,
            session_name,
        )
    return allowed


def run_pipeline_once(
    sheets: GoogleSheetsService | None,
    market_data: MarketDataService,
    telegram: TelegramService,
) -> None:
    """Process Sheet enrichment, then deliver unsent Supabase signals."""
    from services.captain_ai_runtime import run_captain_read_only
    from services.captain_shadow_gate import shadow_gate_enabled
    from services.sheet_signal_risk_guard import (
        SignalRiskGuardError,
        protect_sheet_signal,
        requires_risk_guard,
    )

    captain_shadow = shadow_gate_enabled()
    inserted_signal = None
    captain_assessment = None

    if sheets is not None:
        sheet_signal = load_authoritative_sheet_signal(sheets)
        if sheet_signal and requires_risk_guard(sheet_signal):
            try:
                sheet_signal = protect_sheet_signal(
                    sheet_signal,
                    sheets._analysis_values(),
                )
            except SignalRiskGuardError as exc:
                logger.warning("Sheet signal blocked by risk guard: {}", exc)
                return
            except Exception:
                logger.exception(
                    "Sheet signal risk verification failed; candidate creation blocked."
                )
                return

        if sheet_signal and not _active_sheet_reversal_allowed(
            sheets=sheets,
            market_data=market_data,
            candidate=sheet_signal,
        ):
            sheet_signal = None

        if sheet_signal and not market_data.signal_exists(sheet_signal.external_key):
            market_price = (
                MarketPrice(
                    symbol="XAUUSD",
                    price=sheet_signal.reference_price,
                    observed_at=sheet_signal.observed_at,
                    source=sheet_signal.source,
                )
                if (
                    sheet_signal.reference_price is not None
                    and sheet_signal.observed_at is not None
                )
                else market_data.fetch_current_price()
            )
            if market_price is None:
                logger.warning("Skipping new signal because market price is unavailable")
            else:
                try:
                    captain_assessment = run_captain_read_only()
                except Exception:
                    logger.exception(
                        "Captain authority assessment failed; signal creation blocked."
                    )
                    return

                captain_decision = str(captain_assessment.decision.value)
                captain_direction = str(captain_assessment.direction.value)
                sheet_direction = str(sheet_signal.direction or "").strip().upper()

                if captain_decision != "APPROVE":
                    logger.warning(
                        "Captain blocked candidate creation: decision={} direction={} "
                        "sheet_direction={} reasons={}",
                        captain_decision,
                        captain_direction,
                        sheet_direction,
                        captain_assessment.reasons,
                    )
                    return

                if captain_direction != sheet_direction:
                    logger.warning(
                        "Captain direction mismatch; candidate blocked: captain={} sheet={}",
                        captain_direction,
                        sheet_direction,
                    )
                    return

                inserted_signal = market_data.insert_signal(
                    market_price=market_price,
                    signal_type=sheet_signal.direction,
                    target_price=sheet_signal.target_price,
                    stop_loss=sheet_signal.stop_loss,
                    sheet_label=sheet_signal.label,
                    external_key=sheet_signal.external_key,
                    targets=getattr(sheet_signal, "targets", ()),
                    target_slots=getattr(sheet_signal, "target_slots", ()),
                )

    if captain_shadow:
        if inserted_signal is not None:
            telegram.send_signal(inserted_signal, test=False)
        logger.warning(
            "Captain shadow mode active: outbound Telegram and WhatsApp signal delivery blocked."
        )
        return

    sent_count = telegram.broadcast_pending_signals()
    logger.debug("Supabase Telegram poll completed: sent={}", sent_count)

    deliver_pending_whatsapp_signals()
    logger.debug("Supabase WhatsApp poll completed")


def automation_loop(stop_event: Event) -> None:
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_key)
    market_data = MarketDataService(supabase)
    telegram = TelegramService(supabase)
    sheets: GoogleSheetsService | None = None

    logger.info(
        "Automated market signal pipeline started: interval={}s",
        settings.signal_poll_seconds,
    )
    while not stop_event.is_set():
        try:
            if sheets is None:
                try:
                    sheets = GoogleSheetsService()
                except Exception:
                    logger.exception(
                        "Google Sheets unavailable; continuing Supabase Telegram monitoring"
                    )
            run_pipeline_once(sheets, market_data, telegram)
        except Exception:
            logger.exception("Unexpected market pipeline iteration failure")
        stop_event.wait(settings.signal_poll_seconds)
    logger.info("Automated market pipeline stopped")


def _register_commands(bot: telebot.TeleBot, stop_event: Event) -> None:
    authorized_chat_id = get_settings().telegram_chat_id

    def is_authorized(message: telebot.types.Message) -> bool:
        allowed = str(message.chat.id) == str(authorized_chat_id)
        if not allowed:
            logger.warning("Rejected Telegram command from unauthorized chat {}", message.chat.id)
        return allowed

    def send_welcome(message: telebot.types.Message) -> None:
        if is_authorized(message):
            bot.reply_to(message, "AI Market Analytics Pro agent is online.")

    def handle_update(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        bot.reply_to(message, "Running market pipeline now...")
        try:
            settings = get_settings()
            supabase = create_client(settings.supabase_url, settings.supabase_key)
            try:
                sheets = GoogleSheetsService()
            except Exception:
                logger.exception("Google Sheets unavailable during manual update")
                sheets = None
            run_pipeline_once(
                sheets,
                MarketDataService(supabase),
                TelegramService(supabase),
            )
        except Exception:
            logger.exception("Manual Telegram pipeline update failed")
            bot.reply_to(message, TelegramService.SAFE_USER_ERROR)
        else:
            bot.reply_to(message, "Pipeline update completed.")

    def handle_trend(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        try:
            settings = get_settings()
            service = TelegramService(
                create_client(settings.supabase_url, settings.supabase_key)
            )
            service.send_latest_trend(str(message.chat.id))
        except Exception as exc:
            internal_traceback = traceback.format_exc()
            logger.exception("Telegram /trend command failed")
            TelegramService.record_internal_error(
                "telegram_reply_agent", exc, internal_traceback
            )
            bot.reply_to(message, TelegramService.SAFE_USER_ERROR)

    def clear_chat(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        for message_id in range(message.message_id, max(0, message.message_id - 100), -1):
            try:
                bot.delete_message(message.chat.id, message_id)
            except Exception:
                continue

    def stop_agent(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        bot.reply_to(message, "Stopping automation agent...")
        stop_event.set()
        bot.stop_polling()

    bot.register_message_handler(send_welcome, commands=["start"])
    bot.register_message_handler(handle_trend, commands=["trend"])
    bot.register_message_handler(handle_update, commands=["update_legal"])
    bot.register_message_handler(clear_chat, commands=["clear"])
    bot.register_message_handler(stop_agent, commands=["stop_agent"])


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    if not settings.telegram_chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not configured.")

    stop_event = Event()
    bot = telebot.TeleBot(settings.telegram_bot_token)
    _register_commands(bot, stop_event)
    worker = Thread(
        target=automation_loop,
        args=(stop_event,),
        name="market-signal-pipeline",
        daemon=True,
    )
    worker.start()

    logger.info("Telegram command listener started")
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception:
        logger.exception("Telegram polling stopped unexpectedly")
        raise
    finally:
        stop_event.set()
        worker.join(timeout=10)
        logger.info("Agent shutdown complete")


if __name__ == "__main__":
    main()
