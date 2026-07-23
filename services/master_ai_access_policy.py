"""Controlled permissions for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApprovalLevel(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    OWNER_APPROVAL = "OWNER_APPROVAL"
    FORBIDDEN = "FORBIDDEN"


@dataclass(frozen=True)
class MasterAIActionPolicy:
    action: str
    approval: ApprovalLevel
    description: str


POLICIES: dict[str, MasterAIActionPolicy] = {
    # Read-only intelligence
    "read_system_health": MasterAIActionPolicy(
        "read_system_health",
        ApprovalLevel.AUTOMATIC,
        "Read website, worker, queue and service health.",
    ),
    "read_signal_status": MasterAIActionPolicy(
        "read_signal_status",
        ApprovalLevel.AUTOMATIC,
        "Read current Sheet/Supabase signal and delivery status.",
    ),
    "read_agent_status": MasterAIActionPolicy(
        "read_agent_status",
        ApprovalLevel.AUTOMATIC,
        "Read enabled state, last run, queue and last error.",
    ),

    # Safe operational commands
    "run_signal_agent": MasterAIActionPolicy(
        "run_signal_agent",
        ApprovalLevel.AUTOMATIC,
        "Run the existing Signal Agent without changing its calculation.",
    ),
    "run_whatsapp_reply_agent": MasterAIActionPolicy(
        "run_whatsapp_reply_agent",
        ApprovalLevel.AUTOMATIC,
        "Run the existing WhatsApp Reply Agent.",
    ),
    "run_telegram_reply_agent": MasterAIActionPolicy(
        "run_telegram_reply_agent",
        ApprovalLevel.AUTOMATIC,
        "Run the existing Telegram Reply Agent.",
    ),
    "run_blog_agent": MasterAIActionPolicy(
        "run_blog_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare blog content through the existing agent.",
    ),
    "run_image_agent": MasterAIActionPolicy(
        "run_image_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare image content through the existing agent.",
    ),
    "retry_failed_agent": MasterAIActionPolicy(
        "retry_failed_agent",
        ApprovalLevel.AUTOMATIC,
        "Retry an approved failed agent within configured retry limits.",
    ),
    "send_health_report": MasterAIActionPolicy(
        "send_health_report",
        ApprovalLevel.AUTOMATIC,
        "Send the owner a private system health report.",
    ),

    # Consequential operations
    "publish_website": MasterAIActionPolicy(
        "publish_website",
        ApprovalLevel.OWNER_APPROVAL,
        "Publish website content or deployment.",
    ),
    "publish_signal": MasterAIActionPolicy(
        "publish_signal",
        ApprovalLevel.OWNER_APPROVAL,
        "Manually publish or alter a trading signal.",
    ),
    "restart_railway": MasterAIActionPolicy(
        "restart_railway",
        ApprovalLevel.OWNER_APPROVAL,
        "Restart or redeploy a Railway production service.",
    ),
    "change_dns": MasterAIActionPolicy(
        "change_dns",
        ApprovalLevel.OWNER_APPROVAL,
        "Change production DNS or domain routing.",
    ),
    "database_migration": MasterAIActionPolicy(
        "database_migration",
        ApprovalLevel.OWNER_APPROVAL,
        "Apply a production database migration.",
    ),
    "modify_environment": MasterAIActionPolicy(
        "modify_environment",
        ApprovalLevel.OWNER_APPROVAL,
        "Modify environment variables or service configuration.",
    ),

    # Never permitted
    "execute_trade": MasterAIActionPolicy(
        "execute_trade",
        ApprovalLevel.FORBIDDEN,
        "Master AI must never execute financial trades.",
    ),
    "expose_secrets": MasterAIActionPolicy(
        "expose_secrets",
        ApprovalLevel.FORBIDDEN,
        "Master AI must never expose credentials or secrets.",
    ),
    "delete_production_data": MasterAIActionPolicy(
        "delete_production_data",
        ApprovalLevel.FORBIDDEN,
        "Master AI must never delete production data automatically.",
    ),
}


def get_action_policy(action: str) -> MasterAIActionPolicy | None:
    return POLICIES.get(str(action or "").strip().lower())


def can_execute_automatically(action: str) -> bool:
    policy = get_action_policy(action)
    return bool(policy and policy.approval == ApprovalLevel.AUTOMATIC)


def requires_owner_approval(action: str) -> bool:
    policy = get_action_policy(action)
    return bool(policy and policy.approval == ApprovalLevel.OWNER_APPROVAL)
