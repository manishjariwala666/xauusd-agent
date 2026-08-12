from services.signal_message_formatter import (
    BACK_ONLINE_MESSAGE,
    MAINTENANCE_MESSAGE,
    WEEKEND_MESSAGE,
    format_signal_message,
)


def _signal(direction: str = "BUY") -> dict:
    return {
        "signal_type": direction,
        "price": "4080",
        "signal_time": "2026-07-28T15:30:00+00:00",
        "target_1": "4039.09",
        "target_2": "4056.34",
        "target_3": "4073.59",
        "target_4": "4090.84",
        "target_5": "4108.09",
        "target_6": "4125.34",
        "stop_loss": "4071",
        "sheet_label": "Google Sheet Target 1-6",
    }


def test_shared_signal_message_contains_six_targets() -> None:
    message = format_signal_message(_signal())

    for index in range(1, 7):
        assert f"🎯 Target {index}:" in message

    assert "🟢 XAUUSD BUY" in message
    assert "🛑 Stop Loss: 4071" in message
    assert "— VenusRealm" in message


def test_sell_signal_uses_sell_icon() -> None:
    message = format_signal_message(_signal("SELL"))
    assert "🔴 XAUUSD SELL" in message


def test_all_service_messages_are_english() -> None:
    assert "Saturday and Sunday" in WEEKEND_MESSAGE
    assert "System Maintenance" in MAINTENANCE_MESSAGE
    assert "Back Online" in BACK_ONLINE_MESSAGE
