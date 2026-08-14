"""Read-only Yahoo Finance provider for approved macro instruments."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Final

import yfinance as yf

from .engine import VenusMacroAI
from .models import (
    MacroAssessment,
    MarketDirection,
    MarketSnapshot,
)


YAHOO_SYMBOLS: Final[dict[str, str]] = {
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    # No trustworthy Yahoo 2Y mapping is assumed.
    # Missing US2Y is reported transparently by the scoring engine.
    "VIX": "^VIX",
    "XAGUSD": "SI=F",
    "SPX500": "^GSPC",
    "US30": "^DJI",
    "NASDAQ100": "^NDX",
    "USOIL": "CL=F",
    "BTCUSD": "BTC-USD",
}


def _direction(change_percent: Decimal) -> MarketDirection:
    threshold = Decimal("0.02")

    if change_percent > threshold:
        return MarketDirection.UP
    if change_percent < -threshold:
        return MarketDirection.DOWN
    return MarketDirection.FLAT


def _snapshot(
    logical_symbol: str,
    yahoo_symbol: str,
) -> MarketSnapshot | None:
    """Fetch one normalized snapshot without persistence or execution."""
    try:
        history = yf.Ticker(yahoo_symbol).history(
            period="5d",
            interval="1d",
            auto_adjust=False,
            actions=False,
        )
    except Exception:
        return None

    if history.empty or "Close" not in history:
        return None

    closes = history["Close"].dropna()

    if len(closes) < 2:
        return None

    previous = Decimal(str(float(closes.iloc[-2])))
    current = Decimal(str(float(closes.iloc[-1])))

    if previous <= 0 or current <= 0:
        return None

    change_percent = (
        (current - previous) / previous * Decimal("100")
    ).quantize(Decimal("0.0001"))

    raw_timestamp = closes.index[-1]
    observed_at = raw_timestamp.to_pydatetime()

    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    else:
        observed_at = observed_at.astimezone(timezone.utc)

    return MarketSnapshot(
        symbol=logical_symbol,
        price=current,
        change_percent=change_percent,
        direction=_direction(change_percent),
        observed_at=observed_at,
        source=f"YAHOO_FINANCE:{yahoo_symbol}",
    )


def load_macro_snapshots() -> tuple[MarketSnapshot, ...]:
    """Load available approved snapshots; missing sources remain missing."""
    snapshots = []

    for logical_symbol, yahoo_symbol in YAHOO_SYMBOLS.items():
        snapshot = _snapshot(logical_symbol, yahoo_symbol)

        if snapshot is not None:
            snapshots.append(snapshot)

    return tuple(snapshots)


def load_macro_assessment() -> MacroAssessment | None:
    """Return deterministic assessment or None when all providers fail."""
    snapshots = load_macro_snapshots()

    if not snapshots:
        return None

    return VenusMacroAI().assess(snapshots)
