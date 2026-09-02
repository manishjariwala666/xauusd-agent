"""Best-effort Telegram mirror for terminal ADMIN signal lifecycle actions."""

from __future__ import annotations

from typing import Any

from loguru import logger

from services.telegram_service import TelegramService


TERMINAL_TELEGRAM_ACTIONS = {"CANCEL", "CLOSE"}


def format_admin_terminal_lifecycle_message(
    signal: dict[str, Any],
    *,
    action: str,
) -> str:
    """Render a concise canonical terminal-state message from the saved signal row."""
    clean_action = str(action or "").strip().upper()
    if clean_action not in TERMINAL_TELEGRAM_ACTIONS:
        raise ValueError("Unsupported terminal Telegram lifecycle action.")

    symbol = str(signal.get("symbol") or "XAUUSD").strip().upper()
    status = "CANCELLED" if clean_action == "CANCEL" else "CLOSED"
    marker = "🚫" if clean_action == "CANCEL" else "✅"
    lines = [
        f"{marker} {symbol} SIGNAL {status}",
        f"Status: {status}",
    ]

    timeframe = str(signal.get("timeframe") or "").strip()
    if timeframe:
        lines.append(f"Timeframe: {timeframe}")

    outcome = str(signal.get("outcome") or "").strip()
    if outcome and outcome.upper() != status:
        lines.append(f"Outcome: {outcome}")

    result_points = signal.get("result_points")
    if result_points not in (None, ""):
        lines.append(f"Result: {result_points} points")

    public_id = str(signal.get("public_id") or "").strip()
    if public_id:
        lines.append(f"Signal ID: {public_id}")

    lines.append("Canonical status updated on VenusRealm.")
    return "\n".join(lines)


def deliver_admin_terminal_lifecycle_telegram(
    signal: dict[str, Any],
    *,
    action: str,
) -> bool:
    """Mirror CANCEL/CLOSE after the canonical DB transition has committed.

    Delivery is deliberately best-effort: a Telegram transport outage must not
    roll back or falsify an already-committed canonical lifecycle state.
    """
    clean_action = str(action or "").strip().upper()
    if clean_action not in TERMINAL_TELEGRAM_ACTIONS:
        return False

    try:
        telegram = TelegramService()
        chat_id = str(getattr(telegram, "_chat_id", "") or "").strip()
        if not chat_id:
            logger.warning(
                "Admin terminal Telegram mirror unavailable: signal_id={} action={} reason=no_chat_id",
                signal.get("id"),
                clean_action,
            )
            return False
        telegram.send_text(
            chat_id,
            format_admin_terminal_lifecycle_message(signal, action=clean_action),
        )
    except Exception as exc:
        logger.warning(
            "Admin terminal Telegram mirror failed closed-to-delivery: signal_id={} action={} category={}",
            signal.get("id"),
            clean_action,
            exc.__class__.__name__,
        )
        return False

    logger.info(
        "Admin terminal Telegram mirror delivered: signal_id={} action={}",
        signal.get("id"),
        clean_action,
    )
    return True
