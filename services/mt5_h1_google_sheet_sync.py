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
    
    try:
        from services.google_sheets_service import PrivateGoogleSheetsService, _stringify_cell
        ws = PrivateGoogleSheetsService()._worksheet(worksheet_name)
        headers = ws.row_values(1)
        
        if "candle_start_utc" in headers:
            col_idx = headers.index("candle_start_utc") + 1
            col_values = ws.col_values(col_idx)
            target_val = _stringify_cell(row["candle_start_utc"])
            
            if target_val in col_values:
                # Candle exists! Overwrite the existing row with new High/Low
                row_idx = col_values.index(target_val) + 1
                new_values = [_stringify_cell(row.get(h, "")) for h in headers]
                
                cells = ws.range(row_idx, 1, row_idx, len(headers))
                for i, cell in enumerate(cells):
                    cell.value = new_values[i]
                ws.update_cells(cells)
                
                return row
    except Exception as e:
        import logging
        logging.warning(f"Candle update failed, falling back to append: {e}")
        
    # If not found or error occurred, append as a new candle row
    from services.google_sheets_service import append_row
    append_row(worksheet_name, row)
    return row
