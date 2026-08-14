from decimal import Decimal
from types import SimpleNamespace

from services import master_ai_chat_service


def test_macro_request_uses_read_only_macro_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assessment = SimpleNamespace(
        bias=SimpleNamespace(value="BUY"),
        confidence=82,
        total_score=Decimal("0.61"),
        source_count=4,
        conflicts=(),
    )

    monkeypatch.setattr(
        master_ai_chat_service,
        "load_macro_assessment",
        lambda: assessment,
    )

    result = master_ai_chat_service.generate_master_ai_reply(
        "gold macro bias batao"
    )

    assert "Venus Macro AI" in result
    assert "Bias: BUY" in result
    assert "Confidence: 82%" in result
    assert "Mode: READ-ONLY" in result
    assert "No trade" in result


def test_macro_failure_does_not_guess(monkeypatch):
    def fail():
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        master_ai_chat_service,
        "load_macro_assessment",
        fail,
    )

    result = master_ai_chat_service.generate_master_ai_reply(
        "macro outlook"
    )

    assert "temporarily unavailable" in result
    assert "No market bias was guessed" in result
