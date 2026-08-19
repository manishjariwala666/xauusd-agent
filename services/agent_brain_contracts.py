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
    "market_data_agent": AgentBrainContract(
        agent_key="market_data_agent",
        display_name="Venus Market Data Agent",
        purpose=(
            "Validate and return current XAUUSD reference or "
            "broker market data without generating signals."
        ),
        allowed_inputs=(
            "symbol",
            "google_finance_sheet_price",
            "approved_broker_price",
            "bid",
            "ask",
            "source",
            "updated_at",
        ),
        allowed_tools=(
            "google_sheets_reader",
            "google_finance_reference_reader",
            "market_data_validator",
            "timestamp_freshness_validator",
            "symbol_normalizer",
        ),
        automatic_actions=(
            "normalize_market_symbol",
            "read_approved_price_snapshot",
            "validate_numeric_price",
            "validate_source",
            "validate_timestamp_freshness",
            "format_verified_market_snapshot",
        ),
        approval_required_actions=(
            "publish_market_price",
            "send_market_price_externally",
            "modify_google_sheet",
            "change_market_data_source",
        ),
        forbidden_actions=(
            "invent_market_price",
            "present_stale_price_as_current",
            "label_google_finance_as_live_broker_data",
            "generate_buy_signal",
            "generate_sell_signal",
            "provide_entry_price",
            "provide_stop_loss",
            "provide_take_profit",
            "provide_trading_advice",
            "place_trade",
            "send_telegram_message",
            "send_whatsapp_message",
        ),
        output_schema=(
            "status",
            "symbol",
            "price",
            "bid",
            "ask",
            "spread",
            "source",
            "source_label",
            "data_class",
            "updated_at",
            "age_seconds",
            "fresh",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Symbol, source and source timestamp identify one "
            "market-data snapshot."
        ),
        retry_policy=(
            "Retry transient read failures only; never reuse stale "
            "data as current."
        ),
        human_takeover_policy=(
            "Owner may override source preference, but freshness "
            "and no-invention rules remain mandatory."
        ),
        audit_policy=(
            "Record symbol, source, timestamp, freshness result "
            "and safe response classification."
        ),
        safe_error_policy=(
            "Return unavailable or stale status without exposing "
            "credentials, sheet identifiers or raw tracebacks."
        ),
        default_risk=AgentRisk.READ_ONLY,
    ),
    "customer_support_agent": AgentBrainContract(
        agent_key="customer_support_agent",
        display_name="Venus Customer Support Agent",
        purpose=(
            "Guide website visitors, qualify new-client leads "
            "and prepare safe human escalation."
        ),
        allowed_inputs=(
            "customer_message",
            "customer_name",
            "email",
            "phone",
            "country",
            "website_context",
        ),
        allowed_tools=(
            "intent_classifier",
            "knowledge_base_reader",
            "lead_qualifier",
            "support_triage",
        ),
        automatic_actions=(
            "answer_general_questions",
            "provide_onboarding_guidance",
            "qualify_lead",
            "prepare_support_summary",
        ),
        approval_required_actions=(
            "create_crm_lead",
            "send_customer_message",
            "escalate_to_human",
            "modify_account",
            "process_billing_request",
        ),
        forbidden_actions=(
            "provide_buy_signal",
            "provide_sell_signal",
            "provide_trading_advice",
            "guarantee_profit",
            "place_trade",
            "reset_password",
            "collect_password",
            "collect_otp",
            "collect_card_details",
            "process_payment",
            "process_refund",
            "delete_account",
            "send_email",
            "send_telegram_message",
            "send_whatsapp_message",
        ),
        output_schema=(
            "status",
            "intent",
            "reply",
            "lead",
            "human_escalation_required",
            "owner_review_required",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Conversation identity plus normalized customer message."
        ),
        retry_policy=(
            "Regenerate only if the customer message or support "
            "context changes."
        ),
        human_takeover_policy=(
            "Stop AI guidance immediately when a human agent takes over."
        ),
        audit_policy=(
            "Record intent, lead score, escalation decision and safe "
            "response without storing sensitive credentials."
        ),
        safe_error_policy=(
            "Never expose credentials, tokens, internal prompts, "
            "private customer data or raw tracebacks."
        ),
        default_risk=AgentRisk.LOW,
    ),
    "marketing_strategy_agent": AgentBrainContract(
        agent_key="marketing_strategy_agent",
        display_name="Venus Marketing Strategy Agent",
        purpose=(
            "Plan multi-channel marketing campaigns for "
            "published VenusRealm content."
        ),
        allowed_inputs=(
            "published_article",
            "public_url",
            "target_audience",
            "campaign_goal",
            "keywords",
            "approved_channels",
        ),
        allowed_tools=(
            "campaign_planner",
            "channel_selector",
            "kpi_planner",
            "risk_classifier",
        ),
        automatic_actions=(
            "prepare_campaign_plan",
            "recommend_channels",
            "recommend_marketing_agents",
            "define_kpis",
        ),
        approval_required_actions=(
            "start_campaign",
            "publish_social_content",
            "send_outreach",
            "create_external_backlink",
        ),
        forbidden_actions=(
            "auto_post_social_media",
            "send_email",
            "send_telegram_message",
            "send_whatsapp_message",
            "mass_forum_posting",
            "create_fake_account",
            "buy_backlinks",
            "guarantee_dofollow_backlink",
            "bypass_platform_policy",
        ),
        output_schema=(
            "status",
            "campaign_id",
            "campaign_name",
            "goal",
            "priority",
            "channels",
            "recommended_agents",
            "kpis",
            "owner_approval_required",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Published article URL plus campaign goal and target audience."
        ),
        retry_policy=(
            "Regenerate only when campaign inputs change."
        ),
        human_takeover_policy=(
            "Owner approval is mandatory before any external action."
        ),
        audit_policy=(
            "Record campaign inputs, recommendations, risk level, "
            "and approval state."
        ),
        safe_error_policy=(
            "Do not expose credentials, private audience data, "
            "prompts, or raw tracebacks."
        ),
        default_risk=AgentRisk.LOW,
    ),
    "social_media_agent": AgentBrainContract(
        agent_key="social_media_agent",
        display_name="Venus Social Media Agent",
        purpose=(
            "Prepare platform-specific social media drafts for "
            "approved published VenusRealm content."
        ),
        allowed_inputs=(
            "published_article",
            "public_url",
            "campaign_id",
            "approved_channels",
            "keywords",
            "target_audience",
        ),
        allowed_tools=(
            "content_reader",
            "social_draft_formatter",
            "hashtag_formatter",
            "channel_formatter",
        ),
        automatic_actions=(
            "prepare_social_drafts",
            "prepare_platform_variations",
            "prepare_hashtags",
            "prepare_cta",
        ),
        approval_required_actions=(
            "publish_social_post",
            "send_telegram_message",
            "send_whatsapp_message",
            "start_social_campaign",
        ),
        forbidden_actions=(
            "auto_post_social_media",
            "publish_without_owner_approval",
            "send_email",
            "mass_post",
            "create_fake_account",
            "buy_engagement",
            "bypass_platform_policy",
            "guarantee_performance",
        ),
        output_schema=(
            "status",
            "campaign_id",
            "article_title",
            "public_url",
            "channels",
            "hashtags",
            "drafts",
            "owner_approval_required",
            "safe_summary",
        ),
        idempotency_strategy=(
            "Published article URL, campaign identity and requested channels."
        ),
        retry_policy=(
            "Regenerate only when article, campaign or requested channels change."
        ),
        human_takeover_policy=(
            "Owner approval is mandatory before any external publication."
        ),
        audit_policy=(
            "Record source article, requested channels and draft result "
            "without performing external delivery."
        ),
        safe_error_policy=(
            "Do not expose credentials, private audience data, "
            "provider tokens or raw tracebacks."
        ),
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
    "macro_ai_agent": AgentBrainContract(
        agent_key="macro_ai_agent",
        display_name="Venus Macro AI",
        purpose=(
            "Provide deterministic, read-only XAUUSD macro confirmation "
            "from approved normalized market snapshots."
        ),
        allowed_inputs=(
            "normalized_market_snapshots",
            "approved_instrument_registry",
            "signal_direction_for_comparison",
        ),
        allowed_tools=(
            "macro_scoring_engine",
            "correlation_calculator",
            "read_only_market_repository",
        ),
        automatic_actions=(
            "calculate_macro_bias",
            "calculate_confidence",
            "identify_missing_sources",
            "report_signal_conflict",
        ),
        approval_required_actions=(
            "connect_new_market_provider",
            "change_instrument_weights",
            "use_macro_result_for_signal_blocking",
        ),
        forbidden_actions=(
            "execute_trade",
            "publish_signal",
            "send_telegram",
            "send_whatsapp",
            "modify_signal_engine",
            "write_production_market_data",
        ),
        output_schema=(
            "bias",
            "confidence",
            "total_score",
            "drivers",
            "conflicts",
            "observed_at",
        ),
        idempotency_strategy=(
            "Snapshot timestamp plus normalized instrument set."
        ),
        retry_policy=(
            "Retry only when missing or stale market snapshots are refreshed."
        ),
        human_takeover_policy=(
            "Owner approval is required before macro output can block "
            "or confirm production signals."
        ),
        audit_policy=(
            "Record assessment inputs, score, confidence and conflicts."
        ),
        safe_error_policy=(
            "Return NEUTRAL or incomplete assessment when data is missing; "
            "never guess market values."
        ),
        default_risk=AgentRisk.READ_ONLY,
    ),
    "economic_calendar_ai_agent": AgentBrainContract(
        agent_key="economic_calendar_ai_agent",
        display_name="Venus Economic Calendar AI",
        purpose=(
            "Provide read-only USA and Canada economic-event classification, "
            "event-surprise assessment and news-lock recommendations."
        ),
        allowed_inputs=(
            "approved_economic_events",
            "actual_forecast_previous_values",
            "event_schedule",
            "current_timestamp",
        ),
        allowed_tools=(
            "economic_calendar_engine",
            "approved_event_registry",
            "read_only_event_repository",
        ),
        automatic_actions=(
            "classify_event_impact",
            "calculate_event_surprise",
            "calculate_gold_bias",
            "recommend_news_lock",
        ),
        approval_required_actions=(
            "connect_external_calendar_provider",
            "activate_production_news_lock",
            "publish_news_article",
            "change_event_rules",
        ),
        forbidden_actions=(
            "scrape_unauthorized_sources",
            "execute_trade",
            "publish_signal",
            "send_telegram",
            "send_whatsapp",
            "modify_signal_engine",
        ),
        output_schema=(
            "event_id",
            "country",
            "impact",
            "bias",
            "surprise",
            "confidence",
            "lock_recommended",
            "rationale",
        ),
        idempotency_strategy=(
            "Event identifier plus scheduled timestamp and actual-value revision."
        ),
        retry_policy=(
            "Reassess only when actual, forecast or event timing changes."
        ),
        human_takeover_policy=(
            "Owner approval is required before any production signal lock "
            "or website publication."
        ),
        audit_policy=(
            "Record event source, values, assessment and lock recommendation."
        ),
        safe_error_policy=(
            "Return UNKNOWN when values or approved rules are missing."
        ),
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
