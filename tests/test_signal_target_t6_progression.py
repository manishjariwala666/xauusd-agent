from decimal import Decimal

from services.signal_target_monitor import (
    actionable_target_milestones,
    format_target_progress_message,
    reached_target_milestones,
)


def _canonical_sell(**overrides):
    signal = {
        "external_key": "gsheet-session:2026-08-20:morning:SELL",
        "signal_type": "SELL",
        "symbol": "XAUUSD",
        "price": Decimal("4522.78"),
        "target_1": Decimal("4511.85"),
        "target_2": Decimal("4500.92"),
        "target_3": Decimal("4489.99"),
        "target_4": Decimal("4479.06"),
        "target_5": Decimal("4468.13"),
        "target_6": Decimal("4457.20"),
    }
    signal.update(overrides)
    return signal


def test_canonical_sheet_signal_requires_all_six_targets():
    signal = _canonical_sell(target_6=None)
    assert actionable_target_milestones(signal) == []


def test_canonical_sheet_signal_preserves_t1_through_t6_sequence():
    milestones = actionable_target_milestones(_canonical_sell())
    assert [item.number for item in milestones] == [1, 2, 3, 4, 5, 6]
    assert milestones[-1].price == Decimal("4457.20")


def test_target_one_is_progress_only_and_signal_remains_active():
    signal = _canonical_sell()
    reached = reached_target_milestones(signal, Decimal("4510.00"))
    milestones = actionable_target_milestones(signal)
    assert [item.number for item in reached] == [1]

    message = format_target_progress_message(
        signal,
        reached[-1],
        next_milestone=milestones[1],
        achieved_price=Decimal("4510.00"),
    )
    assert "Signal remains active toward the next configured target" in message
    assert "partial exits" not in message.lower()
    assert "Target 2 coming" in message


def test_target_six_is_final_configured_target_completion():
    signal = _canonical_sell()
    reached = reached_target_milestones(signal, Decimal("4450.00"))
    assert [item.number for item in reached] == [1, 2, 3, 4, 5, 6]

    message = format_target_progress_message(
        signal,
        reached[-1],
        next_milestone=None,
        achieved_price=Decimal("4450.00"),
    )
    assert "Target 6 achieved" in message
    assert "all configured targets completed" in message
