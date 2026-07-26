from dataclasses import dataclass

from services.master_ai_tool_router import execute_master_ai_action
from services.telegram_master_ai_control import handle_master_command_text


@dataclass
class Progress:
    run_id: int = 81
    status: str = "COMPLETED"
    final_summary: str | None = None
    safe_error: str | None = None


def test_registered_safe_action_uses_exact_agent_and_stays_draft() -> None:
    calls: list[dict] = []

    def runner(**kwargs):
        calls.append(kwargs)
        return Progress()

    result = execute_master_ai_action("run_blog_agent", runner=runner)

    assert result.ok is True
    assert result.run_id == 81
    assert calls[0]["input_payload"]["agent_keys"] == ["ai_blog_agent"]
    assert calls[0]["input_payload"]["publish"] is False
    assert calls[0]["input_payload"]["include_image"] is False


def test_approval_required_external_action_does_not_run() -> None:
    calls: list[dict] = []

    result = execute_master_ai_action(
        "run_signal_agent",
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.ok is False
    assert result.status == "OWNER_APPROVAL_REQUIRED"
    assert calls == []


def test_unknown_action_remains_blocked() -> None:
    result = execute_master_ai_action("unregistered_agent_action")

    assert result.ok is False
    assert result.status == "UNKNOWN_ACTION"


def test_safe_value_error_reason_is_actionable_without_traceback() -> None:
    def runner(**kwargs):
        raise ValueError("Google Sheets credentials are unavailable.")

    result = execute_master_ai_action("run_image_agent", runner=runner)

    assert result.ok is False
    assert "Google Sheets credentials are unavailable." in result.message
    assert "Next action:" in result.message
    assert "Traceback" not in result.message
    assert "ValueError" not in result.message


def test_secret_assignment_and_local_path_are_not_returned() -> None:
    def runner(**kwargs):
        raise RuntimeError(
            "/Users/admin/private/service.py api_key=do-not-display traceback"
        )

    result = execute_master_ai_action("run_image_agent", runner=runner)

    assert result.ok is False
    assert result.status == "ERROR"
    assert result.message.startswith("Reason: Internal agent configuration failed.")
    assert "/Users/" not in result.message
    assert "api_key" not in result.message
    assert "do-not-display" not in result.message
    assert "traceback" not in result.message.lower()


def test_disabled_agent_failure_reports_clear_safe_reason() -> None:
    result = execute_master_ai_action(
        "run_image_agent",
        runner=lambda **kwargs: Progress(
            status="FAILED",
            safe_error="Agent is disabled, unavailable, or already running.",
        ),
    )

    assert result.ok is False
    assert result.status == "FAILED"
    assert result.run_id == 81
    assert "Agent is disabled" in result.message
    assert "Next action:" in result.message


def test_read_only_diagnostics_are_available() -> None:
    result = execute_master_ai_action(
        "read_agent_status",
        status_loader=lambda: [
            {
                "agent_key": "image_agent",
                "display_name": "Image Agent",
                "status": "IDLE",
                "is_enabled": True,
            }
        ],
    )

    assert result.ok is True
    assert result.status == "COMPLETED"
    assert "Image Agent: IDLE, enabled=ON" in result.message


def test_retry_only_replays_registered_automatic_action() -> None:
    calls: list[dict] = []

    result = execute_master_ai_action(
        "retry_failed_agent",
        retry_action="run_blog_agent",
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
    )

    assert result.ok is True
    assert len(calls) == 1


def test_retry_does_not_bypass_external_action_approval() -> None:
    result = execute_master_ai_action(
        "retry_failed_agent",
        retry_action="run_signal_agent",
    )

    assert result.ok is False
    assert result.status == "OWNER_APPROVAL_REQUIRED"


def test_telegram_signal_command_keeps_owner_approval_gate(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    calls: list[dict] = []

    result = handle_master_command_text(
        text="/master run signal",
        telegram_user_id=1001,
        chat_id=55,
        runner=lambda **kwargs: calls.append(kwargs),
    )

    assert result.status == "OWNER_APPROVAL_REQUIRED"
    assert "explicit approval" in (result.response_text or "")
    assert calls == []


def test_safe_telegram_run_forwards_injected_supabase(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    injected_supabase = object()
    calls: list[dict] = []

    result = handle_master_command_text(
        text="/master run image",
        telegram_user_id=1001,
        chat_id=55,
        supabase=injected_supabase,
        runner=lambda **kwargs: calls.append(kwargs) or Progress(),
    )

    assert result.status == "COMPLETED"
    assert calls[0]["supabase"] is injected_supabase
