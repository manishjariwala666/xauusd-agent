from types import SimpleNamespace
from unittest.mock import Mock

import agent_bot


def test_pipeline_delivers_telegram_and_whatsapp(monkeypatch):
    market_data = Mock()
    telegram = Mock()
    telegram.broadcast_pending_signals.return_value = 2

    whatsapp_delivery = Mock()
    monkeypatch.setattr(
        agent_bot,
        "deliver_pending_whatsapp_signals",
        whatsapp_delivery,
    )

    agent_bot.run_pipeline_once(
        sheets=None,
        market_data=market_data,
        telegram=telegram,
    )

    telegram.broadcast_pending_signals.assert_called_once_with()
    whatsapp_delivery.assert_called_once_with()


def test_pipeline_inserts_new_sheet_signal_before_delivery(monkeypatch):
    sheet_signal = SimpleNamespace(
        external_key="sheet-signal-1",
        reference_price=4100.0,
        observed_at=None,
        source="GOOGLE_SHEETS",
        direction="SELL",
        target_price=4080.0,
        stop_loss=4120.0,
        label="Sheet SELL target",
    )

    sheets = Mock()
    sheets.get_latest_signal.return_value = sheet_signal

    market_price = SimpleNamespace(
        symbol="XAUUSD",
        price=4100.0,
        observed_at=None,
        source="TEST",
    )

    market_data = Mock()
    market_data.signal_exists.return_value = False
    market_data.fetch_current_price.return_value = market_price

    telegram = Mock()
    telegram.broadcast_pending_signals.return_value = 1

    whatsapp_delivery = Mock()
    monkeypatch.setattr(
        agent_bot,
        "deliver_pending_whatsapp_signals",
        whatsapp_delivery,
    )

    agent_bot.run_pipeline_once(
        sheets=sheets,
        market_data=market_data,
        telegram=telegram,
    )

    market_data.insert_signal.assert_called_once()
    telegram.broadcast_pending_signals.assert_called_once_with()
    whatsapp_delivery.assert_called_once_with()


def test_pipeline_persists_sheet_average_without_fetching_live_price(
    monkeypatch,
):
    from datetime import datetime, timezone
    from decimal import Decimal

    observed_at = datetime(
        2026,
        7,
        29,
        1,
        0,
        tzinfo=timezone.utc,
    )

    sheet_signal = SimpleNamespace(
        external_key="sheet-average-buy-4019-73",
        reference_price=Decimal("4019.73"),
        observed_at=observed_at,
        source="GOOGLE_SHEET:Sheet1",
        direction="BUY",
        target_price=Decimal("4029.21"),
        stop_loss=Decimal("4018.00"),
        label="lower low + lower average",
        targets=(
            Decimal("4029.21"),
            Decimal("4038.70"),
            Decimal("4048.19"),
        ),
    )

    sheets = Mock()
    sheets.get_latest_signal.return_value = sheet_signal

    market_data = Mock()
    market_data.signal_exists.return_value = False

    telegram = Mock()
    telegram.broadcast_pending_signals.return_value = 1

    whatsapp_delivery = Mock()
    monkeypatch.setattr(
        agent_bot,
        "deliver_pending_whatsapp_signals",
        whatsapp_delivery,
    )

    agent_bot.run_pipeline_once(
        sheets=sheets,
        market_data=market_data,
        telegram=telegram,
    )

    market_data.fetch_current_price.assert_not_called()
    market_data.insert_signal.assert_called_once()

    inserted = market_data.insert_signal.call_args.kwargs
    assert inserted["market_price"].price == Decimal("4019.73")
    assert inserted["market_price"].observed_at == observed_at
    assert inserted["signal_type"] == "BUY"
    assert inserted["stop_loss"] == Decimal("4018.00")
    assert inserted["targets"][0] == Decimal("4029.21")
