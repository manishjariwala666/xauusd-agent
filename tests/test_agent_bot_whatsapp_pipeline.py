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
