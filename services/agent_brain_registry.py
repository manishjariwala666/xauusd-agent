"""Unified VenusRealm brain registry including governed legacy agents."""

from __future__ import annotations

from services.agent_brain_contracts import (
    AGENT_BRAINS,
    AgentBrainContract,
    AgentRisk,
)


SEO_AGENT_BRAIN = AgentBrainContract(
    agent_key="seo_agent",
    display_name="Venus SEO Agent",
    purpose=(
        "Audit published VenusRealm content and prepare or persist SEO metadata "
        "improvements only through explicit owner-approved execution."
    ),
    allowed_inputs=(
        "published_content",
        "existing_seo_metadata",
        "approved_seo_rules",
    ),
    allowed_tools=(
        "content_repository",
        "seo_issue_detector",
        "ai_provider",
        "seo_metadata_repository",
        "seo_file_writer",
    ),
    automatic_actions=(
        "inspect_existing_seo_metadata",
        "identify_seo_issues",
        "prepare_seo_improvement_preview",
    ),
    approval_required_actions=(
        "persist_seo_metadata",
        "rewrite_seo_files",
        "modify_published_content_metadata",
        "run_seo_agent",
    ),
    forbidden_actions=(
        "publish_new_content",
        "delete_content",
        "invent_content_performance",
        "guarantee_search_ranking",
        "change_dns",
        "send_external_message",
    ),
    output_schema=(
        "status",
        "scanned_count",
        "improved_count",
        "content_references",
        "approval_state",
        "safe_summary",
    ),
    idempotency_strategy=(
        "Content identity plus current SEO metadata state; upsert by content_id."
    ),
    retry_policy=(
        "Retry transient generation failures only; never duplicate metadata records."
    ),
    human_takeover_policy=(
        "Owner approval is mandatory before any production SEO metadata or file write."
    ),
    audit_policy=(
        "Record approved execution, affected content IDs, issue classes and write outcome."
    ),
    safe_error_policy=(
        "Never expose provider credentials, private paths, database details or raw tracebacks."
    ),
    default_risk=AgentRisk.HIGH,
)


EXTENDED_AGENT_BRAINS: dict[str, AgentBrainContract] = {
    **AGENT_BRAINS,
    SEO_AGENT_BRAIN.agent_key: SEO_AGENT_BRAIN,
}


def get_agent_brain(agent_key: str) -> AgentBrainContract | None:
    return EXTENDED_AGENT_BRAINS.get(str(agent_key or "").strip().lower())


def list_agent_brains() -> tuple[AgentBrainContract, ...]:
    return tuple(EXTENDED_AGENT_BRAINS.values())
