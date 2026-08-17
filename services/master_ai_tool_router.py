"""Controlled tool router for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from services.master_ai_access_policy import ApprovalLevel, get_action_policy
from services.master_ai_agent_registry import format_agent_directory
from services.master_orchestrator import create_and_start_master_task
from services.orchestration_redaction import safe_error_message


@dataclass(frozen=True)
class MasterAIToolResult:
    ok: bool
    action: str
    status: str
    message: str
    run_id: int | None = None


TASKS: dict[str, dict[str, Any]] = {
    "run_signal_agent": {
        "task_type": "SIGNAL",
        "title": "Run Signal Agent",
        "agent_key": "signal_agent",
        "objective": "Run the existing XAUUSD Signal Agent using configured Google Sheet data. Do not invent or alter signal values.",
    },
    "run_whatsapp_reply_agent": {
        "task_type": "WHATSAPP_REPLY",
        "title": "Run WhatsApp Reply Agent",
        "agent_key": "whatsapp_reply_agent",
        "objective": "Process pending WhatsApp replies using existing rules.",
    },
    "run_telegram_reply_agent": {
        "task_type": "TELEGRAM_REPLY",
        "title": "Run Telegram Reply Agent",
        "agent_key": "telegram_reply_agent",
        "objective": "Process pending Telegram replies using existing rules.",
    },
    "run_blog_agent": {
        "task_type": "BLOG",
        "title": "Prepare Blog Content",
        "agent_key": "ai_blog_agent",
        "objective": "Prepare admin-ready blog content. Do not publish automatically.",
        "safe_payload": {"publish": False, "include_image": False},
    },
    "run_image_agent": {
        "task_type": "IMAGE",
        "title": "Prepare Image Content",
        "agent_key": "image_agent",
        "objective": "Prepare admin-ready image content. Do not publish automatically.",
        "safe_payload": {},
    },
}

FAILED_STATUSES = {"BLOCKED", "CANCELLED", "ERROR", "FAILED"}


def _load_completed_step_output(run_id: int, agent_key: str) -> str | None:
    """Load only the verified stored output for the requested worker agent."""
    try:
        from sqlalchemy import text
        from core.database import session_scope

        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT output_summary
                        FROM public.master_ai_execution_steps
                        WHERE run_id = :run_id
                          AND agent_key = :agent_key
                          AND status = 'COMPLETED'
                        ORDER BY finished_at DESC NULLS LAST, id DESC
                        LIMIT 1
                        """
                    ),
                    {"run_id": int(run_id), "agent_key": str(agent_key)},
                )
                .mappings()
                .first()
            )
        if not row:
            return None
        return safe_master_reason(row.get("output_summary"))
    except Exception:
        return None


UNSAFE_ERROR_MARKERS = (
    "traceback", "token=", "secret=", "password=", "api_key=", "apikey=",
    "authorization=", "credential=", "cookie=", "jwt=", "bearer ",
    "postgres://", "postgresql://", "/app/", "/home/", "/users/",
    "/private/", "/var/", "c:\\",
)


def execute_master_ai_action(
    action: str,
    *,
    source: str = "MASTER_AI",
    runner: Callable[..., Any] = create_and_start_master_task,
    input_payload: dict[str, Any] | None = None,
    status_loader: Callable[..., list[dict[str, Any]]] | None = None,
    retry_action: str | None = None,
    supabase: Any | None = None,
) -> MasterAIToolResult:
    """Execute one policy-approved agent action through the shared backend."""
    clean_action = str(action or "").strip().lower()
    policy = get_action_policy(clean_action)
    if policy is None:
        return MasterAIToolResult(False, clean_action, "UNKNOWN_ACTION", "Unknown Master AI action.")
    if policy.approval == ApprovalLevel.FORBIDDEN:
        return MasterAIToolResult(False, clean_action, "FORBIDDEN", "This action is permanently blocked.")
    if policy.approval == ApprovalLevel.OWNER_APPROVAL:
        return MasterAIToolResult(False, clean_action, "OWNER_APPROVAL_REQUIRED", "Owner ki explicit approval required hai.")

    if clean_action == "list_registered_agents":
        return MasterAIToolResult(True, clean_action, "COMPLETED", format_agent_directory())

    if clean_action in {"read_agent_status", "read_signal_status", "read_system_health"}:
        if status_loader is None:
            return MasterAIToolResult(False, clean_action, "CONFIGURATION_REQUIRED", "Read-only diagnostic loader configured nahi hai.\nNext action: registered status loader configure karke retry karein.")
        try:
            rows = status_loader()
        except Exception as exc:
            return _failed_result(clean_action, "ERROR", safe_master_reason(exc) or "Diagnostic status unavailable.")
        return MasterAIToolResult(True, clean_action, "COMPLETED", _format_safe_diagnostics(rows))

    if clean_action == "retry_failed_agent":
        target = str(retry_action or "").strip().lower()
        target_policy = get_action_policy(target)
        if not target_policy:
            return MasterAIToolResult(False, clean_action, "UNKNOWN_ACTION", "Retry target registered nahi hai.")
        if target_policy.approval != ApprovalLevel.AUTOMATIC:
            return MasterAIToolResult(False, clean_action, "OWNER_APPROVAL_REQUIRED", "Is agent retry ke liye owner ki explicit approval required hai.")
        return execute_master_ai_action(target, source=source, runner=runner, input_payload=input_payload, status_loader=status_loader, supabase=supabase)

    task = TASKS.get(clean_action)
    if task is None:
        return MasterAIToolResult(False, clean_action, "NOT_IMPLEMENTED", "Action policy me allowed hai, lekin router tool pending hai.")

    try:
        payload = {
            "objective": task["objective"],
            "master_ai_action": clean_action,
            "automatic_execution": True,
            "agent_keys": [task["agent_key"]],
            **dict(task.get("safe_payload") or {}),
            **dict(input_payload or {}),
        }
        payload["publish"] = False
        payload.pop("owner_approved_publish", None)
        payload["agent_keys"] = [task["agent_key"]]
        progress = runner(
            task_type=task["task_type"], title=task["title"], source=source,
            requested_by=None, input_payload=payload, supabase=supabase,
        )
    except Exception as exc:
        return _failed_result(clean_action, "ERROR", safe_master_reason(exc) or "Agent start nahi hua.")

    status = str(getattr(progress, "status", "ACCEPTED") or "ACCEPTED").upper()
    run_id = getattr(progress, "run_id", None)
    if status in FAILED_STATUSES:
        reason = safe_master_reason(getattr(progress, "safe_error", None) or getattr(progress, "final_summary", None)) or "Registered agent failed without a safe error summary."
        return _failed_result(clean_action, status, reason, run_id=run_id)
    if status == "WAITING_APPROVAL":
        return MasterAIToolResult(False, clean_action, status, "Owner approval record complete hone ke baad action continue hoga.", run_id)

    verified_step_output = None
    if run_id is not None:
        verified_step_output = _load_completed_step_output(int(run_id), str(task["agent_key"]))

    if status == "COMPLETED" and not verified_step_output:
        return _failed_result(
            clean_action,
            "UNVERIFIED_RESULT",
            f"{task['agent_key']} completed state was reported but no verified worker output was stored.",
            run_id=run_id,
        )

    if verified_step_output:
        return MasterAIToolResult(True, clean_action, status, verified_step_output, run_id)

    return MasterAIToolResult(True, clean_action, status, "Master AI orchestration accepted; verified worker result is pending.", run_id)


def _failed_result(action: str, status: str, reason: str, *, run_id: int | None = None) -> MasterAIToolResult:
    safe_reason = safe_master_reason(reason) or "Agent action failed."
    return MasterAIToolResult(False, action, status, f"Reason: {safe_reason}\nNext action: configuration ya required input repair karke retry karein.", run_id)


def _format_safe_diagnostics(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No registered diagnostic records found."
    lines = ["Registered agent diagnostics"]
    for row in rows[:25]:
        name = str(row.get("display_name") or row.get("agent_key") or "Agent")
        status = str(row.get("status") or "UNKNOWN").upper()
        enabled = "ON" if row.get("is_enabled", True) else "OFF"
        line = f"{name}: {status}, enabled={enabled}"
        error = safe_master_reason(row.get("last_error") or row.get("safe_error"))
        if error:
            line += f", reason={error}"
        lines.append(line)
    return "\n".join(lines)


def safe_master_reason(error: BaseException | str | None) -> str | None:
    reason = safe_error_message(error)
    if not reason:
        return None
    lowered = reason.lower()
    if any(marker in lowered for marker in UNSAFE_ERROR_MARKERS):
        return "Internal agent configuration failed."
    return reason
