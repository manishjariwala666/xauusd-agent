"""Master AI capability matrix for safe agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CapabilityMode(StrEnum):
    READ = "READ"
    RUN = "RUN"
    APPROVAL = "APPROVAL"
    BLOCKED = "BLOCKED"


class AgentRiskLevel(StrEnum):
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class AgentCapability:
    agent_key: str
    mode: CapabilityMode
    risk: AgentRiskLevel
    owner_approval_required: bool
    allowed_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    dependencies: tuple[str, ...] = ()


MASTER_AI_CAPABILITIES: dict[str, AgentCapability] = {
    "master_ai": AgentCapability(
        agent_key="master_ai",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.HIGH,
        owner_approval_required=True,
        allowed_actions=(
            "inspect_agent_registry",
            "inspect_agent_status",
            "prepare_execution_plan",
            "request_owner_approval",
        ),
        blocked_actions=(
            "direct_trade_execution",
            "direct_message_send",
            "direct_database_write",
            "direct_signal_publish",
            "direct_infrastructure_change",
        ),
    ),
    "signal_agent": AgentCapability(
        agent_key="signal_agent",
        mode=CapabilityMode.RUN,
        risk=AgentRiskLevel.MEDIUM,
        owner_approval_required=False,
        allowed_actions=(
            "run_frozen_signal_pipeline",
            "read_google_sheet_signal",
            "store_signal",
            "deliver_signal",
        ),
        blocked_actions=(
            "modify_signal_logic",
            "change_stop_loss_rules",
            "change_frozen_release",
        ),
        dependencies=("market_data_agent",),
    ),
    "market_data_agent": AgentCapability(
        agent_key="market_data_agent",
        mode=CapabilityMode.RUN,
        risk=AgentRiskLevel.LOW,
        owner_approval_required=False,
        allowed_actions=(
            "read_market_snapshot",
            "validate_market_price",
            "return_normalized_market_data",
        ),
        blocked_actions=(
            "publish_signal",
            "execute_trade",
            "write_signal_logic",
        ),
    ),
    "macro_ai_agent": AgentCapability(
        agent_key="macro_ai_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=True,
        allowed_actions=(
            "calculate_macro_bias",
            "calculate_confidence",
            "report_conflict",
        ),
        blocked_actions=(
            "block_signal_automatically",
            "publish_signal",
            "send_message",
            "execute_trade",
        ),
        dependencies=("market_data_agent",),
    ),
    "economic_calendar_ai_agent": AgentCapability(
        agent_key="economic_calendar_ai_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=True,
        allowed_actions=(
            "classify_event",
            "calculate_event_surprise",
            "recommend_news_lock",
        ),
        blocked_actions=(
            "activate_news_lock",
            "publish_signal",
            "send_message",
            "execute_trade",
        ),
    ),
    "ai_blog_agent": AgentCapability(
        agent_key="ai_blog_agent",
        mode=CapabilityMode.APPROVAL,
        risk=AgentRiskLevel.MEDIUM,
        owner_approval_required=True,
        allowed_actions=(
            "prepare_blog_draft",
            "prepare_seo_metadata",
        ),
        blocked_actions=(
            "publish_without_approval",
            "send_external_message",
        ),
    ),
    "cms_editor_agent": AgentCapability(
        agent_key="cms_editor_agent",
        mode=CapabilityMode.APPROVAL,
        risk=AgentRiskLevel.HIGH,
        owner_approval_required=True,
        allowed_actions=(
            "prepare_structured_draft",
            "validate_content_fields",
        ),
        blocked_actions=(
            "publish_without_approval",
            "delete_content",
        ),
        dependencies=("ai_blog_agent",),
    ),
    "master_content_review_agent": AgentCapability(
        agent_key="master_content_review_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=False,
        allowed_actions=(
            "review_draft",
            "report_publish_readiness",
        ),
        blocked_actions=(
            "publish_content",
            "modify_content",
        ),
        dependencies=("cms_editor_agent",),
    ),
    "master_publish_approval_agent": AgentCapability(
        agent_key="master_publish_approval_agent",
        mode=CapabilityMode.APPROVAL,
        risk=AgentRiskLevel.CRITICAL,
        owner_approval_required=True,
        allowed_actions=(
            "publish_owner_approved_draft",
        ),
        blocked_actions=(
            "publish_without_owner_approval",
            "bulk_publish",
        ),
        dependencies=("master_content_review_agent",),
    ),
    "image_agent": AgentCapability(
        agent_key="image_agent",
        mode=CapabilityMode.APPROVAL,
        risk=AgentRiskLevel.MEDIUM,
        owner_approval_required=True,
        allowed_actions=(
            "prepare_image",
            "prepare_thumbnail",
        ),
        blocked_actions=(
            "publish_image_without_approval",
            "delete_media",
        ),
    ),
    "announcement_agent": AgentCapability(
        agent_key="announcement_agent",
        mode=CapabilityMode.APPROVAL,
        risk=AgentRiskLevel.HIGH,
        owner_approval_required=True,
        allowed_actions=("prepare_announcement",),
        blocked_actions=(
            "publish_announcement_without_approval",
            "send_mass_notification",
        ),
    ),
    "marketing_strategy_agent": AgentCapability(
        agent_key="marketing_strategy_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=True,
        allowed_actions=("prepare_marketing_plan",),
        blocked_actions=(
            "launch_campaign",
            "spend_budget",
            "send_campaign",
        ),
    ),
    "social_media_agent": AgentCapability(
        agent_key="social_media_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.LOW,
        owner_approval_required=True,
        allowed_actions=(
            "prepare_social_drafts",
            "prepare_platform_variations",
            "prepare_hashtags",
            "prepare_cta",
        ),
        blocked_actions=(
            "publish_social_post",
            "send_social_message",
            "start_social_campaign",
            "spend_budget",
        ),
        dependencies=("marketing_strategy_agent",),
    ),
    "website_health_agent": AgentCapability(
        agent_key="website_health_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=False,
        allowed_actions=("inspect_website_health",),
        blocked_actions=(
            "restart_service",
            "deploy_code",
            "change_dns",
        ),
    ),
    "delivery_monitor_agent": AgentCapability(
        agent_key="delivery_monitor_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=False,
        allowed_actions=("inspect_delivery_status",),
        blocked_actions=(
            "resend_message",
            "change_delivery_state",
        ),
    ),
    "scheduler_agent": AgentCapability(
        agent_key="scheduler_agent",
        mode=CapabilityMode.APPROVAL,
        risk=AgentRiskLevel.CRITICAL,
        owner_approval_required=True,
        allowed_actions=("prepare_schedule_change",),
        blocked_actions=(
            "change_schedule_without_approval",
            "resume_production_job_without_approval",
        ),
    ),
    "admin_support_agent": AgentCapability(
        agent_key="admin_support_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=False,
        allowed_actions=(
            "inspect_safe_diagnostics",
            "suggest_safe_fix",
        ),
        blocked_actions=(
            "execute_shell",
            "change_configuration",
            "restart_service",
        ),
    ),
    "report_agent": AgentCapability(
        agent_key="report_agent",
        mode=CapabilityMode.READ,
        risk=AgentRiskLevel.READ_ONLY,
        owner_approval_required=False,
        allowed_actions=("generate_internal_report",),
        blocked_actions=("send_external_report",),
    ),
    "customer_support_agent": AgentCapability(
        agent_key="customer_support_agent",
        mode=CapabilityMode.BLOCKED,
        risk=AgentRiskLevel.HIGH,
        owner_approval_required=True,
        allowed_actions=("prepare_support_reply_draft",),
        blocked_actions=(
            "send_customer_reply",
            "access_private_client_data_without_scope",
        ),
    ),
    "telegram_reply_agent": AgentCapability(
        agent_key="telegram_reply_agent",
        mode=CapabilityMode.BLOCKED,
        risk=AgentRiskLevel.HIGH,
        owner_approval_required=True,
        allowed_actions=("prepare_telegram_reply_draft",),
        blocked_actions=("send_telegram_reply",),
    ),
    "whatsapp_reply_agent": AgentCapability(
        agent_key="whatsapp_reply_agent",
        mode=CapabilityMode.BLOCKED,
        risk=AgentRiskLevel.HIGH,
        owner_approval_required=True,
        allowed_actions=("prepare_whatsapp_reply_draft",),
        blocked_actions=("send_whatsapp_reply",),
    ),
}


def get_agent_capability(agent_key: str) -> AgentCapability | None:
    return MASTER_AI_CAPABILITIES.get(
        str(agent_key or "").strip().lower()
    )


def list_agent_capabilities() -> tuple[AgentCapability, ...]:
    return tuple(MASTER_AI_CAPABILITIES.values())
