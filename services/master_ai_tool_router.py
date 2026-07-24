"""Controlled tool router for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from services.master_ai_access_policy import (
    ApprovalLevel,
    get_action_policy,
)
from services.master_orchestrator import create_and_start_master_task


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
        "objective": (
            "Prepare admin-ready blog content. Do not publish automatically."
        ),
    },
    "run_image_agent": {
        "task_type": "IMAGE",
        "title": "Prepare Image Content",
        "objective": (
            "Prepare admin-ready image content. Do not publish automatically."
        ),
    },
}


def execute_master_ai_action(
    action: str,
    *,
    source: str = "MASTER_AI",
    runner: Callable[..., Any] = create_and_start_master_task,
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

    task = TASKS.get(clean_action)
    if task is None:
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status="NOT_IMPLEMENTED",
            message="Action policy me allowed hai, lekin router tool pending hai.",
        )

    try:
        progress = runner(
            task_type=task["task_type"],
            title=task["title"],
            source=source,
            input_payload={
                "master_ai_action": clean_action,
                "automatic_execution": True,
            },
        )
    except Exception as exc:
        return MasterAIToolResult(
            ok=False,
            action=clean_action,
            status="ERROR",
            message=f"Agent start nahi hua: {type(exc).__name__}",
        )

    return MasterAIToolResult(
        ok=True,
        action=clean_action,
        status=str(getattr(progress, "status", "ACCEPTED")),
        message=f"{task['title']} accepted.",
        run_id=getattr(progress, "run_id", None),
    )
