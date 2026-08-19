from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from services.captain_shadow_gate import evaluate_signal_shadow_gate
from services.google_sheets import SheetSignal
from services.sheet_signal_source import _version_canonical_signal


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
        day_high=Decimal("4442.47"),
        day_low=Decimal("4354.07"),
        live_cmp=Decimal("4432.62"),
        buy_base=Decimal("4357.90"),
        sell_base=Decimal("4432.62"),
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


def test_canonical_runtime_key_is_unique_per_setup_bar():
    base = SheetSignal(
        direction="BUY",
        target_price=Decimal("4446.30"),
        stop_loss=Decimal("4354.07"),
        label="evening reversal",
        external_key="gsheet-session:2026-08-19:evening:BUY",
        reference_price=Decimal("4357.90"),
        observed_at=datetime(2026, 8, 19, 11, 0, tzinfo=timezone.utc),
        targets=(Decimal("4446.30"), Decimal("4468.40")),
        target_slots=(Decimal("4446.30"), Decimal("4468.40")),
    )
    later = replace(
        base,
        observed_at=datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc),
    )

    first = _version_canonical_signal(base)
    second = _version_canonical_signal(later)

    assert first is not None and second is not None
    assert first.external_key != second.external_key
    assert first.external_key.startswith("gsheet-session:2026-08-19:evening:BUY:")
    assert second.external_key.startswith("gsheet-session:2026-08-19:evening:BUY:")
