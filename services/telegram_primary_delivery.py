"""Durable Captain-verified Telegram delivery for primary market signals."""

from __future__ import annotations

from typing import Any

from loguru import logger

from services.captain_shadow_gate import evaluate_signal_shadow_gate
from services.signal_channel_delivery import deliver_pending_signal_recipients


def deliver_pending_telegram_signals(telegram: Any) -> tuple[int, int]:
    """Deliver pending Telegram signals with the shared durable contract.

    Uses the same per-recipient claim/retry state as WhatsApp and the same
    Captain/Shadow verification semantics. The existing Telegram formatter and
    bot client remain authoritative for message rendering and transport.
    """

    chat_id = str(getattr(telegram, "_chat_id", "") or "").strip()
    bot = getattr(telegram, "_bot", None)
    if not chat_id or bot is None:
        logger.warning("Telegram durable delivery unavailable: transport not configured")
        return 0, 0

    def verify(signal: dict[str, Any]) -> tuple[bool, str]:
        gate = evaluate_signal_shadow_gate(signal)
        if gate.blocked:
            return False, gate.reason
        return True, gate.reason

    def send(recipient: str, message: str) -> str:
        delivered = bot.send_message(
            recipient,
            message,
            disable_web_page_preview=True,
        )
        return str(delivered.message_id)

    return deliver_pending_signal_recipients(
        channel="telegram",
        recipients=(chat_id,),
        send=send,
        format_message=lambda signal: telegram.format_message(signal),
        max_attempts=3,
        verify_signal=verify,
    )
