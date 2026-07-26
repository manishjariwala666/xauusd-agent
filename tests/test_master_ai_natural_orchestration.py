from __future__ import annotations

from dataclasses import dataclass
import pytest

from services.master_ai_intent_resolver import (
    IntentRisk,
    resolve_master_ai_intent,
)
from services.telegram_master_ai_control import handle_master_command_text


@dataclass
class Progress:
    run_id: int = 91
    status: str = "COMPLETED"
    final_summary: str = "Safe agent completed."


def _authorize(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")


def test_natural_blog_request_reaches_permission_router_as_draft(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Blog Agent se aaj ka draft banao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
    )

    assert result.status == "COMPLETED"
    assert calls[0]["input_payload"]["agent_keys"] == ["ai_blog_agent"]
    assert calls[0]["input_payload"]["publish"] is False
    assert calls[0]["input_payload"]["include_image"] is False
    assert calls[0]["source"] == "TELEGRAM_MASTER_AI_NATURAL"


def test_natural_image_request_reaches_image_agent(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Image Agent se featured image banao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
    )

    assert result.status == "COMPLETED"
    assert calls[0]["input_payload"]["agent_keys"] == ["image_agent"]


def test_natural_status_request_is_read_only(monkeypatch) -> None:
    _authorize(monkeypatch)
    runner_calls: list[dict] = []
    result = handle_master_command_text(
        text="Sab agents ka status batao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: runner_calls.append(kwargs),
        status_loader=lambda: [
            {
                "agent_key": "ai_blog_agent",
                "display_name": "Blog Agent",
                "status": "IDLE",
                "is_enabled": True,
            }
        ],
    )

    assert result.status == "COMPLETED"
    assert "Blog Agent: IDLE" in (result.response_text or "")
    assert runner_calls == []


def test_named_agent_status_does_not_run_that_agent(monkeypatch) -> None:
    _authorize(monkeypatch)
    runner_calls: list[dict] = []
    result = handle_master_command_text(
        text="Blog Agent ka status batao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: runner_calls.append(kwargs),
        status_loader=lambda: [],
    )

    assert result.status == "COMPLETED"
    assert runner_calls == []


def test_failed_blog_retry_uses_safe_registered_retry(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Failed Blog Agent retry karo",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
    )

    assert result.status == "COMPLETED"
    assert len(calls) == 1
    assert calls[0]["input_payload"]["agent_keys"] == ["ai_blog_agent"]
    assert calls[0]["input_payload"]["publish"] is False


def test_ambiguous_request_executes_nothing(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Blog Agent aur Image Agent dono se content banao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.status == "CLARIFICATION_REQUIRED"
    assert calls == []


def test_signal_delivery_requires_approval_and_does_not_execute(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Signal Telegram par bhejo",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.status == "APPROVAL_REQUIRED"
    assert calls == []


def test_railway_deployment_requires_approval(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Railway deploy karo",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.status == "APPROVAL_REQUIRED"
    assert calls == []


def test_unauthorized_natural_request_is_rejected(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Blog Agent se aaj ka draft banao",
        telegram_user_id=9999,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.status == "UNAUTHORIZED"
    assert calls == []


def test_invented_agent_action_is_not_executed(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="Quantum Agent ko run karo",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.status == "CLARIFICATION_REQUIRED"
    assert calls == []


def test_natural_action_creates_sanitized_audit_record(monkeypatch) -> None:
    _authorize(monkeypatch)
    audit_calls: list[dict] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control._log_master_command_to_sheet",
        lambda **kwargs: audit_calls.append(kwargs),
    )
    monkeypatch.setattr(
        "services.telegram_master_ai_control._record_command_memory_and_event",
        lambda **kwargs: None,
    )

    handle_master_command_text(
        text="Image Agent se featured image banao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: Progress(),
    )

    assert audit_calls
    assert audit_calls[0]["command"] == "natural:run_image_agent"
    assert "featured image" not in str(audit_calls[0]).lower()


def test_existing_slash_blog_command_still_works(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    result = handle_master_command_text(
        text="/master run blog",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
    )

    assert result.status == "COMPLETED"
    assert calls[0]["input_payload"]["publish"] is False
    assert calls[0]["input_payload"]["include_image"] is False


def test_error_diagnosis_resolves_to_safe_read_only_action() -> None:
    proposal = resolve_master_ai_intent("Master AI ka error diagnose karo")

    assert proposal.action == "read_agent_status"
    assert proposal.risk == IntentRisk.SAFE


@pytest.mark.parametrize(
    "message",
    (
        "today signal?",
        "today signle ?",
        "aaj ka signal?",
        "signal batao",
    ),
)
def test_natural_signal_question_requires_approval_without_execution(
    monkeypatch,
    message: str,
) -> None:
    _authorize(monkeypatch)
    runner_calls: list[dict] = []
    chat_calls: list[str] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control.generate_master_ai_reply",
        lambda prompt: chat_calls.append(prompt) or "GENERIC_CHAT_REPLY",
    )

    result = handle_master_command_text(
        text=message,
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: runner_calls.append(kwargs),
    )

    assert result.status == "APPROVAL_REQUIRED"
    assert "Agent: Signal Agent" in (result.response_text or "")
    assert "Risk: HIGH" in (result.response_text or "")
    assert "Status: APPROVAL_REQUIRED" in (result.response_text or "")
    assert "Executed: NO" in (result.response_text or "")
    assert runner_calls == []
    assert chat_calls == []


def test_unrelated_conversation_still_reaches_normal_ai_chat(monkeypatch) -> None:
    _authorize(monkeypatch)
    chat_calls: list[str] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control.generate_master_ai_reply",
        lambda prompt: chat_calls.append(prompt) or "SAFE_CHAT_REPLY",
    )

    result = handle_master_command_text(
        text="Aaj ka din kaisa raha?",
        telegram_user_id=1001,
        chat_id=55,
    )

    assert result.status == "AI_CHAT_RESPONSE"
    assert result.response_text == "SAFE_CHAT_REPLY"
    assert chat_calls == ["Aaj ka din kaisa raha?"]
