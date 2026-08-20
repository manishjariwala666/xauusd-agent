"""Pure helpers for detecting XAUUSD target hits."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class TargetMilestone:
    """One valid, sequential profit milestone for a signal."""

    number: int
    source_slot: int
    price: Decimal


def actionable_target_milestones(
    signal: dict[str, Any],
) -> list[TargetMilestone]:
    """Return directionally valid targets without changing Sheet numbering.

    Canonical Google-Sheet session signals are six-target strategies: Target 1
    through Target 5 are progress milestones and Target 6 is the only target
    completion milestone. Therefore all six numbered targets must be present,
    unique and directionally sequential for a canonical ``gsheet-session:``
    signal. Legacy/non-canonical signals keep the historical permissive fallback.
    """
    direction = str(signal.get("signal_type") or "").strip().upper()
    entry_value = signal.get("price")
    if direction not in {"BUY", "SELL"} or entry_value in (None, ""):
        return []

    entry = Decimal(str(entry_value))
    external_key = str(signal.get("external_key") or "").strip()
    requires_six_targets = external_key.startswith("gsheet-session:")
    milestones: list[TargetMilestone] = []
    seen: set[Decimal] = set()
    previous = entry

    has_numbered_targets = any(
        signal.get(f"target_{slot}") not in (None, "")
        for slot in range(1, 7)
    )

    for source_slot in range(1, 7):
        value = signal.get(f"target_{source_slot}")
        if value in (None, ""):
            if requires_six_targets or (source_slot == 1 and has_numbered_targets):
                return []
            continue

        try:
            target = Decimal(str(value))
        except Exception:
            if requires_six_targets or source_slot == 1:
                return []
            continue

        if target in seen:
            if requires_six_targets or source_slot == 1:
                return []
            continue

        is_valid = (
            target > entry and target > previous
            if direction == "BUY"
            else target < entry and target < previous
        )
        if not is_valid:
            if requires_six_targets or source_slot == 1:
                return []
            continue

        seen.add(target)
        previous = target
        milestones.append(
            TargetMilestone(
                number=source_slot,
                source_slot=source_slot,
                price=target,
            )
        )

    if requires_six_targets:
        if [item.number for item in milestones] != [1, 2, 3, 4, 5, 6]:
            return []
        return milestones

    if not has_numbered_targets and not milestones:
        fallback = signal.get("target_price")
        if fallback not in (None, ""):
            target = Decimal(str(fallback))
            if (
                direction == "BUY" and target > entry
            ) or (
                direction == "SELL" and target < entry
            ):
                milestones.append(TargetMilestone(1, 0, target))

    return milestones


def reached_target_milestones(
    signal: dict[str, Any],
    current_price: Decimal,
) -> list[TargetMilestone]:
    """Return all sequential milestones reached by the current quote."""
    direction = str(signal.get("signal_type") or "").strip().upper()
    milestones = actionable_target_milestones(signal)
    if direction == "BUY":
        return [item for item in milestones if current_price >= item.price]
    if direction == "SELL":
        return [item for item in milestones if current_price <= item.price]
    return []


def milestone_profit_points(
    signal: dict[str, Any],
    milestone: TargetMilestone,
) -> Decimal:
    """Return positive entry-to-milestone distance."""
    direction = str(signal.get("signal_type") or "").strip().upper()
    entry = Decimal(str(signal["price"]))
    if direction == "BUY":
        return milestone.price - entry
    if direction == "SELL":
        return entry - milestone.price
    raise ValueError("Signal direction must be BUY or SELL.")


def format_target_progress_message(
    signal: dict[str, Any],
    milestone: TargetMilestone,
    *,
    next_milestone: TargetMilestone | None,
    achieved_price: Decimal,
) -> str:
    """Build a factual target-progress message without implying early exit."""
    direction = str(signal["signal_type"]).strip().upper()
    symbol = str(signal.get("symbol") or "XAUUSD").strip().upper()
    entry = Decimal(str(signal["price"]))
    points = milestone_profit_points(signal, milestone)

    lines = [
        f"🎯 Yahooo — Target {milestone.number} achieved — {symbol} {direction} ✅",
        "",
        f"Entry: {entry:.2f}",
        f"Target {milestone.number}: {milestone.price:.2f}",
        f"Observed price: {achieved_price:.2f}",
        f"Move from entry: +{points:.2f} points",
        "",
    ]
    if next_milestone is not None:
        lines.extend(
            [
                f"⏳ Target {next_milestone.number} coming: {next_milestone.price:.2f}",
                "Signal remains active toward the next configured target unless the separate stop/reversal rule closes it.",
            ]
        )
    else:
        lines.append("🏁 Target 6 achieved — all configured targets completed.")

    lines.extend(
        [
            "",
            "Market analysis only; returns are not guaranteed.",
            "",
            "— VenusRealm",
        ]
    )
    return "\n".join(lines)


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
    distance = entry - stop_loss if direction == "BUY" else stop_loss - entry
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
