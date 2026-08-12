"""Shared English signal and service-status messages."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


WEEKEND_MESSAGE = (
    "🎉 Enjoy Your Weekend\n\n"
    "Markets are closed on Saturday and Sunday.\n\n"
    "Enjoy your weekend with profits, family and happy travelling.\n\n"
    "— VenusRealm"
)

MAINTENANCE_MESSAGE = (
    "🛠️ VenusRealm System Maintenance\n\n"
    "Our services are temporarily under scheduled maintenance.\n\n"
    "Signal delivery and support responses may be delayed during this period. "
    "We are working to restore all services as quickly as possible.\n\n"
    "Thank you for your patience.\n\n"
    "— VenusRealm"
)

BACK_ONLINE_MESSAGE = (
    "✅ VenusRealm Is Back Online\n\n"
    "System maintenance has been completed successfully.\n\n"
    "Signal delivery and support services are now operating normally.\n\n"
    "Thank you for your patience.\n\n"
    "— VenusRealm"
)


def _price(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        decimal = Decimal(str(value))
    except Exception:
        return str(value)
    rendered = f"{decimal:.2f}"
    return rendered.rstrip("0").rstrip(".")


def _price_fixed(value: Any) -> str:
    """Return legacy-compatible comma-separated price formatting."""
    if value in (None, ""):
        return "—"
    try:
        return f"{Decimal(str(value)):,.2f}"
    except Exception:
        return str(value)


def _time(value: Any) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime(
            "%d %b %Y · %H:%M UTC"
        )
    except ValueError:
        return str(value)


def signal_targets(signal: dict[str, Any]) -> list[Any]:
    from services.signal_target_monitor import actionable_target_milestones

    targets = [
        milestone.price
        for milestone in actionable_target_milestones(signal)
    ]

    if not targets:
        fallback = signal.get("target_price")
        if fallback not in (None, ""):
            targets.append(fallback)

    return targets


def format_signal_message(signal: dict[str, Any], *, test: bool = False) -> str:
    from services.signal_target_monitor import actionable_target_milestones

    direction = str(signal.get("signal_type") or "").strip().upper()
    icon = "🟢" if direction == "BUY" else "🔴"
    test_label = "TEST · " if test else ""
    milestones = actionable_target_milestones(signal)
    targets = [milestone.price for milestone in milestones]

    lines = [
        f"{icon} {test_label}XAUUSD {direction}",
        "",
        f"Entry: {_price(signal.get('price'))}",
        f"Time: {_time(signal.get('signal_time') or signal.get('updated_at'))}",
        "",
        (
            "Targets: "
            + (
                ", ".join(_price_fixed(target) for target in targets)
                if targets
                else "—"
            )
        ),
    ]

    for milestone in milestones:
        lines.append(
            f"🎯 Target {milestone.number}: {_price(milestone.price)}"
        )

    if milestones:
        first = milestones[0]
        lines.append(
            f"⏳ Target {first.number} coming: {_price(first.price)}"
        )

    if not targets:
        lines.append("🎯 Targets: —")

    lines.extend(
        [
            "",
            f"🛑 Stop Loss: {_price(signal.get('stop_loss'))}",
        ]
    )

    if signal.get("timeframe"):
        lines.append(f"⏱️ Timeframe: {signal['timeframe']}")
    if signal.get("risk_level"):
        lines.append(f"⚠️ Risk: {signal['risk_level']}")
    if signal.get("sheet_label"):
        lines.append(f"📄 Sheet Label: {signal['sheet_label']}")

    lines.extend(
        [
            "",
            "Manage risk carefully. This is market analysis, "
            "not guaranteed financial advice.",
            "",
            "— VenusRealm",
        ]
    )
    return "\n".join(lines)
