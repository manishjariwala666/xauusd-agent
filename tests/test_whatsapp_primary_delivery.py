from datetime import datetime, timezone
from types import SimpleNamespace

import services.production_agents as production_agents


class FakeWhatsAppService:
    calls = []

    def send_text(self, recipient, message):
        type(self).calls.append((recipient, message))
        return "wamid.test.123"


class WeekdayDateTime:
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 8, 24, 9, 0, tzinfo=tz or timezone.utc)


def test_whatsapp_uses_shared_durable_contract(monkeypatch):
    captured = {}
    FakeWhatsAppService.calls = []

    monkeypatch.setattr(production_agents, "datetime", WeekdayDateTime)
    monkeypatch.setattr(
        production_agents._legacy,
        "_verified_whatsapp_recipients",
        lambda: ["15550000001", "15550000002"],
    )
    monkeypatch.setattr(
        production_agents._legacy,
        "WhatsAppService",
        FakeWhatsAppService,
    )
    monkeypatch.setattr(
        production_agents._legacy,
        "format_signal_message",
        lambda signal: f"{signal['signal_type']} {signal['id']}",
    )

    def durable(**kwargs):
        captured.update(kwargs)
        assert kwargs["channel"] == "whatsapp"
        assert kwargs["recipients"] == ["15550000001", "15550000002"]
        assert kwargs["max_attempts"] == 3
        assert kwargs["format_message"]({"signal_type": "SELL", "id": 11}) == "SELL 11"
        assert kwargs["send"]("15550000001", "SELL 11") == "wamid.test.123"
        return 1, 0

    monkeypatch.setattr(
        production_agents,
        "deliver_pending_signal_recipients",
        durable,
    )

    production_agents._durable_pending_whatsapp_signals()

    assert captured["verify_signal"] is production_agents._captain_delivery_verifier
    assert FakeWhatsAppService.calls == [("15550000001", "SELL 11")]


def test_whatsapp_no_verified_recipients_never_enters_delivery(monkeypatch):
    called = False

    monkeypatch.setattr(
        production_agents._legacy,
        "_verified_whatsapp_recipients",
        lambda: [],
    )

    def durable(**kwargs):
        nonlocal called
        called = True
        return 0, 0

    monkeypatch.setattr(
        production_agents,
        "deliver_pending_signal_recipients",
        durable,
    )

    production_agents._durable_pending_whatsapp_signals()
    assert called is False


def test_shared_captain_verifier_allows_matching_approve(monkeypatch):
    monkeypatch.setattr(
        "services.captain_shadow_gate.evaluate_signal_shadow_gate",
        lambda signal: SimpleNamespace(
            blocked=False,
            decision="APPROVE",
            direction=signal["signal_type"],
            confidence=96,
            macro_bias="BULLISH_GOLD",
            news_locked=False,
            reason="verified",
        ),
    )

    allowed, reason = production_agents._captain_delivery_verifier(
        {"signal_type": "BUY", "id": 21}
    )

    assert allowed is True
    assert reason == "verified"


def test_shared_captain_verifier_blocks_and_preserves_reason(monkeypatch):
    monkeypatch.setattr(
        "services.captain_shadow_gate.evaluate_signal_shadow_gate",
        lambda signal: SimpleNamespace(
            blocked=True,
            decision="WAIT",
            direction="NONE",
            confidence=100,
            macro_bias="NEUTRAL",
            news_locked=True,
            reason="high impact news lock",
        ),
    )

    allowed, reason = production_agents._captain_delivery_verifier(
        {"signal_type": "SELL", "id": 22}
    )

    assert allowed is False
    assert "decision=WAIT" in reason
    assert "news_locked=True" in reason
    assert "high impact news lock" in reason
