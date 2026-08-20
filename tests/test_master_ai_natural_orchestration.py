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


def test_long_seo_blog_brief_is_not_misread_as_agent_status(monkeypatch) -> None:
    _authorize(monkeypatch)
    calls: list[dict] = []
    status_calls: list[bool] = []
    prompt = """Create ONE real SEO blog DRAFT using ai_blog_agent.

Topic:
Gold Trading Strategy for XAUUSD: How to Identify Buy and Sell Setups

Requirements:
- DRAFT only. Never publish.
- 1400-1600 words.
- Include H2/H3 structure, practical examples, FAQ and trading risk disclaimer.

Images:
- Create/select 1 featured image.

Return ONLY the verified execution result:
- DRAFT_ID
- STATUS
- PREVIEW_LINK
"""

    result = handle_master_command_text(
        text=prompt,
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
        status_loader=lambda: status_calls.append(True) or [],
    )

    assert result.status == "COMPLETED"
    assert len(calls) == 1
    assert calls[0]["input_payload"]["agent_keys"] == ["ai_blog_agent"]
    assert calls[0]["input_payload"]["publish"] is False
    assert calls[0]["input_payload"]["include_image"] is False
    assert status_calls == []


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
def test_natural_signal_question_returns_read_only_snapshot(
    monkeypatch,
    message: str,
) -> None:
    from datetime import date
    from decimal import Decimal
    from services.master_ai_signal_reader import MasterAISignalSnapshot

    _authorize(monkeypatch)
    runner_calls: list[dict] = []
    chat_calls: list[str] = []

    snapshot = MasterAISignalSnapshot(
        signal_date=date(2026, 7, 29),
        open_price=Decimal("4028.68"),
        high_price=Decimal("4047.76"),
        low_price=Decimal("4009.79"),
        close_price=Decimal("4031.44"),
        day_high=Decimal("4047.76"),
        day_low=Decimal("4009.79"),
        step=Decimal("9.49"),
        range_value=Decimal("37.97"),
        buy_base=Decimal("4019.72"),
        sell_base=Decimal("4044.33"),
        mode="Aggressive (0.25)",
        latest_slot="04:30 PM TO 05:30 PM",
        live_cmp=Decimal("4031.44"),
        buy_targets=(Decimal("4029.21"), Decimal("4038.70")),
        sell_targets=(Decimal("4034.84"), Decimal("4025.35")),
    )

    monkeypatch.setattr(
        "services.telegram_master_ai_control.get_today_signal_snapshot",
        lambda: snapshot,
    )
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

    assert result.status == "COMPLETED"
    assert "Read-only signal status" in (result.response_text or "")
    assert "Live CMP: 4031.44" in (result.response_text or "")
    assert "Buy Targets: 4029.21, 4038.70" in (result.response_text or "")
    assert "Sell Targets: 4034.84, 4025.35" in (result.response_text or "")
    assert "koi signal create, execute ya publish nahi hua" in (
        result.response_text or ""
    )
    assert runner_calls == []
    assert chat_calls == []


def test_signal_run_request_still_requires_owner_approval(monkeypatch) -> None:
    _authorize(monkeypatch)
    runner_calls: list[dict] = []

    result = handle_master_command_text(
        text="Signal Agent chalao",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: runner_calls.append(kwargs),
    )

    assert result.status == "APPROVAL_REQUIRED"
    assert "Action: run_signal_agent" in (result.response_text or "")
    assert "Executed: NO" in (result.response_text or "")
    assert runner_calls == []


def test_unrelated_conversation_still_reaches_normal_ai_chat(monkeypatch) -> None:
    _authorize(monkeypatch)
    monkeypatch.setattr(
        "services.telegram_master_ai_control._MASTER_CHAT_MEMORY",
        {},
    )
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


@pytest.mark.parametrize(
    "message",
    (
        "Signal band karo",
        "Signal bandh karo",
        "Signal stop karo",
        "Disable signal",
        "Signal Agent off karo",
    ),
)
def test_signal_stop_requests_require_owner_approval_without_execution(
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
    assert "Action: disable_signal_agent" in (result.response_text or "")
    assert "Risk: HIGH" in (result.response_text or "")
    assert "Executed: NO" in (result.response_text or "")
    assert runner_calls == []
    assert chat_calls == []
