from decimal import Decimal

from services.signal_target_monitor import (
    format_target_hit_message,
    profit_points,
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
