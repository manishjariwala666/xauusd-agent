"""Telegram delivery for pending Supabase market signals."""

from __future__ import annotations

from datetime import datetime, timezone
import html
from threading import Event
from typing import Any

from loguru import logger
from supabase import Client, create_client
import telebot

from config import get_settings


class TelegramConfigurationError(RuntimeError):
    """Raised when Telegram delivery settings are missing."""


class TelegramService:
    """Format, deliver, and persist Telegram signal delivery state."""

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
        return "\n".join(
            (
                f"<b>{icon} {heading}XAUUSD {html.escape(direction)}</b>",
                "",
                f"<b>Price:</b> {TelegramService._value(signal.get('price'))}",
                f"<b>Time:</b> {html.escape(observed_at)}",
                (
                    "<b>Target:</b> "
                    f"{TelegramService._value(signal.get('target_price'))}"
                ),
                (
                    "<b>Stop Loss:</b> "
                    f"{TelegramService._value(signal.get('stop_loss'))}"
                ),
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
            )
        )

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
    def _value(value: Any) -> str:
        if value in (None, ""):
            return "—"
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return html.escape(str(value))
