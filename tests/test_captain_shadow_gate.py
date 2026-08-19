from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from services.captain_shadow_gate import (
    evaluate_signal_shadow_gate,
)


def assessment(
    *,
    decision="WAIT",
    direction="NONE",
    confidence=100,
    macro_bias="BULLISH_GOLD",
    macro_confidence=95,
    news_locked=True,
):
    return SimpleNamespace(
        decision=SimpleNamespace(value=decision),
        direction=SimpleNamespace(value=direction),
        confidence=confidence,
        macro_bias=macro_bias,
        macro_confidence=macro_confidence,
        news_locked=news_locked,
        reasons=("test reason",),
    )


def observed_assessment(
    *,
    decision="APPROVE",
    direction="SELL",
    day_high="4362.70",
    day_low="4325.97",
    buy_base="4332.95",
    sell_base="4357.44",
):
    return SimpleNamespace(
        assessment=assessment(
            decision=decision,
            direction=direction,
            confidence=95,
            news_locked=False,
        ),
        signal_date=date(2026, 8, 19),
        source="GOOGLE_SHEET",
        day_high=Decimal(day_high),
        day_low=Decimal(day_low),
        live_cmp=Decimal("4349.53"),
        buy_base=Decimal(buy_base),
        sell_base=Decimal(sell_base),
        buy_targets=(),
        sell_targets=(),
    )


def test_shadow_gate_disabled_does_not_block(monkeypatch):
    monkeypatch.delenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        raising=False,
    )

    result = evaluate_signal_shadow_gate(
        {"signal_type": "BUY"},
        runner=lambda: assessment(),
    )

    assert result.enabled is False
    assert result.blocked is False
    assert result.decision == "NOT_RUN"


def test_shadow_gate_blocks_wait(monkeypatch):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    result = evaluate_signal_shadow_gate(
        {"signal_type": "BUY"},
        runner=lambda: assessment(),
    )

    assert result.enabled is True
    assert result.blocked is True
    assert result.decision == "WAIT"
    assert result.news_locked is True


def test_shadow_gate_allows_matching_captain_approve(monkeypatch):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    result = evaluate_signal_shadow_gate(
        {"signal_type": "BUY"},
        runner=lambda: assessment(
            decision="APPROVE",
            direction="BUY",
            confidence=95,
            news_locked=False,
        ),
    )

    assert result.enabled is False
    assert result.decision == "APPROVE"
    assert result.direction == "BUY"
    assert result.blocked is False


def test_shadow_gate_blocks_direction_mismatch(monkeypatch):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    result = evaluate_signal_shadow_gate(
        {"signal_type": "SELL"},
        runner=lambda: assessment(
            decision="APPROVE",
            direction="BUY",
            confidence=95,
            news_locked=False,
        ),
    )

    assert result.enabled is True
    assert result.blocked is True
    assert "direction mismatch" in result.reason


def test_two_sided_session_sweep_blocks_even_matching_approve(monkeypatch):
    monkeypatch.setenv("CAPTAIN_SIGNAL_SHADOW_GATE", "1")
    monkeypatch.setattr(
        "services.captain_shadow_gate.record_captain_shadow_audit",
        lambda *args, **kwargs: SimpleNamespace(
            correlation_id="audit-whipsaw",
            persisted=True,
            master_ai_summary="two-sided sweep blocked",
        ),
    )

    result = evaluate_signal_shadow_gate(
        {"id": 19, "signal_type": "SELL"},
        runner=lambda: observed_assessment(),
    )

    assert result.blocked is True
    assert result.decision == "APPROVE"
    assert result.direction == "SELL"
    assert "Two-sided session sweep detected" in result.reason
    assert "Buy Base (4332.95)" in result.reason
    assert "Sell Base (4357.44)" in result.reason
    assert result.audit_correlation_id == "audit-whipsaw"


def test_one_sided_structure_keeps_matching_approve_allowed(monkeypatch):
    monkeypatch.setenv("CAPTAIN_SIGNAL_SHADOW_GATE", "1")
    monkeypatch.setattr(
        "services.captain_shadow_gate.record_captain_shadow_audit",
        lambda *args, **kwargs: SimpleNamespace(
            correlation_id="audit-one-sided",
            persisted=True,
            master_ai_summary="verified",
        ),
    )

    result = evaluate_signal_shadow_gate(
        {"id": 20, "signal_type": "SELL"},
        runner=lambda: observed_assessment(
            day_high="4362.70",
            day_low="4340.00",
        ),
    )

    assert result.blocked is False
    assert result.direction == "SELL"
    assert result.audit_correlation_id == "audit-one-sided"


def test_shadow_gate_fails_closed_on_runtime_error(monkeypatch):
    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    def fail():
        raise RuntimeError("boom")

    result = evaluate_signal_shadow_gate(
        {"signal_type": "BUY"},
        runner=fail,
    )

    assert result.enabled is True
    assert result.blocked is True
    assert result.decision == "ERROR"
    assert result.news_locked is True


def test_telegram_send_signal_never_calls_bot_when_gate_blocks(monkeypatch):
    from services.telegram_service import TelegramService

    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    class FakeBot:
        def __init__(self):
            self.calls = 0

        def send_message(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError(
                "Telegram network send must not execute when verification blocks."
            )

    service = TelegramService.__new__(TelegramService)
    service._bot = FakeBot()
    service._chat_id = "shadow-test"
    service._supabase = None

    monkeypatch.setattr(
        "services.captain_shadow_gate.evaluate_signal_shadow_gate",
        lambda signal: type(
            "Shadow",
            (),
            {
                "enabled": True,
                "blocked": True,
                "decision": "WAIT",
                "direction": "NONE",
                "confidence": 95,
                "macro_bias": "BULLISH_GOLD",
                "macro_confidence": 95,
                "news_locked": False,
                "reason": "verification blocked",
            },
        )(),
    )

    result = service.send_signal(
        {
            "id": "shadow-signal-1",
            "signal_type": "BUY",
            "price": 4342.54,
        },
        test=False,
    )

    assert result is False
    assert service._bot.calls == 0


def test_shadow_gate_audit_failure_never_allows_delivery(monkeypatch):
    from services.telegram_service import TelegramService

    monkeypatch.setenv(
        "CAPTAIN_SIGNAL_SHADOW_GATE",
        "1",
    )

    class FakeBot:
        def __init__(self):
            self.calls = 0

        def send_message(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("Telegram send must stay blocked")

    service = TelegramService.__new__(TelegramService)
    service._bot = FakeBot()
    service._chat_id = "shadow"
    service._supabase = None

    monkeypatch.setattr(
        "services.captain_shadow_gate.evaluate_signal_shadow_gate",
        lambda signal: type(
            "Shadow",
            (),
            {
                "enabled": True,
                "blocked": True,
                "decision": "WAIT",
                "direction": "NONE",
                "confidence": 100,
                "macro_bias": "BULLISH_GOLD",
                "macro_confidence": 95,
                "news_locked": True,
                "reason": "calendar unavailable",
            },
        )(),
    )

    monkeypatch.setattr(
        "services.google_sheets_service.append_signal_log",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("audit down")
        ),
    )

    result = service.send_signal(
        {
            "id": "shadow-audit-1",
            "signal_type": "BUY",
            "price": 4342.54,
        },
        test=False,
    )

    assert result is False
    assert service._bot.calls == 0
