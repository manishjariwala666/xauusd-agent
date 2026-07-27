"""Google Sheet-safe adapter for MT5-only XAUUSD H1 data."""

from __future__ import annotations

from typing import Any

from services.mt5_h1_repository import H1Candle


def build_sheet_row(candle: H1Candle) -> dict[str, Any]:
    """Return one normalized row for the active XAUUSD H1 slot."""

    return {
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "candle_start_utc": candle.candle_start_utc.isoformat(),
        "open": float(candle.open),
        "high": float(candle.high),
        "low": float(candle.low),
        "close": float(candle.close),
        "live_price": float(candle.close),
        "source": "MT5",
        "broker_symbol": candle.broker_symbol,
        "broker_server": candle.broker_server,
        "received_at_utc": candle.received_at_utc.isoformat(),
    }
