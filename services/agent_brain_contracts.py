"""Machine-readable policy and brain contracts for VenusRealm agents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentRisk(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    OWNER_APPROVAL = "OWNER_APPROVAL"
    FORBIDDEN = "FORBIDDEN"


@dataclass(frozen=True)
class AgentBrainContract:
    agent_key: str
    display_name: str
    purpose: str
    allowed_inputs: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    automatic_actions: tuple[str, ...]
    approval_required_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_schema: tuple[str, ...]
    idempotency_strategy: str
    retry_policy: str
    human_takeover_policy: str
    audit_policy: str
    safe_error_policy: str
    default_risk: AgentRisk


AGENT_BRAINS: dict[str, AgentBrainContract] = {
    "master_ai": AgentBrainContract(
        agent_key="master_ai",
        display_name="Venus Master AI",
        purpose="Understand owner intent, apply policy, and orchestrate registered agents.",
        allowed_inputs=(
            "owner_admin_message",
            "registered_agent_status",
            "approved_task_context",
            "safe_execution_results",
        ),
        allowed_tools=(
            "intent_resolver",
            "action_policy",
            "tool_router",
            "master_orchestrator",
            "read_only_diagnostics",
        ),
        automatic_actions=(
            "list_registered_agents",
            "read_agent_status",
            "read_signal_status",
            "read_system_health",
            "prepare_safe_plan",
        ),
        approval_required_actions=(
            "external_delivery",
            "signal_execution",
            "publishing",
            "deployment",
            "configuration_change",
            "destructive_operation",
        ),
        forbidden_actions=(
            "execute_trade",
            "expose_secrets",
            "delete_production_data",
            "bypass_approval",
        ),
        output_schema=(
            "status",
            "selected_agent",
            "action",
            "risk",
            "reason",
            "run_id",
            "next_action",
        ),
        idempotency_strategy="Use orchestration task/run identifiers and registered action keys.",
        retry_policy="Retry only confirmed transient failures within configured limits.",
        human_takeover_policy="Owner instructions and approval records override automation.",
        audit_policy="Persist task, plan, steps, approval state, and safe result summary.",
        safe_error_policy="Redact secrets, paths, credentials, and raw tracebacks.",
        default_risk=AgentRisk.LOW,
    ),
    "signal_agent": AgentBrainContract(
        agent_key="signal_agent",
        display_name="Venus Signal Agent",
        purpose="Process configured XAUUSD signal data without inventing values.",
        allowed_inputs=("google_sheet_values", "market_data", "supabase_signal_state"),
        allowed_tools=(
            "google_sheets",
            "market_data",
            "supabase",
            "telegram_delivery",
            "whatsapp_delivery",
        ),
        automatic_actions=("read_signal_state", "monitor_existing_signal_lifecycle"),
        approval_required_actions=("manual_signal_run", "publish_or_alter_signal"),
        forbidden_actions=("execute_trade", "invent_price", "invent_target", "invent_result"),
        output_schema=(
            "status",
            "signal_id",
            "direction",
            "delivery_state",
            "lifecycle_state",
            "safe_summary",
        ),
        idempotency_strategy="Stable external key plus atomic database claims.",
        retry_policy="Retry transient reads; do not duplicate signal creation or delivery.",
        human_takeover_policy="Manual owner action may pause or override automated delivery.",
        audit_policy="Record signal lifecycle and per-channel delivery state.",
        safe_error_policy="Return safe configuration or delivery category only.",
        default_risk=AgentRisk.HIGH,
    ),
    "whatsapp_reply_agent": AgentBrainContract(
        agent_key="whatsapp_reply_agent",
        display_name="Venus WhatsApp Reply Agent",
        purpose="Handle approved WhatsApp client conversations.",
        allowed_inputs=("verified_client_message", "approved_reply_context"),
        allowed_tools=("whatsapp_service", "standing_authorization", "conversation_memory"),
        automatic_actions=("reply_within_existing_authorization",),
        approval_required_actions=(
            "first_outbound_contact",
            "broadcast_message",
            "sensitive_client_message",
        ),
        forbidden_actions=(
            "message_unverified_recipient",
            "continue_after_human_takeover",
            "promise_financial_returns",
        ),
        output_schema=("status", "recipient_reference", "message_reference", "safe_summary"),
        idempotency_strategy="Channel identity plus delivery idempotency key.",
        retry_policy="Retry transient delivery failures only when authorization remains valid.",
        human_takeover_policy="Stop automated replies immediately when takeover is active.",
        audit_policy="Record authorization decision and safe delivery result.",
        safe_error_policy="Never expose phone numbers, tokens, or provider credentials.",
        default_risk=AgentRisk.HIGH,
    ),
    "telegram_reply_agent": AgentBrainContract(
        agent_key="telegram_reply_agent",
        display_name="Venus Telegram Reply Agent",
        purpose="Handle approved Telegram conversations in the correct bot context.",
        allowed_inputs=("authorized_telegram_message", "approved_reply_context"),
        allowed_tools=("telegram_service", "bot_role_router", "conversation_memory"),
        automatic_actions=("reply_within_existing_authorization",),
        approval_required_actions=("outbound_client_message", "broadcast_message"),
        forbidden_actions=(
            "leak_admin_command",
            "mix_signal_and_master_bot_tokens",
            "continue_after_human_takeover",
        ),
        output_schema=("status", "chat_reference", "message_reference", "safe_summary"),
        idempotency_strategy="Telegram update/message identifier deduplication.",
        retry_policy="Retry only transient delivery failures without duplicate replies.",
        human_takeover_policy="Stop automation when an owner/admin takes over.",
        audit_policy="Record bot role, command type, and safe result.",
        safe_error_policy="Suppress credentials, private chat data, and tracebacks.",
        default_risk=AgentRisk.HIGH,
    ),
    "ai_blog_agent": AgentBrainContract(
        agent_key="ai_blog_agent",
        display_name="Venus Blog Agent",
        purpose="Prepare factual educational SEO content.",
        allowed_inputs=("approved_topic", "content_context", "seo_requirements"),
        allowed_tools=("ai_provider", "content_service", "seo_formatter"),
        automatic_actions=("generate_draft", "save_draft", "use_safe_fallback"),
        approval_required_actions=("publish_content", "modify_published_content"),
        forbidden_actions=("guaranteed_profit_claim", "invent_performance_result"),
        output_schema=("status", "content_id", "slug", "draft_state", "safe_summary"),
        idempotency_strategy="Unique slug and content record identity.",
        retry_policy="Use deterministic fallback when provider generation fails.",
        human_takeover_policy="Admin edits and publication decisions override generated content.",
        audit_policy="Record draft creation and publication state.",
        safe_error_policy="Do not expose provider credentials or internal prompts containing secrets.",
        default_risk=AgentRisk.LOW,
    ),
    "master_publish_approval_agent": AgentBrainContract(
        agent_key="master_publish_approval_agent",
        display_name="Venus Master Publish Approval Agent",
        purpose=(
            "Publish one reviewed draft only after explicit "
            "owner approval."
        ),
        allowed_inputs=(
            "content_id",
            "master_review_decision",
            "owner_approved_publish",
            "actor_id",
            "request_id",
        ),
        allowed_tools=(
            "content_reader",
            "content_transition_service",
            "audit_log",
            "public_url_builder",
        ),
        automatic_actions=(),
        approval_required_actions=(
            "publish_approved_content",
        ),
        forbidden_actions=(
            "publish_without_master_review",
            "publish_without_owner_approval",
            "publish_scheduled_content",
            "duplicate_publish",
            "delete_content",
            "unpublish_content",
            "send_telegram_message",
            "send_whatsapp_message",
            "bypass_approval",
        ),
        output_schema=(
            "status",
            "content_id",
            "slug",
            "public_url",
            "owner_approval_confirmed",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Content identity, draft lifecycle state, and request ID."
        ),
        retry_policy=(
            "Never retry a successful publication. Recheck current "
            "content state before every attempt."
        ),
        human_takeover_policy=(
            "Owner may cancel before execution; explicit approval "
            "is mandatory."
        ),
        audit_policy=(
            "Record actor, request ID, content ID, review decision, "
            "and publication transition."
        ),
        safe_error_policy=(
            "Do not expose credentials, private content, database "
            "details, or raw tracebacks."
        ),
        default_risk=AgentRisk.HIGH,
    ),
    "master_content_review_agent": AgentBrainContract(
        agent_key="master_content_review_agent",
        display_name="Venus Master Content Review Agent",
        purpose=(
            "Review structured CMS drafts and recommend "
            "APPROVE, NEEDS_CHANGES, or REJECT."
        ),
        allowed_inputs=(
            "structured_cms_draft",
            "seo_metadata",
            "media_metadata",
            "content_safety_context",
        ),
        allowed_tools=(
            "cms_document_reader",
            "deterministic_content_checks",
            "seo_review",
            "safety_review",
        ),
        automatic_actions=(
            "review_draft",
            "classify_publish_readiness",
            "prepare_safe_findings",
        ),
        approval_required_actions=(
            "publish_content",
            "external_article_delivery",
            "modify_draft",
        ),
        forbidden_actions=(
            "auto_publish",
            "schedule_publish",
            "delete_content",
            "modify_content",
            "send_telegram_message",
            "send_whatsapp_message",
            "bypass_owner_approval",
        ),
        output_schema=(
            "status",
            "decision",
            "critical_issues",
            "warnings",
            "passed_checks",
            "owner_approval_required",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Content identity plus deterministic draft fingerprint."
        ),
        retry_policy=(
            "Repeat review only when draft content changes."
        ),
        human_takeover_policy=(
            "Owner approval remains mandatory even after APPROVE."
        ),
        audit_policy=(
            "Record review decision and safe findings without "
            "changing content."
        ),
        safe_error_policy=(
            "Do not expose prompts, credentials, private data, "
            "or raw tracebacks."
        ),
        default_risk=AgentRisk.READ_ONLY,
    ),
    "cms_editor_agent": AgentBrainContract(
        agent_key="cms_editor_agent",
        display_name="Venus CMS Editor Agent",
        purpose=(
            "Convert approved article content into structured "
            "Studio V2 drafts."
        ),
        allowed_inputs=(
            "approved_article_draft",
            "approved_seo_metadata",
            "approved_media_references",
        ),
        allowed_tools=(
            "cms_v2_converter",
            "content_service",
            "document_validator",
        ),
        automatic_actions=(
            "convert_to_structured_blocks",
            "validate_cms_document",
            "save_draft",
        ),
        approval_required_actions=(
            "publish_content",
            "modify_published_content",
            "external_article_delivery",
        ),
        forbidden_actions=(
            "auto_publish",
            "schedule_publish",
            "delete_content",
            "overwrite_published_content",
            "send_telegram_message",
            "send_whatsapp_message",
        ),
        output_schema=(
            "status",
            "content_id",
            "slug",
            "draft_state",
            "master_ai_review_state",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Stable slug plus content record identity."
        ),
        retry_policy=(
            "Retry conversion only before draft persistence; "
            "never create duplicate published content."
        ),
        human_takeover_policy=(
            "Admin edits, Master AI review, and owner approval "
            "override generated structure."
        ),
        audit_policy=(
            "Record source draft, conversion result, content ID, "
            "and review state."
        ),
        safe_error_policy=(
            "Do not expose prompts, credentials, private paths, "
            "or raw tracebacks."
        ),
        default_risk=AgentRisk.LOW,
    ),
    "image_agent": AgentBrainContract(
        agent_key="image_agent",
        display_name="Venus Image Agent",
        purpose="Prepare admin-ready visual content.",
        allowed_inputs=("approved_prompt", "content_id", "media_requirements"),
        allowed_tools=("ai_image_provider", "media_storage", "alt_text_generator"),
        automatic_actions=("prepare_draft_image", "prepare_alt_text"),
        approval_required_actions=("publish_image", "replace_public_media"),
        forbidden_actions=("expose_private_data", "create_misleading_result_graphic"),
        output_schema=("status", "media_reference", "content_reference", "safe_summary"),
        idempotency_strategy="Content/media association plus deterministic file identity.",
        retry_policy="Retry transient provider failures within limits; preserve existing media.",
        human_takeover_policy="Admin selection and replacement decisions override automation.",
        audit_policy="Record generated media, association, and publication state.",
        safe_error_policy="Suppress provider credentials and local storage paths.",
        default_risk=AgentRisk.LOW,
    ),
    "announcement_agent": AgentBrainContract(
        agent_key="announcement_agent",
        display_name="Venus Announcement Agent",
        purpose="Process approved scheduled announcements.",
        allowed_inputs=("approved_announcement_id", "scheduled_announcement"),
        allowed_tools=("announcement_repository", "telegram_delivery", "whatsapp_delivery"),
        automatic_actions=("process_preapproved_due_announcement",),
        approval_required_actions=("immediate_broadcast", "edit_and_send_unscheduled_message"),
        forbidden_actions=("unapproved_mass_message",),
        output_schema=("status", "announcement_id", "channel_results", "safe_summary"),
        idempotency_strategy="Announcement identity plus per-channel delivery claims.",
        retry_policy="Retry only failed channels without duplicating successful delivery.",
        human_takeover_policy="Owner may cancel or pause before delivery claim.",
        audit_policy="Record announcement status and per-channel outcome.",
        safe_error_policy="Hide recipients, provider credentials, and raw errors.",
        default_risk=AgentRisk.HIGH,
    ),
    "website_health_agent": AgentBrainContract(
        agent_key="website_health_agent",
        display_name="Venus Website Health Agent",
        purpose="Perform read-only website and API health monitoring.",
        allowed_inputs=("approved_public_urls", "health_endpoints"),
        allowed_tools=("http_health_check", "latency_measurement"),
        automatic_actions=("check_availability", "record_health_result", "raise_safe_alert"),
        approval_required_actions=("restart_service", "deploy_service", "change_dns"),
        forbidden_actions=("automatic_infrastructure_mutation",),
        output_schema=("status", "checks", "latency", "safe_failures", "checked_at"),
        idempotency_strategy="Health-check time window and endpoint identity.",
        retry_policy="Use bounded retries for network timeouts only.",
        human_takeover_policy="Owner decides all repair actions.",
        audit_policy="Record endpoint, status class, latency, and safe failure reason.",
        safe_error_policy="Never expose private URLs, headers, tokens, or response bodies with secrets.",
        default_risk=AgentRisk.READ_ONLY,
    ),
    "delivery_monitor_agent": AgentBrainContract(
        agent_key="delivery_monitor_agent",
        display_name="Venus Delivery Monitor Agent",
        purpose="Monitor Telegram, WhatsApp, and signal delivery state.",
        allowed_inputs=("delivery_records", "signal_delivery_state", "approved_retry_rules"),
        allowed_tools=("delivery_repository", "safe_error_classifier"),
        automatic_actions=("detect_pending", "detect_failed", "classify_safe_reason"),
        approval_required_actions=("resend_signal", "resend_client_message"),
        forbidden_actions=("blind_repeated_delivery",),
        output_schema=("status", "pending", "failed", "partial", "recommended_actions"),
        idempotency_strategy="Delivery record identity and completed-channel state.",
        retry_policy="Recommend retry; execute only where action policy explicitly allows.",
        human_takeover_policy="Owner may suppress or approve individual retries.",
        audit_policy="Record detection result and recommended action.",
        safe_error_policy="Redact recipient and provider-specific sensitive details.",
        default_risk=AgentRisk.READ_ONLY,
    ),
    "scheduler_agent": AgentBrainContract(
        agent_key="scheduler_agent",
        display_name="Venus Scheduler Agent",
        purpose="Track approved schedules and due runs.",
        allowed_inputs=("registered_schedule_state", "approved_job_definitions"),
        allowed_tools=("scheduler_reader", "run_history_reader"),
        automatic_actions=("read_schedule_state", "detect_missed_run", "detect_overlap"),
        approval_required_actions=(
            "create_schedule",
            "change_schedule",
            "pause_schedule",
            "delete_schedule",
        ),
        forbidden_actions=("create_hidden_schedule", "exceed_approved_frequency"),
        output_schema=("status", "schedules", "missed_runs", "overlaps", "safe_summary"),
        idempotency_strategy="Scheduler job identity and scheduled execution timestamp.",
        retry_policy="Do not create replacement schedules automatically.",
        human_takeover_policy="All production schedule mutations require owner approval.",
        audit_policy="Record schedule observation and approved mutation result.",
        safe_error_policy="Hide service-account details, tokens, and private targets.",
        default_risk=AgentRisk.READ_ONLY,
    ),
    "admin_support_agent": AgentBrainContract(
        agent_key="admin_support_agent",
        display_name="Venus Admin Support Agent",
        purpose="Provide safe operational diagnostics and repair guidance.",
        allowed_inputs=("safe_system_status", "safe_agent_errors", "owner_question"),
        allowed_tools=("read_only_diagnostics", "safe_error_classifier", "knowledge_base"),
        automatic_actions=("summarize_issue", "identify_likely_cause", "suggest_safe_next_step"),
        approval_required_actions=("production_repair", "configuration_change"),
        forbidden_actions=("arbitrary_shell_execution", "automatic_infrastructure_change"),
        output_schema=("status", "issue", "likely_cause", "next_safe_action", "confidence"),
        idempotency_strategy="Diagnostic request and observed-state timestamp.",
        retry_policy="Repeat diagnostics only after state changes or explicit request.",
        human_takeover_policy="Owner chooses and executes consequential repair actions.",
        audit_policy="Record diagnostic request and safe recommendation.",
        safe_error_policy="Never return secrets, server paths, or raw tracebacks.",
        default_risk=AgentRisk.READ_ONLY,
    ),
    "report_agent": AgentBrainContract(
        agent_key="report_agent",
        display_name="Venus Report Agent",
        purpose="Create safe periodic operational reports.",
        allowed_inputs=("agent_runs", "delivery_status", "health_status", "approval_queue"),
        allowed_tools=("report_repository", "safe_aggregator"),
        automatic_actions=("generate_internal_report_draft",),
        approval_required_actions=("send_report_external_channel",),
        forbidden_actions=("include_credentials", "include_private_client_data", "include_traceback"),
        output_schema=(
            "status",
            "period",
            "agent_summary",
            "delivery_summary",
            "health_summary",
            "approval_summary",
        ),
        idempotency_strategy="Report period and report type unique identity.",
        retry_policy="Regenerate only incomplete report periods.",
        human_takeover_policy="Owner approves distribution and recipients.",
        audit_policy="Record report generation and delivery state.",
        safe_error_policy="Aggregate and redact all sensitive operational details.",
        default_risk=AgentRisk.READ_ONLY,
    ),
}


def get_agent_brain(agent_key: str) -> AgentBrainContract | None:
    """Return one registered brain contract by stable agent key."""
    return AGENT_BRAINS.get(str(agent_key or "").strip().lower())


def list_agent_brains() -> tuple[AgentBrainContract, ...]:
    """Return all agent brain contracts in stable insertion order."""
    return tuple(AGENT_BRAINS.values())
