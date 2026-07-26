"""Controlled tool router for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from services.master_ai_access_policy import (
    ApprovalLevel,
    get_action_policy,
)
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
        "objective": (
            "Run the existing XAUUSD Signal Agent using configured "
            "Google Sheet data. Do not invent or alter signal values."
        ),
    },
    "run_whatsapp_reply_agent": {
        "task_type": "WHATSAPP_REPLY",
        "title": "Run WhatsApp Reply Agent",
        "objective": "Process pending WhatsApp replies using existing rules.",
    },
    "run_telegram_reply_agent": {
        "task_type": "TELEGRAM_REPLY",
        "title": "Run Telegram Reply Agent",
        "objective": "Process pending Telegram replies using existing rules.",
    },
    "run_blog_agent": {
        "task_type": "BLOG",
        "title": "Prepare Blog Content",
        "agent_key": "ai_blog_agent",
        "objective": (
            "Prepare admin-ready blog content. Do not publish automatically."
        ),
        "safe_payload": {
            "publish": False,
            "include_image": False,
        },
    },
    "run_image_agent": {
        "task_type": "IMAGE",
        "title": "Prepare Image Content",
        "agent_key": "image_agent",
        "objective": (
            "Prepare admin-ready image content. Do not publish automatically."
        ),
        "safe_payload": {},
    },
}

FAILED_STATUSES = {"BLOCKED", "CANCELLED", "ERROR", "FAILED"}
UNSAFE_ERROR_MARKERS = (
    "traceback",
    "token=",
    "secret=",
    "password=",
    "api_key=",
    "apikey=",
    "authorization=",
    "credential=",
    "cookie=",
    "jwt=",
    "bearer ",
    "postgres://",
    "postgresql://",
    "/app/",
    "/home/",
    "/users/",
    "/private/",
    "/var/",
    "c:\\",
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
    """Execute one policy-approved agent action."""

    clean_action = str(action or "").strip().lower()
    policy = get_action_policy(clean_action)

    if policy is None:
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status="UNKNOWN_ACTION",
            message="Unknown Master AI action.",
        )

    if policy.approval == ApprovalLevel.FORBIDDEN:
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status="FORBIDDEN",
            message="This action is permanently blocked.",
        )

    if policy.approval == ApprovalLevel.OWNER_APPROVAL:
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status="OWNER_APPROVAL_REQUIRED",
            message="Owner ki explicit approval required hai.",
        )

    if clean_action == "list_registered_agents":
        return MasterAIToolResult(
            ok=True,
            action=clean_action,
            status="COMPLETED",
            message=format_agent_directory(),
        )

    if clean_action in {
        "read_agent_status",
        "read_signal_status",
        "read_system_health",
    }:
        if status_loader is None:
            return MasterAIToolResult(
                ok=False,
                action=clean_action,
                status="CONFIGURATION_REQUIRED",
                message=(
                    "Read-only diagnostic loader configured nahi hai.\n"
                    "Next action: registered status loader configure karke retry karein."
                ),
            )
        try:
            rows = status_loader()
        except Exception as exc:
            reason = safe_master_reason(exc) or "Diagnostic status unavailable."
            return _failed_result(clean_action, "ERROR", reason)
        return MasterAIToolResult(
            ok=True,
            action=clean_action,
            status="COMPLETED",
            message=_format_safe_diagnostics(rows),
        )

    if clean_action == "retry_failed_agent":
        target = str(retry_action or "").strip().lower()
        target_policy = get_action_policy(target)
        if not target_policy:
            return MasterAIToolResult(
                ok=False,
                action=clean_action,
                status="UNKNOWN_ACTION",
                message="Retry target registered nahi hai.",
            )
        if target_policy.approval != ApprovalLevel.AUTOMATIC:
            return MasterAIToolResult(
                ok=False,
                action=clean_action,
                status="OWNER_APPROVAL_REQUIRED",
                message="Is agent retry ke liye owner ki explicit approval required hai.",
            )
        return execute_master_ai_action(
            target,
            source=source,
            runner=runner,
            input_payload=input_payload,
            status_loader=status_loader,
            supabase=supabase,
        )

    task = TASKS.get(clean_action)
    if task is None:
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status="NOT_IMPLEMENTED",
            message="Action policy me allowed hai, lekin router tool pending hai.",
        )

    try:
        payload = {
            "objective": task["objective"],
            "master_ai_action": clean_action,
            "automatic_execution": True,
            "agent_keys": [task["agent_key"]],
            **dict(task.get("safe_payload") or {}),
            **dict(input_payload or {}),
        }
        # Safety controls owned by the router cannot be weakened by caller data.
        payload.update(task.get("safe_payload") or {})
        payload["agent_keys"] = [task["agent_key"]]
        progress = runner(
            task_type=task["task_type"],
            title=task["title"],
            source=source,
            requested_by=None,
            input_payload=payload,
            supabase=supabase,
        )
    except Exception as exc:
        safe_reason = safe_master_reason(exc) or "Agent start nahi hua."
        return _failed_result(clean_action, "ERROR", safe_reason)

    status = str(getattr(progress, "status", "ACCEPTED") or "ACCEPTED").upper()
    run_id = getattr(progress, "run_id", None)
    if status in FAILED_STATUSES:
        reason = safe_master_reason(
            getattr(progress, "safe_error", None)
            or getattr(progress, "final_summary", None)
        ) or "Registered agent failed without a safe error summary."
        return _failed_result(clean_action, status, reason, run_id=run_id)
    if status == "WAITING_APPROVAL":
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status=status,
            message="Owner approval record complete hone ke baad action continue hoga.",
            run_id=run_id,
        )

    summary = safe_master_reason(getattr(progress, "final_summary", None))
    return MasterAIToolResult(
        ok=True,
        action=clean_action,
        status=status,
        message=summary or "Master AI orchestration accepted.",
        run_id=run_id,
    )


def _failed_result(
    action: str,
    status: str,
    reason: str,
    *,
    run_id: int | None = None,
) -> MasterAIToolResult:
    safe_reason = safe_master_reason(reason) or "Agent action failed."
    return MasterAIToolResult(
        ok=False,
        action=action,
        status=status,
        message=(
            f"Reason: {safe_reason}\n"
            "Next action: configuration ya required input repair karke retry karein."
        ),
        run_id=run_id,
    )


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
    """Return an actionable reason while suppressing tracebacks and secret-like text."""
    reason = safe_error_message(error)
    if not reason:
        return None
    lowered = reason.lower()
    if any(marker in lowered for marker in UNSAFE_ERROR_MARKERS):
        return "Internal agent configuration failed."
    return reason
