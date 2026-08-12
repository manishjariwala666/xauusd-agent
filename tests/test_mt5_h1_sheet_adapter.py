from datetime import datetime, timezone
from decimal import Decimal

from services.mt5_h1_repository import H1Candle
from services.mt5_h1_sheet_adapter import build_sheet_row


def test_sheet_row_contains_current_mt5_h1_ohlc_and_live_price():
    candle = H1Candle(
        symbol="XAUUSD",
        broker_symbol="XAUUSDm",
        broker_server="LOCAL_TEST",
        candle_start_utc=datetime(
            2026, 7, 27, 11, 0, tzinfo=timezone.utc
        ),
        open=Decimal("4090.10"),
        high=Decimal("4098.50"),
        low=Decimal("4088.20"),
        close=Decimal("4095.75"),
        source_event_id="sheet-adapter-test",
        received_at_utc=datetime(
            2026, 7, 27, 11, 5, tzinfo=timezone.utc
        ),
    )

    row = build_sheet_row(candle)

    assert row["symbol"] == "XAUUSD"
    assert row["timeframe"] == "H1"
    assert row["open"] == 4090.10
    assert row["high"] == 4098.50
    assert row["low"] == 4088.20
    assert row["close"] == 4095.75
    assert row["live_price"] == 4095.75
    assert row["source"] == "MT5"
