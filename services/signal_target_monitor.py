"""Pure helpers for detecting XAUUSD target hits."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def target_is_hit(signal: dict[str, Any], current_price: Decimal) -> bool:
    """Return True when the current quote has reached the signal target."""
    direction = str(signal.get("signal_type") or "").upper()
    target_value = signal.get("target_price")

    if direction not in {"BUY", "SELL"} or target_value is None:
        return False

    target = Decimal(str(target_value))

    if direction == "BUY":
        return current_price >= target

    return current_price <= target


def profit_points(signal: dict[str, Any]) -> Decimal:
    """Calculate positive target distance in XAUUSD points."""
    direction = str(signal.get("signal_type") or "").upper()
    entry_value = signal.get("price")
    target_value = signal.get("target_price")

    if direction not in {"BUY", "SELL"}:
        raise ValueError("Signal direction must be BUY or SELL.")
    if entry_value is None or target_value is None:
        raise ValueError("Signal entry and target are required.")

    entry = Decimal(str(entry_value))
    target = Decimal(str(target_value))

    return target - entry if direction == "BUY" else entry - target


def format_target_hit_message(signal: dict[str, Any]) -> str:
    """Build the approved VenusRealm WhatsApp target-hit message."""
    direction = str(signal["signal_type"]).upper()
    symbol = str(signal.get("symbol") or "XAUUSD").upper()
    entry = Decimal(str(signal["price"]))
    target = Decimal(str(signal["target_price"]))
    points = profit_points(signal)

    return (
        "🎯 Yahooo VenusRealm TARGET HIT ✅\n\n"
        f"{symbol} {direction}\n"
        f"Entry: {entry:.2f}\n"
        f"Target: {target:.2f}\n"
        f"Profit: +{points:.2f} points 🟢\n\n"
        "🎉 Enjoy Profit! 🥳💚"
    )


def stop_loss_is_hit(
    signal: dict[str, Any],
    current_price: Decimal,
) -> bool:
    """Return True when the live quote has crossed the signal stop loss."""
    direction = str(signal.get("signal_type") or "").strip().upper()
    stop_value = signal.get("stop_loss")

    if direction not in {"BUY", "SELL"} or stop_value is None:
        return False

    stop_loss = Decimal(str(stop_value))

    if direction == "BUY":
        return current_price <= stop_loss

    return current_price >= stop_loss


def loss_points(signal: dict[str, Any]) -> Decimal:
    """Return the positive distance between entry and stop loss."""
    direction = str(signal.get("signal_type") or "").strip().upper()
    entry_value = signal.get("price")
    stop_value = signal.get("stop_loss")

    if direction not in {"BUY", "SELL"}:
        raise ValueError("Signal direction must be BUY or SELL.")
    if entry_value is None or stop_value is None:
        raise ValueError("Signal entry and stop loss are required.")

    entry = Decimal(str(entry_value))
    stop_loss = Decimal(str(stop_value))

    distance = (
        entry - stop_loss
        if direction == "BUY"
        else stop_loss - entry
    )
    return abs(distance)


def format_stop_loss_hit_message(signal: dict[str, Any]) -> str:
    """Build the approved VenusRealm stop-loss closure message."""
    direction = str(signal["signal_type"]).strip().upper()
    symbol = str(signal.get("symbol") or "XAUUSD").strip().upper()
    entry = Decimal(str(signal["price"]))
    stop_loss = Decimal(str(signal["stop_loss"]))
    points = loss_points(signal)

    return (
        f"🔴 STOP LOSS HIT — {symbol} {direction}\n\n"
        f"Entry: {entry:.2f}\n"
        f"Stop Loss: {stop_loss:.2f}\n"
        f"Result: -{points:.2f} points\n\n"
        "This signal is now closed.\n"
        "Please wait for the next confirmed setup.\n\n"
        "— VenusRealm"
    )
