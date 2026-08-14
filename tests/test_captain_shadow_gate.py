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


def test_shadow_gate_blocks_even_captain_approve(monkeypatch):
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

    # Shadow mode observes APPROVE but still blocks delivery.
    assert result.enabled is True
    assert result.decision == "APPROVE"
    assert result.blocked is True


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


def test_telegram_send_signal_never_calls_bot_when_shadow_gate_enabled(
    monkeypatch,
):
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
                "Telegram network send must not execute in shadow mode."
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
                "decision": "APPROVE",
                "direction": "BUY",
                "confidence": 95,
                "macro_bias": "BULLISH_GOLD",
                "macro_confidence": 95,
                "news_locked": False,
                "reason": "shadow test",
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
