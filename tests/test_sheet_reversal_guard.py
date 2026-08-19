from datetime import datetime, timezone

from services.sheet_reversal_guard import opposite_reversal_confirmed


def test_august_19_sell_does_not_flip_on_first_bounce() -> None:
    values = [
        ["DATE: 2026-08-19"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["09:30 AM TO 10:30 AM", "4355.97", "4344.80", "4355.98", "4350.39", "4348.72"],
        ["10:30 AM TO 11:30 AM", "4350.28", "4335.73", "4350.39", "4343.01", "4338.31"],
        ["11:30 AM TO 12:30 PM", "4348.80", "4333.92", "4343.00", "4341.36", "4348.58"],
        ["12:30 PM TO 01:30 PM", "4362.62", "4347.87", "4341.36", "4355.24", "4355.28"],
    ]

    assert not opposite_reversal_confirmed(
        values,
        signal_date="2026-08-19",
        session_name="morning",
        from_direction="SELL",
        to_direction="BUY",
        now=datetime(2026, 8, 19, 8, 1, tzinfo=timezone.utc),
    )


def test_sell_to_buy_requires_two_higher_highs_and_bullish_confirmation() -> None:
    values = [
        ["DATE: 2026-08-19"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["10:30 AM TO 11:30 AM", "4350.28", "4335.73", "4350.39", "4343.01", "4338.31"],
        ["11:30 AM TO 12:30 PM", "4355.00", "4338.00", "4343.01", "4348.00", "4349.00"],
        ["12:30 PM TO 01:30 PM", "4362.62", "4347.87", "4348.00", "4355.24", "4356.00"],
    ]

    assert opposite_reversal_confirmed(
        values,
        signal_date="2026-08-19",
        session_name="morning",
        from_direction="SELL",
        to_direction="BUY",
        now=datetime(2026, 8, 19, 8, 1, tzinfo=timezone.utc),
    )


def test_august_18_single_stop_wick_does_not_confirm_buy_reversal() -> None:
    values = [
        ["DATE: 2026-08-18"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["03:30 PM TO 04:30 PM", "4399.47", "4389.62", "4391.00", "4394.55", "4397.51"],
        ["04:30 PM TO 05:30 PM", "4398.58", "4388.45", "4394.55", "4393.52", "4396.02"],
        ["05:30 PM TO 06:30 PM", "4400.05", "4390.71", "4393.51", "4395.38", "4394.51"],
    ]

    assert not opposite_reversal_confirmed(
        values,
        signal_date="2026-08-18",
        session_name="evening",
        from_direction="SELL",
        to_direction="BUY",
        now=datetime(2026, 8, 18, 13, 1, tzinfo=timezone.utc),
    )


def test_buy_to_sell_requires_two_lower_lows_and_bearish_confirmation() -> None:
    values = [
        ["DATE: 2026-08-18"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["04:30 PM TO 05:30 PM", "4400", "4395", "4398", "4397", "4398"],
        ["05:30 PM TO 06:30 PM", "4398", "4390", "4397", "4394", "4393"],
        ["06:30 PM TO 07:30 PM", "4396", "4384", "4394", "4390", "4388"],
    ]

    assert opposite_reversal_confirmed(
        values,
        signal_date="2026-08-18",
        session_name="evening",
        from_direction="BUY",
        to_direction="SELL",
        now=datetime(2026, 8, 18, 14, 1, tzinfo=timezone.utc),
    )
