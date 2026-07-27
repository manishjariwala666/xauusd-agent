"""Synchronise validated MT5 XAUUSD H1 candles to Google Sheets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.google_sheets_service import append_row
from services.mt5_h1_repository import H1Candle
from services.mt5_h1_sheet_adapter import build_sheet_row


MT5_H1_WORKSHEET = "mt5_h1_market_data"


def build_google_sheet_row(
    candle: H1Candle,
    *,
    is_test: bool = False,
) -> dict[str, Any]:
    row = dict(build_sheet_row(candle))

    row.update(
        {
            "record_type": (
                "TEST_ONLY_DO_NOT_TRADE"
                if is_test
                else "LIVE_MT5_H1"
            ),
            "source_event_id": candle.source_event_id,
            "synced_at_utc": datetime.now(timezone.utc).isoformat(),
            "is_test": is_test,
        }
    )

    return row


def sync_candle_to_google_sheet(
    candle: H1Candle,
    *,
    is_test: bool = False,
    worksheet_name: str = MT5_H1_WORKSHEET,
) -> dict[str, Any]:
    row = build_google_sheet_row(candle, is_test=is_test)
    append_row(worksheet_name, row)
    return row
