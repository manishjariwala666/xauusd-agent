from decimal import Decimal

from services.signal_target_monitor import (
    actionable_target_milestones,
    format_target_progress_message,
    format_target_hit_message,
    profit_points,
    reached_target_milestones,
    target_is_hit,
)


def test_buy_target_hit() -> None:
    signal = {
        "signal_type": "BUY",
        "price": "4077.75",
        "target_price": "4079.47",
    }

    assert not target_is_hit(signal, Decimal("4079.46"))
    assert target_is_hit(signal, Decimal("4079.47"))
    assert profit_points(signal) == Decimal("1.72")


def test_sell_target_hit() -> None:
    signal = {
        "signal_type": "SELL",
        "price": "4077.75",
        "target_price": "4075.25",
    }

    assert not target_is_hit(signal, Decimal("4075.26"))
    assert target_is_hit(signal, Decimal("4075.25"))
    assert profit_points(signal) == Decimal("2.50")


def test_target_hit_message_format() -> None:
    signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "price": "4077.75",
        "target_price": "4079.47",
    }

    assert format_target_hit_message(signal) == (
        "🎯 Yahooo VenusRealm TARGET HIT ✅\n\n"
        "XAUUSD BUY\n"
        "Entry: 4077.75\n"
        "Target: 4079.47\n"
        "Profit: +1.72 points 🟢\n\n"
        "🎉 Enjoy Profit! 🥳💚"
    )


def test_sell_targets_reject_invalid_first_target_without_renumbering() -> None:
    signal = {
        "symbol": "XAUUSD",
        "signal_type": "SELL",
        "price": "4395.06",
        "target_1": "4395.37",
        "target_2": "4382.46",
        "target_3": "4369.55",
        "target_4": "4356.64",
        "target_5": "4343.73",
        "target_6": "4330.82",
    }

    milestones = actionable_target_milestones(signal)

    assert milestones == []


def test_august_12_sell_base_preserves_all_target_numbers() -> None:
    signal = {
        "symbol": "XAUUSD",
        "signal_type": "SELL",
        "price": "4408.28",
        "target_1": "4395.37",
        "target_2": "4382.46",
        "target_3": "4369.55",
        "target_4": "4356.64",
        "target_5": "4343.73",
        "target_6": "4330.82",
    }

    milestones = actionable_target_milestones(signal)

    assert [(item.number, item.source_slot, item.price) for item in milestones] == [
        (1, 1, Decimal("4395.37")),
        (2, 2, Decimal("4382.46")),
        (3, 3, Decimal("4369.55")),
        (4, 4, Decimal("4356.64")),
        (5, 5, Decimal("4343.73")),
        (6, 6, Decimal("4330.82")),
    ]


def test_buy_progress_at_4406_reports_two_achieved_and_third_coming() -> None:
    signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "price": "4368.68",
        "target_1": "4381.54",
        "target_2": "4394.45",
        "target_3": "4407.36",
        "target_4": "4420.27",
        "target_5": "4433.18",
        "target_6": "4446.09",
    }

    milestones = actionable_target_milestones(signal)
    reached = reached_target_milestones(signal, Decimal("4406.00"))

    assert [item.number for item in reached] == [1, 2]
    message = format_target_progress_message(
        signal,
        reached[-1],
        next_milestone=milestones[2],
        achieved_price=Decimal("4406.00"),
    )
    assert "Target 2 achieved" in message
    assert "Target 3 coming: 4407.36" in message
    assert "Signal remains active toward the next configured target" in message
    assert "partial exits" not in message.lower()
    assert "returns are not guaranteed" in message


def test_invalid_later_target_keeps_source_number_for_next_milestone() -> None:
    signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "price": "100",
        "target_1": "110",
        "target_2": "not-a-price",
        "target_3": "130",
    }

    milestones = actionable_target_milestones(signal)

    assert [(item.number, item.price) for item in milestones] == [
        (1, Decimal("110")),
        (3, Decimal("130")),
    ]
    message = format_target_progress_message(
        signal,
        milestones[0],
        next_milestone=milestones[1],
        achieved_price=Decimal("111"),
    )
    assert "Target 1 achieved" in message
    assert "Target 3 coming: 130.00" in message


def test_buy_stop_loss_hit() -> None:
    from services.signal_target_monitor import (
        loss_points,
        stop_loss_is_hit,
    )

    signal = {
        "signal_type": "BUY",
        "price": "4038.35",
        "stop_loss": "4037.67",
    }

    assert not stop_loss_is_hit(signal, Decimal("4037.68"))
    assert stop_loss_is_hit(signal, Decimal("4037.67"))
    assert stop_loss_is_hit(signal, Decimal("4028.49"))
    assert loss_points(signal) == Decimal("0.68")


def test_sell_stop_loss_hit() -> None:
    from services.signal_target_monitor import (
        loss_points,
        stop_loss_is_hit,
    )

    signal = {
        "signal_type": "SELL",
        "price": "4038.35",
        "stop_loss": "4039.15",
    }

    assert not stop_loss_is_hit(signal, Decimal("4039.14"))
    assert stop_loss_is_hit(signal, Decimal("4039.15"))
    assert stop_loss_is_hit(signal, Decimal("4042.00"))
    assert loss_points(signal) == Decimal("0.80")


def test_stop_loss_hit_message_format() -> None:
    from services.signal_target_monitor import (
        format_stop_loss_hit_message,
    )

    signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "price": "4038.35",
        "stop_loss": "4037.67",
    }

    assert format_stop_loss_hit_message(signal) == (
        "🔴 STOP LOSS HIT — XAUUSD BUY\n\n"
        "Entry: 4038.35\n"
        "Stop Loss: 4037.67\n"
        "Result: -0.68 points\n\n"
        "This signal is now closed.\n"
        "Please wait for the next confirmed setup.\n\n"
        "— VenusRealm"
    )
