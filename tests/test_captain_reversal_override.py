from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from services.captain_shadow_gate import evaluate_signal_shadow_gate
from services.google_sheets import GoogleSheetsService
from services.sheet_signal_source import _structural_override_signal


def _assessment(*, decision="APPROVE", direction="BUY", news_locked=False):
    return SimpleNamespace(
        decision=SimpleNamespace(value=decision),
        direction=SimpleNamespace(value=direction),
        confidence=95,
        macro_bias="BULLISH_GOLD",
        macro_confidence=90,
        news_locked=news_locked,
        reasons=("test",),
    )


def _two_sided_observed(*, decision="APPROVE", direction="BUY"):
    return SimpleNamespace(
        assessment=_assessment(decision=decision, direction=direction),
        signal_date=date(2026, 8, 19),
        source="GOOGLE_SHEET",
        day_high=Decimal("4460.70"),
        day_low=Decimal("4354.07"),
        live_cmp=Decimal("4460.70"),
        buy_base=Decimal("4357.90"),
        sell_base=Decimal("4446.66"),
        buy_targets=(),
        sell_targets=(),
    )


def test_confirmed_two_bar_reversal_resolves_only_two_sided_sweep(monkeypatch):
    monkeypatch.setenv("CAPTAIN_SIGNAL_SHADOW_GATE", "1")
    monkeypatch.setattr(
        "services.captain_shadow_gate.record_captain_shadow_audit",
        lambda *args, **kwargs: SimpleNamespace(
            correlation_id="audit-reversal",
            persisted=True,
            master_ai_summary="verified reversal",
        ),
    )

    result = evaluate_signal_shadow_gate(
        {"id": 100, "signal_type": "BUY"},
        runner=lambda: _two_sided_observed(),
        structure_reversal_confirmed=True,
    )

    assert result.blocked is False
    assert result.decision == "APPROVE"
    assert result.direction == "BUY"
    assert "two-bar structural reversal" in result.reason


def test_reversal_override_never_bypasses_captain_wait(monkeypatch):
    monkeypatch.setenv("CAPTAIN_SIGNAL_SHADOW_GATE", "1")
    monkeypatch.setattr(
        "services.captain_shadow_gate.record_captain_shadow_audit",
        lambda *args, **kwargs: SimpleNamespace(
            correlation_id="audit-wait",
            persisted=True,
            master_ai_summary="blocked",
        ),
    )

    result = evaluate_signal_shadow_gate(
        {"id": 101, "signal_type": "BUY"},
        runner=lambda: _two_sided_observed(decision="WAIT", direction="BUY"),
        structure_reversal_confirmed=True,
    )

    assert result.blocked is True
    assert result.decision == "WAIT"


def test_august_19_evening_two_high_break_emits_buy_before_cmp_cross():
    values = [
        ["DATE: 2026-08-19"],
        [
            "Open", "High", "Low", "Close", "", "", "",
            "EVENING SESSION", "02:30 PM - 03:30 AM",
            "Session High", "Session Low", "Buy Base", "Sell Base", "Mode",
        ],
        [
            "4333.45", "4460.70", "4325.97", "4460.70", "", "", "",
            "READY", "02:30 PM - 03:30 AM",
            "4460.70", "4354.07", "4357.90", "4446.66", "Conservative (0.18)",
        ],
        [],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP", "", "Target", "BUY Level", "SELL Level", "Step", "Range", "Multiplier", "Session"],
        ["02:30 PM TO 03:30 PM", "4361.73", "4354.07", "4357.44", "4357.90", "4361.34", "", "Target 1", "4377.09", "4427.47", "19.19", "106.63", "0.18", "EVENING SESSION"],
        ["03:30 PM TO 04:30 PM", "4369.29", "4359.46", "4357.90", "4364.37", "4366.42", "", "Target 2", "4396.28", "4408.28", "19.19", "106.63", "0.18", "EVENING SESSION"],
        ["04:30 PM TO 05:30 PM", "4375.45", "4363.38", "4364.38", "4369.41", "4365.21", "", "Target 3", "4415.47", "4389.09", "19.19", "106.63", "0.18", "EVENING SESSION"],
        ["05:30 PM TO 06:30 PM", "4442.47", "4362.17", "4369.42", "4402.32", "4437.94", "", "Target 4", "4434.66", "4369.90", "19.19", "106.63", "0.18", "EVENING SESSION"],
        ["06:30 PM TO 07:30 PM", "4460.70", "4432.62", "4402.32", "4446.66", "4460.70", "", "Target 5", "4453.85", "4350.71", "19.19", "106.63", "0.18", "EVENING SESSION"],
        ["07:30 PM TO 08:30 PM", "", "", "4446.66", "", "", "", "Target 6", "4473.04", "4331.52", "19.19", "106.63", "0.18", "EVENING SESSION"],
    ]

    sheets = GoogleSheetsService.__new__(GoogleSheetsService)
    signal = _structural_override_signal(
        sheets,
        values,
        now=datetime(2026, 8, 19, 12, 1, tzinfo=timezone.utc),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4357.90")
    assert signal.stop_loss == Decimal("4354.07")
    assert signal.target_price == Decimal("4377.09")
    assert signal.targets == (
        Decimal("4377.09"),
        Decimal("4396.28"),
        Decimal("4415.47"),
        Decimal("4434.66"),
        Decimal("4453.85"),
        Decimal("4473.04"),
    )
    assert "two closed higher highs" in signal.label
