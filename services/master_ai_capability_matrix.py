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
        "master_ai", CapabilityMode.READ, AgentRiskLevel.HIGH, True,
        ("inspect_agent_registry", "inspect_agent_status", "prepare_execution_plan", "request_owner_approval"),
        ("direct_trade_execution", "direct_message_send", "direct_database_write", "direct_signal_publish", "direct_infrastructure_change"),
    ),
    "signal_agent": AgentCapability(
        "signal_agent", CapabilityMode.APPROVAL, AgentRiskLevel.HIGH, True,
        ("run_frozen_signal_pipeline", "read_google_sheet_signal", "store_signal", "deliver_signal"),
        ("modify_signal_logic", "change_stop_loss_rules", "change_frozen_release", "manual_run_without_owner_approval"),
        ("market_data_agent",),
    ),
    "market_data_agent": AgentCapability(
        "market_data_agent", CapabilityMode.RUN, AgentRiskLevel.READ_ONLY, False,
        ("read_market_snapshot", "validate_market_price", "return_normalized_market_data"),
        ("publish_signal", "execute_trade", "write_signal_logic", "send_external_message"),
    ),
    "macro_ai_agent": AgentCapability(
        "macro_ai_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, True,
        ("calculate_macro_bias", "calculate_confidence", "report_conflict"),
        ("block_signal_automatically", "publish_signal", "send_message", "execute_trade"),
        ("market_data_agent",),
    ),
    "economic_calendar_ai_agent": AgentCapability(
        "economic_calendar_ai_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, True,
        ("classify_event", "calculate_event_surprise", "recommend_news_lock"),
        ("activate_news_lock", "publish_signal", "send_message", "execute_trade"),
    ),
    "ai_blog_agent": AgentCapability(
        "ai_blog_agent", CapabilityMode.RUN, AgentRiskLevel.LOW, False,
        ("prepare_blog_draft", "prepare_seo_metadata", "save_draft"),
        ("publish_without_approval", "modify_published_content", "send_external_message"),
    ),
    "cms_editor_agent": AgentCapability(
        "cms_editor_agent", CapabilityMode.RUN, AgentRiskLevel.LOW, False,
        ("prepare_structured_draft", "validate_content_fields", "save_draft"),
        ("publish_without_approval", "schedule_publish", "delete_content"),
        ("ai_blog_agent",),
    ),
    "master_content_review_agent": AgentCapability(
        "master_content_review_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, False,
        ("review_draft", "report_publish_readiness"),
        ("publish_content", "modify_content"),
        ("cms_editor_agent",),
    ),
    "master_publish_approval_agent": AgentCapability(
        "master_publish_approval_agent", CapabilityMode.APPROVAL, AgentRiskLevel.CRITICAL, True,
        ("publish_owner_approved_draft",),
        ("publish_without_owner_approval", "bulk_publish", "delete_content"),
        ("master_content_review_agent",),
    ),
    "image_agent": AgentCapability(
        "image_agent", CapabilityMode.RUN, AgentRiskLevel.LOW, False,
        ("prepare_image", "prepare_thumbnail", "associate_draft_media"),
        ("publish_image_without_approval", "replace_public_media", "delete_media"),
    ),
    "announcement_agent": AgentCapability(
        "announcement_agent", CapabilityMode.APPROVAL, AgentRiskLevel.HIGH, True,
        ("process_preapproved_due_announcement", "prepare_announcement"),
        ("publish_announcement_without_approval", "send_mass_notification_without_approval"),
    ),
    "marketing_strategy_agent": AgentCapability(
        "marketing_strategy_agent", CapabilityMode.RUN, AgentRiskLevel.READ_ONLY, False,
        ("prepare_marketing_plan", "recommend_channels", "define_kpis"),
        ("launch_campaign", "spend_budget", "send_campaign", "create_external_backlink"),
    ),
    "social_media_agent": AgentCapability(
        "social_media_agent", CapabilityMode.RUN, AgentRiskLevel.LOW, False,
        ("prepare_social_drafts", "prepare_platform_variations", "prepare_hashtags", "prepare_cta"),
        ("publish_social_post", "send_social_message", "start_social_campaign", "spend_budget"),
        ("marketing_strategy_agent",),
    ),
    "website_health_agent": AgentCapability(
        "website_health_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, False,
        ("inspect_website_health",),
        ("restart_service", "deploy_code", "change_dns"),
    ),
    "delivery_monitor_agent": AgentCapability(
        "delivery_monitor_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, False,
        ("inspect_delivery_status",),
        ("resend_message", "change_delivery_state"),
    ),
    "scheduler_agent": AgentCapability(
        "scheduler_agent", CapabilityMode.APPROVAL, AgentRiskLevel.CRITICAL, True,
        ("inspect_schedule", "prepare_schedule_change"),
        ("change_schedule_without_approval", "resume_production_job_without_approval", "delete_schedule_without_approval"),
    ),
    "admin_support_agent": AgentCapability(
        "admin_support_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, False,
        ("inspect_safe_diagnostics", "suggest_safe_fix"),
        ("execute_shell", "change_configuration", "restart_service"),
    ),
    "report_agent": AgentCapability(
        "report_agent", CapabilityMode.READ, AgentRiskLevel.READ_ONLY, False,
        ("generate_internal_report",),
        ("send_external_report",),
    ),
    "customer_support_agent": AgentCapability(
        "customer_support_agent", CapabilityMode.RUN, AgentRiskLevel.LOW, False,
        ("prepare_support_reply_draft", "qualify_lead", "prepare_escalation_summary"),
        ("send_customer_reply", "modify_account", "process_payment", "provide_trading_signal"),
    ),
    "telegram_reply_agent": AgentCapability(
        "telegram_reply_agent", CapabilityMode.APPROVAL, AgentRiskLevel.HIGH, True,
        ("reply_within_approved_context",),
        ("send_telegram_reply_without_owner_approval", "continue_after_human_takeover"),
    ),
    "whatsapp_reply_agent": AgentCapability(
        "whatsapp_reply_agent", CapabilityMode.APPROVAL, AgentRiskLevel.HIGH, True,
        ("reply_within_standing_authorization",),
        ("send_whatsapp_reply_without_owner_approval", "continue_after_human_takeover"),
    ),
}


def get_agent_capability(agent_key: str) -> AgentCapability | None:
    return MASTER_AI_CAPABILITIES.get(str(agent_key or "").strip().lower())


def list_agent_capabilities() -> tuple[AgentCapability, ...]:
    return tuple(MASTER_AI_CAPABILITIES.values())
