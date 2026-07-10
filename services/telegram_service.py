"""Telegram delivery for pending Supabase market signals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import html
import re
from threading import Event
import traceback
from typing import Any

from loguru import logger
from sqlalchemy import text
from supabase import Client, create_client
import telebot

from config import get_settings
from core.database import session_scope
from services.google_sheets_service import append_public_signal_log


class TelegramConfigurationError(RuntimeError):
    """Raised when Telegram delivery settings are missing."""


class TelegramService:
    """Format, deliver, and persist Telegram signal delivery state."""

    SAFE_USER_ERROR = (
        "⚠️ Service temporarily unavailable. Please try again later."
    )
    _TREND_MAX_AGE = timedelta(hours=6)

    def __init__(self, supabase: Client | None = None) -> None:
        settings = get_settings()
        if not settings.telegram_bot_token:
            raise TelegramConfigurationError(
                "TELEGRAM_BOT_TOKEN is not configured."
            )
        if not settings.telegram_chat_id:
            raise TelegramConfigurationError(
                "TELEGRAM_CHAT_ID is not configured."
            )
        self._bot = telebot.TeleBot(
            settings.telegram_bot_token,
            parse_mode="HTML",
        )
        self._chat_id = settings.telegram_chat_id
        self._poll_seconds = settings.signal_poll_seconds
        self._supabase = supabase or create_client(
            settings.supabase_url,
            settings.supabase_key,
        )

    def broadcast_pending_signals(self, limit: int = 50) -> int:
        """Send unsent BUY/SELL rows and return successful delivery count."""
        try:
            response = (
                self._supabase.table("market_signals")
                .select("*")
                .in_("signal_type", ["BUY", "SELL"])
                .is_("telegram_sent_at", "null")
                .order("updated_at")
                .limit(limit)
                .execute()
            )
        except Exception:
            logger.exception("Unable to load pending Telegram signals")
            return 0

        sent_count = 0
        for signal in response.data or []:
            if self.send_signal(signal):
                sent_count += 1
        if sent_count:
            logger.info("Telegram delivery batch completed: sent={}", sent_count)
        return sent_count

    def send_signal(self, signal: dict[str, Any], test: bool = False) -> bool:
        """Send one formatted signal through the configured Telegram bot."""
        signal_id = signal.get("id")
        try:
            message = self._bot.send_message(
                self._chat_id,
                self.format_message(signal, test=test),
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.exception(
                "Telegram signal delivery failed: id={}",
                signal_id,
            )
            if signal_id is not None and not test:
                self._record_failure(signal_id, str(exc))
            return False

        if signal_id is not None and not test:
            try:
                (
                    self._supabase.table("market_signals")
                    .update(
                        {
                            "telegram_sent_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                            "telegram_message_id": str(message.message_id),
                            "delivery_error": None,
                        }
                    )
                    .eq("id", signal_id)
                    .execute()
                )
            except Exception:
                logger.exception(
                    "Telegram sent but delivery state update failed: id={}",
                    signal_id,
                )
                return False

        logger.info(
            "Telegram signal delivered: id={} message_id={} test={}",
            signal_id,
            message.message_id,
            test,
        )
        append_public_signal_log(
            status="test_sent" if test else "sent",
            message_id=str(message.message_id),
            direction=str(signal.get("signal_type") or ""),
            entry=signal.get("price") or "",
            target_1=signal.get("target_1") or signal.get("target_price") or "",
            target_2=signal.get("target_2") or "",
            target_3=signal.get("target_3") or "",
            stop_loss=signal.get("stop_loss") or "",
            notes=f"signal_id={signal_id or ''}",
        )
        return True

    def send_test_signal(self, signal: dict[str, Any]) -> bool:
        """Verify connectivity using the production formatter and sender."""
        return self.send_signal(signal, test=True)

    def send_text(self, chat_id: str, message: str) -> str:
        """Send an escaped plain-text reply to one Telegram conversation."""
        delivered = self._bot.send_message(
            chat_id,
            html.escape(message[:4096]),
            disable_web_page_preview=True,
        )
        return str(delivered.message_id)

    def send_latest_trend(self, chat_id: str) -> bool:
        """Send only the newest valid and sufficiently fresh XAUUSD signal."""
        signal = self.get_latest_valid_signal()
        if signal is None:
            self.send_text(chat_id, self.SAFE_USER_ERROR)
            return False
        self._bot.send_message(
            chat_id,
            self.format_message(signal),
            disable_web_page_preview=True,
        )
        return True

    def get_latest_valid_signal(self) -> dict[str, Any] | None:
        """Load recent candidates and reject malformed, future, or stale rows."""
        response = (
            self._supabase.table("market_signals")
            .select("*")
            .in_("signal_type", ["BUY", "SELL"])
            .order("signal_time", desc=True)
            .order("updated_at", desc=True)
            .limit(25)
            .execute()
        )
        return self.select_latest_valid_signal(
            list(response.data or []),
            now=datetime.now(timezone.utc),
            max_age=self._TREND_MAX_AGE,
        )

    @staticmethod
    def select_latest_valid_signal(
        signals: list[dict[str, Any]],
        *,
        now: datetime,
        max_age: timedelta,
    ) -> dict[str, Any] | None:
        """Choose the newest valid row without ever falling back to stale data."""
        normalized_now = (
            now.replace(tzinfo=timezone.utc)
            if now.tzinfo is None
            else now.astimezone(timezone.utc)
        )
        valid: list[tuple[datetime, dict[str, Any]]] = []
        for signal in signals:
            direction = str(signal.get("signal_type") or "").upper()
            if direction not in {"BUY", "SELL"}:
                continue
            try:
                price = float(signal.get("price"))
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue
            observed_at = TelegramService._parse_time(
                signal.get("signal_time") or signal.get("updated_at")
            )
            if observed_at is None:
                continue
            age = normalized_now - observed_at
            if age < timedelta(minutes=-5) or age > max_age:
                continue
            valid.append((observed_at, signal))
        if not valid:
            return None
        valid.sort(key=lambda item: item[0], reverse=True)
        return valid[0][1]

    @staticmethod
    def record_internal_error(
        agent_key: str,
        exc: BaseException,
        traceback_text: str | None = None,
    ) -> None:
        """Persist an admin-only summary and traceback for operational review."""
        summary = TelegramService._admin_error_summary(exc)
        internal_traceback = (
            traceback_text or traceback.format_exc()
        ).strip()
        if not internal_traceback or internal_traceback == "NoneType: None":
            internal_traceback = f"{exc.__class__.__name__}: {exc}"
        try:
            with session_scope() as session:
                agent_id = session.execute(
                    text(
                        """
                        UPDATE public.ai_agents
                        SET status = 'ERROR', last_error = :summary,
                            last_run_at = NOW(),
                            failure_count = failure_count + 1,
                            updated_at = NOW()
                        WHERE agent_key = :agent_key
                        RETURNING id
                        """
                    ),
                    {"agent_key": agent_key, "summary": summary},
                ).scalar_one_or_none()
                if agent_id is not None:
                    session.execute(
                        text(
                            """
                            INSERT INTO public.ai_agent_runs (
                                agent_id, status, trigger_type, finished_at,
                                error_message, result_summary
                            ) VALUES (
                                :agent_id, 'ERROR', 'TELEGRAM_COMMAND', NOW(),
                                :traceback, :summary
                            )
                            """
                        ),
                        {
                            "agent_id": agent_id,
                            "traceback": internal_traceback[:8_000],
                            "summary": summary,
                        },
                    )
        except Exception:
            logger.exception("Unable to persist Telegram command failure")

    def monitor_forever(self, stop_event: Event | None = None) -> None:
        """Continuously poll Supabase while isolating transient failures."""
        event = stop_event or Event()
        logger.info(
            "Telegram market signal monitor started: interval={}s",
            self._poll_seconds,
        )
        while not event.is_set():
            try:
                self.broadcast_pending_signals()
            except Exception:
                logger.exception("Unexpected Telegram monitor iteration failure")
            event.wait(self._poll_seconds)
        logger.info("Telegram market signal monitor stopped")

    @staticmethod
    def format_message(
        signal: dict[str, Any],
        test: bool = False,
    ) -> str:
        """Return a clear HTML Telegram signal message."""
        direction = str(signal.get("signal_type", "")).upper()
        icon = "🟢" if direction == "BUY" else "🔴"
        heading = "TEST · " if test else ""
        observed_at = TelegramService._format_time(
            signal.get("signal_time") or signal.get("updated_at")
        )
        targets = [
            TelegramService._value(
                signal.get(key)
                or (signal.get("target_price") if key == "target_1" else None)
            )
            for key in ("target_1", "target_2", "target_3")
            if signal.get(key)
            or (key == "target_1" and signal.get("target_price"))
        ]
        lines = [
            f"<b>{icon} {heading}XAUUSD {html.escape(direction)}</b>",
            "",
            f"<b>Entry:</b> {TelegramService._value(signal.get('price'))}",
            f"<b>Time:</b> {html.escape(observed_at)}",
            f"<b>Targets:</b> {html.escape(', '.join(targets) or '—')}",
            f"<b>Stop Loss:</b> {TelegramService._value(signal.get('stop_loss'))}",
        ]
        if signal.get("risk_level"):
            lines.append(
                f"<b>Risk:</b> {html.escape(str(signal.get('risk_level')))}"
            )
        if signal.get("timeframe"):
            lines.append(
                f"<b>Timeframe:</b> {html.escape(str(signal.get('timeframe')))}"
            )
        if signal.get("note"):
            lines.append(f"<b>Note:</b> {html.escape(str(signal.get('note')))}")
        lines.extend(
            [
                (
                    "<b>Sheet Label:</b> "
                    f"{html.escape(str(signal.get('sheet_label') or '—'))}"
                ),
                (
                    "<b>Source:</b> "
                    f"{html.escape(str(signal.get('source') or '—'))}"
                ),
                "",
                "<i>Manage risk carefully. This is market analysis, "
                "not guaranteed financial advice.</i>",
            ]
        )
        return "\n".join(lines)

    def _record_failure(self, signal_id: Any, error: str) -> None:
        try:
            (
                self._supabase.table("market_signals")
                .update({"delivery_error": error[:1000]})
                .eq("id", signal_id)
                .execute()
            )
        except Exception:
            logger.exception(
                "Unable to persist Telegram delivery error: id={}",
                signal_id,
            )

    @staticmethod
    def _format_time(value: Any) -> str:
        if not value:
            return datetime.now(timezone.utc).strftime(
                "%d %b %Y · %H:%M UTC"
            )
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
            return parsed.astimezone(timezone.utc).strftime(
                "%d %b %Y · %H:%M UTC"
            )
        except ValueError:
            return str(value)

    @staticmethod
    def _parse_time(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _admin_error_summary(exc: BaseException) -> str:
        """Create a bounded summary without URLs, paths, or secret-like data."""
        message = str(exc).splitlines()[0].strip()
        message = re.sub(r"https?://\S+", "[redacted-url]", message)
        message = re.sub(
            r"(?:[A-Za-z]:)?[/\\][\w./\\-]+",
            "[redacted-path]",
            message,
        )
        message = re.sub(
            r"(?i)(token|secret|password|api[_ -]?key)\s*[=:]\s*\S+",
            r"\1=[redacted]",
            message,
        )
        summary = f"{exc.__class__.__name__}: {message or 'Command failed'}"
        return summary[:500]

    @staticmethod
    def _value(value: Any) -> str:
        if value in (None, ""):
            return "—"
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return html.escape(str(value))
