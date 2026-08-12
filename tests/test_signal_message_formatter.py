from services.signal_message_formatter import (
    BACK_ONLINE_MESSAGE,
    MAINTENANCE_MESSAGE,
    WEEKEND_MESSAGE,
    format_signal_message,
)


def _signal(direction: str = "BUY") -> dict:
    targets = (
        ["4090", "4100", "4110", "4120", "4130", "4140"]
        if direction == "BUY"
        else ["4070", "4060", "4050", "4040", "4030", "4020"]
    )
    return {
        "signal_type": direction,
        "price": "4080",
        "signal_time": "2026-07-28T15:30:00+00:00",
        **{
            f"target_{index}": target
            for index, target in enumerate(targets, start=1)
        },
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


def test_sell_signal_preserves_actionable_sheet_target_numbers() -> None:
    signal = {
        "signal_type": "SELL",
        "price": "4408.28",
        "signal_time": "2026-08-12T05:00:00+00:00",
        "target_1": "4395.37",
        "target_2": "4382.46",
        "target_3": "4369.55",
        "target_4": "4356.64",
        "target_5": "4343.73",
        "target_6": "4330.82",
        "stop_loss": "4415.01",
    }

    message = format_signal_message(signal)

    assert "Entry: 4408.28" in message
    assert "Targets: 4,395.37, 4,382.46, 4,369.55" in message
    assert "🎯 Target 1: 4395.37" in message
    assert "🎯 Target 2: 4382.46" in message
    assert "🎯 Target 6: 4330.82" in message
    assert "⏳ Target 1 coming: 4395.37" in message
    assert "🛑 Stop Loss: 4415.01" in message


def test_all_service_messages_are_english() -> None:
    assert "Saturday and Sunday" in WEEKEND_MESSAGE
    assert "System Maintenance" in MAINTENANCE_MESSAGE
    assert "Back Online" in BACK_ONLINE_MESSAGE
