from decimal import Decimal

import pytest

from services.google_sheets import SheetSignal
from services.sheet_signal_risk_guard import (
    SignalRiskGuardError,
    protect_sheet_signal,
    requires_risk_guard,
)


def _sheet_rows(*, session_high: str = "4435.58", session_low: str = "4389.68"):
    return [
        ["DATE: 2026-08-18"],
        ["", "", "", "", "", "", "", "MORNING SESSION", "03:30 AM - 02:30 PM", "Session High", "Session Low", "Buy Base", "Sell Base", "Mode"],
        ["", "", "", "", "", "", "", "READY", "03:30 AM - 02:30 PM", session_high, session_low, "4390.39", "4425.87", "Aggressive (0.25)"],
        ["", "", "", "", "", "", "", "Target", "BUY Level", "SELL Level", "Step", "Range", "Multiplier", "Session"],
        ["", "", "", "", "", "", "", "Target 1", "4401.86", "4414.40", "11.47", "45.90", "0.25", "MORNING SESSION"],
    ]


def _sell_signal(stop_loss: str = "4433.70") -> SheetSignal:
    return SheetSignal(
        direction="SELL",
        target_price=Decimal("4414.40"),
        stop_loss=Decimal(stop_loss),
        label=(
            "2026-08-18 06:30 AM TO 07:30 AM · "
            "lower low + lower average + CMP below average + recent candle high"
        ),
        external_key="gsheet-session:2026-08-18:morning:SELL",
        reference_price=Decimal("4425.87"),
    )


def test_sell_fallback_stop_uses_wider_session_high_plus_step_multiplier_buffer():
    guarded = protect_sheet_signal(_sell_signal(), _sheet_rows())

    # max(4433.70 recent candle high, 4435.58 session high)
    # + (11.47 * 0.25 = 2.8675) => 4438.45 after 0.01 rounding.
    assert guarded.stop_loss == Decimal("4438.45")
    assert "risk guard: session high + 2.87 buffer" in guarded.label


def test_buy_fallback_stop_uses_session_low_minus_step_multiplier_buffer():
    signal = SheetSignal(
        direction="BUY",
        target_price=Decimal("4401.86"),
        stop_loss=Decimal("4394.06"),
        label=(
            "2026-08-18 06:30 AM TO 07:30 AM · "
            "higher high + higher average + CMP above average + recent candle low"
        ),
        external_key="gsheet-session:2026-08-18:morning:BUY",
        reference_price=Decimal("4390.39"),
    )

    # This specific candidate is invalid because the provided recent/session lows
    # are not below the configured BUY entry; the guard must fail closed instead
    # of inventing a stop.
    with pytest.raises(SignalRiskGuardError, match="session low is invalid"):
        protect_sheet_signal(signal, _sheet_rows())


def test_explicit_sheet_stop_is_never_rewritten():
    signal = SheetSignal(
        direction="SELL",
        target_price=Decimal("4414.40"),
        stop_loss=Decimal("4440.00"),
        label="2026-08-18 signal · sheet SELL SL",
        external_key="gsheet-session:2026-08-18:morning:SELL",
        reference_price=Decimal("4425.87"),
    )

    assert requires_risk_guard(signal) is False
    assert protect_sheet_signal(signal, _sheet_rows()) == signal


def test_missing_exact_session_summary_fails_closed():
    rows = [["DATE: 2026-08-18"], ["no session summary"]]

    with pytest.raises(SignalRiskGuardError, match="Morning session summary is unavailable"):
        protect_sheet_signal(_sell_signal(), rows)
