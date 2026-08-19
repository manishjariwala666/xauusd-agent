from datetime import datetime, timezone

from services import master_ai_captain_status
from services import master_ai_chat_service


def _audit_row():
    return {
        "correlation_id": "audit-123",
        "master_ai_summary": (
            "Captain: APPROVE SELL | confidence=94% | CMP=4425.87 | "
            "high=4435.58 | low=4389.68 | Shadow=VERIFIED"
        ),
        "created_at": datetime(2026, 8, 18, 6, 30, tzinfo=timezone.utc),
    }


def test_captain_status_request_uses_canonical_audit_reader(monkeypatch):
    monkeypatch.setattr(
        master_ai_captain_status,
        "latest_captain_shadow_audit",
        _audit_row,
    )

    reply = master_ai_captain_status.latest_captain_status_reply()

    assert "Captain: APPROVE SELL" in reply
    assert "CMP=4425.87" in reply
    assert "Audit: audit-123" in reply


def test_admin_and_telegram_shared_chat_backend_bypass_llm_for_captain_status(monkeypatch):
    monkeypatch.setattr(
        master_ai_chat_service,
        "latest_captain_status_reply",
        lambda: "VERIFIED CAPTAIN AUDIT",
    )
    monkeypatch.setattr(
        master_ai_chat_service,
        "_generate_gemini_reply",
        lambda message: (_ for _ in ()).throw(AssertionError("Gemini must not be called")),
    )

    class ExplodingClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("OpenAI network client must not be called for verified status")

    monkeypatch.setattr(master_ai_chat_service.httpx, "Client", ExplodingClient)

    assert (
        master_ai_chat_service.generate_master_ai_reply(
            "Captain and Shadow ne kya kaam kiya?"
        )
        == "VERIFIED CAPTAIN AUDIT"
    )


def test_missing_audit_fails_closed_without_simulation(monkeypatch):
    monkeypatch.setattr(
        master_ai_captain_status,
        "latest_captain_shadow_audit",
        lambda: None,
    )

    reply = master_ai_captain_status.latest_captain_status_reply()

    assert "verified audit" in reply
    assert "invent nahi karunga" in reply
