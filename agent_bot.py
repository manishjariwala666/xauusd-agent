"""Long-running Google Sheets → market data → Supabase → Telegram agent."""

from __future__ import annotations

from threading import Event, Thread
import traceback

from loguru import logger
from supabase import create_client
import telebot

from config import get_settings
from services.google_sheets import GoogleSheetsService
from services.market_data import MarketDataService, MarketPrice
from services.telegram_service import TelegramService


def run_pipeline_once(
    sheets: GoogleSheetsService | None,
    market_data: MarketDataService,
    telegram: TelegramService,
) -> None:
    """Process Sheet enrichment, then deliver unsent Supabase signals."""
    if sheets is not None:
        sheet_signal = sheets.get_latest_signal()
        if sheet_signal and not market_data.signal_exists(
            sheet_signal.external_key
        ):
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
                logger.warning(
                    "Skipping new signal because market price is unavailable"
                )
            else:
                market_data.insert_signal(
                    market_price=market_price,
                    signal_type=sheet_signal.direction,
                    target_price=sheet_signal.target_price,
                    stop_loss=sheet_signal.stop_loss,
                    sheet_label=sheet_signal.label,
                    external_key=sheet_signal.external_key,
                )

    # TelegramService queries only BUY/SELL rows where telegram_sent_at is
    # NULL, and stores telegram_sent_at + telegram_message_id after delivery.
    # This persistent database state prevents duplicate messages on restart.
    sent_count = telegram.broadcast_pending_signals()
    logger.debug("Supabase Telegram poll completed: sent={}", sent_count)


def automation_loop(stop_event: Event) -> None:
    """Run the pipeline continuously while isolating transient API errors."""
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
                        "Google Sheets unavailable; continuing Supabase "
                        "Telegram monitoring"
                    )
            run_pipeline_once(sheets, market_data, telegram)
        except Exception:
            logger.exception("Unexpected market pipeline iteration failure")
        stop_event.wait(settings.signal_poll_seconds)
    logger.info("Automated market signal pipeline stopped")


def _register_commands(
    bot: telebot.TeleBot,
    stop_event: Event,
) -> None:
    """Preserve operational bot commands without exposing private data."""
    authorized_chat_id = get_settings().telegram_chat_id

    def is_authorized(message: telebot.types.Message) -> bool:
        allowed = str(message.chat.id) == str(authorized_chat_id)
        if not allowed:
            logger.warning(
                "Rejected Telegram command from unauthorized chat {}",
                message.chat.id,
            )
        return allowed

    def send_welcome(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        bot.reply_to(message, "AI Market Analytics Pro agent is online.")

    def handle_update(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        bot.reply_to(message, "Running market pipeline now...")
        try:
            settings = get_settings()
            supabase = create_client(
                settings.supabase_url,
                settings.supabase_key,
            )
            try:
                sheets = GoogleSheetsService()
            except Exception:
                logger.exception(
                    "Google Sheets unavailable during manual update"
                )
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
        """Return only a fresh persisted signal and conceal internal failures."""
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
                "telegram_reply_agent",
                exc,
                internal_traceback,
            )
            bot.reply_to(message, TelegramService.SAFE_USER_ERROR)

    def clear_chat(message: telebot.types.Message) -> None:
        if not is_authorized(message):
            return
        for message_id in range(
            message.message_id,
            max(0, message.message_id - 100),
            -1,
        ):
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
    """Start the market pipeline and Telegram command listener."""
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
        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30,
        )
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
