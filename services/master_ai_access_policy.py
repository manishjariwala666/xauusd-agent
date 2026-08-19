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
    "list_registered_agents": MasterAIActionPolicy(
        "list_registered_agents",
        ApprovalLevel.AUTOMATIC,
        "List registered VenusRealm agents without exposing internal configuration.",
    ),
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

    # Safe internal/draft agent execution
    "run_blog_agent": MasterAIActionPolicy(
        "run_blog_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare and save a blog draft; publishing remains locked.",
    ),
    "run_image_agent": MasterAIActionPolicy(
        "run_image_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare internal image assets without publishing them.",
    ),
    "run_market_data_agent": MasterAIActionPolicy(
        "run_market_data_agent",
        ApprovalLevel.AUTOMATIC,
        "Validate supplied approved XAUUSD market data without generating a signal.",
    ),
    "run_customer_support_agent": MasterAIActionPolicy(
        "run_customer_support_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare safe customer guidance and lead qualification without sending messages or changing accounts.",
    ),
    "run_marketing_strategy_agent": MasterAIActionPolicy(
        "run_marketing_strategy_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare a marketing campaign plan for already-published content without starting a campaign.",
    ),
    "run_social_media_agent": MasterAIActionPolicy(
        "run_social_media_agent",
        ApprovalLevel.AUTOMATIC,
        "Prepare social-media drafts without posting or sending them.",
    ),
    "run_cms_editor_agent": MasterAIActionPolicy(
        "run_cms_editor_agent",
        ApprovalLevel.AUTOMATIC,
        "Create a Studio V2 draft only; publishing and scheduling remain locked.",
    ),
    "run_master_ai_content_review_agent": MasterAIActionPolicy(
        "run_master_ai_content_review_agent",
        ApprovalLevel.AUTOMATIC,
        "Perform read-only publish-readiness review of a CMS draft.",
    ),
    "retry_failed_agent": MasterAIActionPolicy(
        "retry_failed_agent",
        ApprovalLevel.AUTOMATIC,
        "Retry an approved automatic agent within configured retry limits.",
    ),

    # Real external or consequential agent execution
    "run_signal_agent": MasterAIActionPolicy(
        "run_signal_agent",
        ApprovalLevel.OWNER_APPROVAL,
        "Run the Signal Agent, which may publish or deliver a real signal.",
    ),
    "disable_signal_agent": MasterAIActionPolicy(
        "disable_signal_agent",
        ApprovalLevel.OWNER_APPROVAL,
        "Disable or stop the Signal Agent only after explicit owner approval.",
    ),
    "run_whatsapp_reply_agent": MasterAIActionPolicy(
        "run_whatsapp_reply_agent",
        ApprovalLevel.OWNER_APPROVAL,
        "Run the WhatsApp Reply Agent, which may send a real client message.",
    ),
    "run_telegram_reply_agent": MasterAIActionPolicy(
        "run_telegram_reply_agent",
        ApprovalLevel.OWNER_APPROVAL,
        "Run the Telegram Reply Agent, which may send a real client message.",
    ),
    "run_master_ai_publish_approval_agent": MasterAIActionPolicy(
        "run_master_ai_publish_approval_agent",
        ApprovalLevel.OWNER_APPROVAL,
        "Publish one reviewed CMS draft only after explicit owner approval.",
    ),
    "run_announcement_agent": MasterAIActionPolicy(
        "run_announcement_agent",
        ApprovalLevel.OWNER_APPROVAL,
        "Run an announcement that may deliver real Telegram or WhatsApp messages.",
    ),
    "send_health_report": MasterAIActionPolicy(
        "send_health_report",
        ApprovalLevel.OWNER_APPROVAL,
        "Send the owner a private system health report through an external channel.",
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
