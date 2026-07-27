from datetime import datetime, timezone
from decimal import Decimal

from services import mt5_h1_google_sheet_sync
from services.mt5_h1_repository import H1Candle


def candle() -> H1Candle:
    return H1Candle(
        symbol="XAUUSD",
        candle_start_utc=datetime(
            2026, 7, 27, 15, 0, tzinfo=timezone.utc
        ),
        open=Decimal("4090.10"),
        high=Decimal("4098.50"),
        low=Decimal("4088.20"),
        close=Decimal("4095.75"),
        broker_symbol="XAUUSDM",
        broker_server="LOCAL_TEST",
        received_at_utc=datetime(
            2026, 7, 27, 16, 0, tzinfo=timezone.utc
        ),
        source_event_id="sheet-sync-test-1",
        source="MT5",
    )


def test_build_row_is_mt5_h1_only():
    row = mt5_h1_google_sheet_sync.build_google_sheet_row(
        candle(),
        is_test=False,
    )

    assert row["symbol"] == "XAUUSD"
    assert row["timeframe"] == "H1"
    assert row["source"] == "MT5"
    assert row["record_type"] == "LIVE_MT5_H1"
    assert row["is_test"] is False


def test_sync_appends_to_dedicated_tab(monkeypatch):
    captured = {}

    def fake_append(tab_name, row):
        captured["tab_name"] = tab_name
        captured["row"] = row

    monkeypatch.setattr(
        mt5_h1_google_sheet_sync,
        "append_row",
        fake_append,
    )

    row = mt5_h1_google_sheet_sync.sync_candle_to_google_sheet(
        candle(),
        is_test=True,
    )

    assert captured["tab_name"] == "mt5_h1_market_data"
    assert captured["row"] == row
    assert row["record_type"] == "TEST_ONLY_DO_NOT_TRADE"
    assert row["is_test"] is True
