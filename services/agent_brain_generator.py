"""Preview-only brain contract generator for Venus Agent Builder."""

from __future__ import annotations

import re
from typing import Any

from services.agent_brain_contracts import AgentRisk


DEPARTMENT_DEFAULTS: dict[str, dict[str, tuple[str, ...]]] = {
    "marketing": {
        "allowed_tools": (
            "content_reader",
            "campaign_planner",
            "analytics_reader",
        ),
        "automatic_actions": (
            "analyze_approved_input",
            "prepare_draft_output",
            "prepare_safe_summary",
        ),
        "approval_required_actions": (
            "external_posting",
            "send_outreach",
            "modify_campaign",
        ),
        "forbidden_actions": (
            "mass_spam",
            "create_fake_account",
            "buy_backlinks",
            "bypass_platform_policy",
        ),
    },
    "support": {
        "allowed_tools": (
            "knowledge_base_reader",
            "intent_classifier",
            "support_triage",
        ),
        "automatic_actions": (
            "answer_general_questions",
            "prepare_guidance",
            "prepare_escalation_summary",
        ),
        "approval_required_actions": (
            "send_customer_message",
            "create_crm_record",
            "modify_customer_account",
        ),
        "forbidden_actions": (
            "provide_trading_signal",
            "collect_password_or_otp",
            "process_payment",
            "process_refund",
        ),
    },
    "content": {
        "allowed_tools": (
            "content_reader",
            "content_formatter",
            "validation_service",
        ),
        "automatic_actions": (
            "prepare_content_draft",
            "validate_output",
            "prepare_safe_summary",
        ),
        "approval_required_actions": (
            "publish_content",
            "modify_published_content",
            "external_delivery",
        ),
        "forbidden_actions": (
            "auto_publish",
            "invent_facts",
            "guarantee_profit",
            "delete_content",
        ),
    },
    "analytics": {
        "allowed_tools": (
            "read_only_analytics",
            "report_builder",
            "trend_analyzer",
        ),
        "automatic_actions": (
            "read_approved_metrics",
            "prepare_report",
            "prepare_recommendations",
        ),
        "approval_required_actions": (
            "change_tracking_configuration",
            "send_external_report",
        ),
        "forbidden_actions": (
            "modify_source_data",
            "invent_metrics",
            "expose_private_data",
        ),
    },
    "general": {
        "allowed_tools": (
            "approved_data_reader",
            "deterministic_validator",
        ),
        "automatic_actions": (
            "analyze_approved_input",
            "prepare_draft_output",
        ),
        "approval_required_actions": (
            "external_action",
            "configuration_change",
        ),
        "forbidden_actions": (
            "bypass_approval",
            "expose_secrets",
            "delete_production_data",
        ),
    },
}

EXTERNAL_ACTION_TERMS = {
    "publish",
    "post",
    "send",
    "email",
    "telegram",
    "whatsapp",
    "payment",
    "refund",
    "deploy",
    "delete",
    "trade",
    "backlink",
}

CRITICAL_TERMS = {
    "trade",
    "payment",
    "refund",
    "delete",
    "deploy",
    "deployment",
    "production",
    "secret",
    "credential",
    "database migration",
}


def _clean(value: object, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def normalize_agent_key(value: object) -> str:
    key = re.sub(
        r"[^a-z0-9]+",
        "_",
        _clean(value, 120).lower(),
    ).strip("_")

    if not key:
        raise ValueError("Agent key is required.")

    if not key.endswith("_agent"):
        key += "_agent"

    if not re.fullmatch(r"[a-z][a-z0-9_]{2,99}", key):
        raise ValueError("Agent key format is invalid.")

    return key


def infer_risk(spec: dict[str, Any]) -> AgentRisk:
    text = " ".join(
        [
            _clean(spec.get("purpose"), 1000),
            *[
                _clean(item, 200)
                for item in spec.get("requested_actions", [])
            ],
            *[
                _clean(item, 200)
                for item in spec.get("requested_tools", [])
            ],
        ]
    ).casefold()

    if any(term in text for term in CRITICAL_TERMS):
        return AgentRisk.CRITICAL

    if any(term in text for term in EXTERNAL_ACTION_TERMS):
        return AgentRisk.HIGH

    if bool(spec.get("read_only")):
        return AgentRisk.READ_ONLY

    return AgentRisk.LOW


def generate_brain_preview(
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Generate a deterministic, non-executable brain preview."""
    display_name = _clean(
        spec.get("display_name")
        or spec.get("name"),
        160,
    )
    purpose = _clean(spec.get("purpose"), 1000)

    if not display_name:
        raise ValueError("Agent display name is required.")

    if len(purpose) < 20:
        raise ValueError(
            "Agent purpose must contain at least 20 characters."
        )

    agent_key = normalize_agent_key(
        spec.get("agent_key") or display_name
    )

    department = _clean(
        spec.get("department") or "general",
        50,
    ).lower()

    defaults = DEPARTMENT_DEFAULTS.get(
        department,
        DEPARTMENT_DEFAULTS["general"],
    )

    inferred_risk = infer_risk(spec)

    requested_risk = _clean(
        spec.get("risk"),
        30,
    ).upper()

    risk = (
        AgentRisk(requested_risk)
        if requested_risk
        else inferred_risk
    )

    # User cannot downgrade an automatically detected higher-risk design.
    risk_order = {
        AgentRisk.READ_ONLY: 0,
        AgentRisk.LOW: 1,
        AgentRisk.HIGH: 2,
        AgentRisk.CRITICAL: 3,
    }

    if risk_order[risk] < risk_order[inferred_risk]:
        risk = inferred_risk

    allowed_inputs = tuple(
        dict.fromkeys(
            _clean(item, 120)
            for item in spec.get(
                "allowed_inputs",
                ["approved_task_context"],
            )
            if _clean(item, 120)
        )
    )

    requested_tools = tuple(
        _clean(item, 120)
        for item in spec.get("requested_tools", [])
        if _clean(item, 120)
    )

    allowed_tools = tuple(
        dict.fromkeys(
            defaults["allowed_tools"] + requested_tools
        )
    )

    forbidden_actions = tuple(
        dict.fromkeys(
            defaults["forbidden_actions"]
            + (
                "activate_agent",
                "modify_secrets",
                "deploy_production",
                "git_push",
                "database_migration",
            )
        )
    )

    if risk is AgentRisk.CRITICAL:
        automatic_actions: tuple[str, ...] = ()
        approval_required_actions = tuple(
            dict.fromkeys(
                defaults["approval_required_actions"]
                + tuple(
                    _clean(item, 120)
                    for item in spec.get(
                        "requested_actions",
                        [],
                    )
                    if _clean(item, 120)
                )
                + ("generate_scaffold_preview",)
            )
        )
    else:
        automatic_actions = defaults["automatic_actions"]
        approval_required_actions = tuple(
            dict.fromkeys(
                defaults["approval_required_actions"]
                + tuple(
                    _clean(item, 120)
                    for item in spec.get(
                        "requested_actions",
                        [],
                    )
                    if _clean(item, 120)
                )
            )
        )

    output_schema = tuple(
        dict.fromkeys(
            [
                "status",
                "safe_summary",
                *[
                    _clean(item, 120)
                    for item in spec.get(
                        "output_schema",
                        [],
                    )
                    if _clean(item, 120)
                ],
            ]
        )
    )

    return {
        "version": 1,
        "state": "BRAIN_PREVIEW",
        "agent_key": agent_key,
        "display_name": display_name,
        "department": department,
        "purpose": purpose,
        "allowed_inputs": list(allowed_inputs),
        "allowed_tools": list(allowed_tools),
        "automatic_actions": list(automatic_actions),
        "approval_required_actions": list(
            approval_required_actions
        ),
        "forbidden_actions": list(forbidden_actions),
        "output_schema": list(output_schema),
        "idempotency_strategy": (
            "Stable task identifier plus normalized approved input."
        ),
        "retry_policy": (
            "Retry only safe transient failures; never repeat "
            "successful external actions."
        ),
        "human_takeover_policy": (
            "Owner or human operator instructions override automation."
        ),
        "audit_policy": (
            "Record design inputs, generated contract, risk decision "
            "and approval state."
        ),
        "safe_error_policy": (
            "Redact secrets, credentials, private data, paths "
            "and raw tracebacks."
        ),
        "default_risk": risk.value,
        "execution_enabled": False,
        "registry_written": False,
        "runner_written": False,
        "files_generated": False,
        "owner_approval_required": True,
    }
