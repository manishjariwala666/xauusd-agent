"""Safe reference market-data reader for VenusRealm Master AI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


SUPPORTED_SYMBOLS = {
    "XAUUSD",
}

ALLOWED_SOURCES = {
    "GOOGLE_FINANCE",
    "GOOGLE_FINANCE_SHEET",
    "GOOGLE_SHEET",
    "MT5",
    "BROKER_FEED",
}

LIVE_SOURCES = {
    "MT5",
    "BROKER_FEED",
}

REFERENCE_SOURCES = {
    "GOOGLE_FINANCE",
    "GOOGLE_FINANCE_SHEET",
    "GOOGLE_SHEET",
}


def _clean(value: object, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def _parse_timestamp(value: object) -> datetime:
    raw = _clean(value, 100)

    if not raw:
        raise ValueError("Market-data timestamp is required.")

    try:
        parsed = datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            "Market-data timestamp must be valid ISO-8601."
        ) from exc

    if parsed.tzinfo is None:
        raise ValueError(
            "Market-data timestamp must include timezone."
        )

    return parsed.astimezone(timezone.utc)


def _parse_price(value: object) -> Decimal:
    raw = _clean(value, 100).replace(",", "")

    if not raw or raw.upper() in {
        "N/A",
        "#N/A",
        "UNAVAILABLE",
        "ERROR",
        "NULL",
        "NONE",
    }:
        raise ValueError("Market price is unavailable.")

    try:
        price = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(
            "Market price must be numeric."
        ) from exc

    if price <= 0:
        raise ValueError(
            "Market price must be greater than zero."
        )

    return price


def build_market_snapshot(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate one market snapshot without generating any signal."""
    symbol = _clean(
        payload.get("symbol") or "XAUUSD",
        30,
    ).upper()

    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(
            f"Unsupported market symbol: {symbol}."
        )

    source = _clean(
        payload.get("source"),
        80,
    ).upper().replace(" ", "_")

    if source not in ALLOWED_SOURCES:
        raise ValueError(
            "A supported market-data source is required."
        )

    timestamp = _parse_timestamp(
        payload.get("updated_at")
        or payload.get("timestamp")
    )

    current_time = (
        now.astimezone(timezone.utc)
        if now is not None
        else datetime.now(timezone.utc)
    )

    age_seconds = max(
        0,
        int((current_time - timestamp).total_seconds()),
    )

    max_age_seconds = int(
        payload.get("max_age_seconds") or 1200
    )
    max_age_seconds = max(30, min(max_age_seconds, 3600))

    if timestamp > current_time:
        raise ValueError(
            "Market-data timestamp cannot be in the future."
        )

    if age_seconds > max_age_seconds:
        raise PermissionError(
            "Market data is stale and cannot be presented as current."
        )

    price = _parse_price(
        payload.get("price")
        or payload.get("last_price")
    )

    bid_raw = payload.get("bid")
    ask_raw = payload.get("ask")

    bid = (
        _parse_price(bid_raw)
        if bid_raw not in {None, ""}
        else None
    )
    ask = (
        _parse_price(ask_raw)
        if ask_raw not in {None, ""}
        else None
    )

    if bid is not None and ask is not None and ask < bid:
        raise ValueError(
            "Ask price cannot be lower than bid price."
        )

    spread = (
        ask - bid
        if bid is not None and ask is not None
        else None
    )

    data_class = (
        "LIVE_BROKER_DATA"
        if source in LIVE_SOURCES
        else "REFERENCE_DATA"
    )

    label = (
        "Live broker price"
        if source in LIVE_SOURCES
        else "Google Finance reference price"
    )

    return {
        "status": "AVAILABLE",
        "symbol": symbol,
        "price": str(price),
        "bid": str(bid) if bid is not None else None,
        "ask": str(ask) if ask is not None else None,
        "spread": (
            str(spread)
            if spread is not None
            else None
        ),
        "source": source,
        "source_label": label,
        "data_class": data_class,
        "updated_at": timestamp.isoformat(),
        "age_seconds": age_seconds,
        "fresh": True,
        "signal_generated": False,
        "trading_advice_generated": False,
        "execution_started": False,
        "safe_summary": (
            f"{symbol} verified {label.lower()} is available. "
            "No signal or trading recommendation was generated."
        ),
    }


def run_market_data_agent(
    payload: dict[str, Any],
) -> str:
    """Return verified market reference data only."""
    forbidden_flags = (
        "generate_signal",
        "give_signal",
        "recommend_trade",
        "place_trade",
        "send_telegram",
        "send_whatsapp",
        "publish_price",
        "modify_google_sheet",
    )

    for flag in forbidden_flags:
        if payload.get(flag) is True:
            raise PermissionError(
                f"Market Data Agent cannot execute {flag}."
            )

    result = build_market_snapshot(payload)

    return json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
    )
