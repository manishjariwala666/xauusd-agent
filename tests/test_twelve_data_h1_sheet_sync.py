from services import twelve_data_h1_sheet_sync


def test_sync_appends_expected_row(monkeypatch):
    expected = {
        "symbol": "XAU/USD",
        "timeframe": "1h",
        "candle_time_utc": "2026-07-27 23:00:00",
        "open": "4084.85005",
        "high": "4088.56303",
        "low": "4082.81081",
        "close": "4084.7154",
        "source": "TWELVE_DATA",
        "record_type": "EXTERNAL_API_H1",
        "is_test": False,
        "synced_at_utc": "2026-07-27T23:01:00+00:00",
    }

    captured = {}

    monkeypatch.setattr(
        twelve_data_h1_sheet_sync,
        "fetch_latest_xauusd_h1",
        lambda: expected,
    )

    monkeypatch.setattr(
        twelve_data_h1_sheet_sync,
        "append_row",
        lambda tab_name, row: captured.update(
            {"tab_name": tab_name, "row": row}
        ),
    )

    result = twelve_data_h1_sheet_sync.sync_latest_xauusd_h1()

    assert captured["tab_name"] == "xauusd_h1_market_data"
    assert captured["row"] == expected
    assert result == expected
