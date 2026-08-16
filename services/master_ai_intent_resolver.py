"""Deterministic natural-language intent resolution for private Master AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any

from services.master_ai_access_policy import ApprovalLevel, get_action_policy
from services.master_ai_agent_registry import list_registered_agents


class IntentRisk(str, Enum):
    SAFE = "SAFE"
    LOW_RISK = "LOW_RISK"
    HIGH = "HIGH"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class MasterAIIntentProposal:
    status: str
    action: str | None = None
    agent_key: str | None = None
    risk: IntentRisk | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


_ACTION_WORDS = {
    "banao", "chalao", "create", "delete", "deploy", "diagnose",
    "execute", "generate", "karo", "migrate", "publish", "retry",
    "run", "send", "start", "stop", "disable", "off", "bandh",
}


def resolve_master_ai_intent(message: str | None) -> MasterAIIntentProposal:
    """Resolve only deterministic, registered actions without using an LLM."""
    text = _normalize(message)
    if not text:
        return _no_action()

    if _contains_any(text, ("railway deploy", "railway restart", "redeploy railway")):
        return _proposal(
            "restart_railway",
            reason="Railway deployment or restart changes production service state.",
        )
    if _contains_any(text, ("database migration", "db migration", "migrate database")):
        return _proposal(
            "database_migration",
            reason="Database migration requires explicit owner approval.",
        )
    if _contains_any(text, ("environment variable", "env variable", "secret change", "token change")):
        return _proposal(
            "modify_environment",
            reason="Secrets and service configuration require explicit owner approval.",
        )
    if _contains_any(text, ("delete production", "production data delete", "database delete")):
        return _proposal(
            "delete_production_data",
            reason="Production deletion is permanently blocked.",
        )
    if _is_signal_stop_request(text):
        return _proposal(
            "disable_signal_agent",
            agent_key="signal_agent",
            risk=IntentRisk.HIGH,
            reason=(
                "Stopping or disabling the Signal Agent changes live operational "
                "state and requires explicit owner approval."
            ),
        )

    if _is_signal_delivery(text):
        return _proposal(
            "publish_signal",
            agent_key="signal_agent",
            risk=IntentRisk.HIGH,
            reason="Real signal delivery requires explicit owner approval.",
        )
    if _is_signal_information_request(text):
        return _proposal(
            "read_signal_status",
            agent_key="signal_agent",
            risk=IntentRisk.SAFE,
            reason="Read-only current XAUUSD Sheet snapshot requested.",
        )
    if _is_content_publish(text):
        return _proposal(
            "publish_website",
            reason="Publishing content requires explicit owner approval.",
        )

    if _contains_any(text, ("retry", "dobara chalao", "phir se chalao")):
        retry_action, agent_key = _retry_target(text)
        if not retry_action:
            return _clarification(
                "Retry ke liye registered Blog Agent ya Image Agent specify karein."
            )
        target_policy = get_action_policy(retry_action)
        risk = (
            IntentRisk.LOW_RISK
            if target_policy and target_policy.approval == ApprovalLevel.AUTOMATIC
            else IntentRisk.APPROVAL_REQUIRED
        )
        return _proposal(
            "retry_failed_agent",
            agent_key=agent_key,
            risk=risk,
            parameters={"retry_action": retry_action},
            reason=f"Retry target is the registered action {retry_action}.",
        )

    if _is_diagnostic_request(text):
        return _proposal(
            "read_agent_status",
            agent_key="master_ai",
            reason="Read-only registered-agent diagnostics requested.",
        )
    if _is_agent_list_request(text):
        return _proposal(
            "list_registered_agents",
            agent_key="master_ai",
            reason="Read-only registered-agent directory requested.",
        )

    requested: list[tuple[str, str, dict[str, Any], str]] = []

    blog_requested = _contains_any(
        text,
        (
            "blog agent",
            "blog draft",
            "draft banao",
            "article banao",
            "seo blog",
            "blog post",
            "ai_blog_agent",
        ),
    )

    explicit_image_agent_requested = _contains_any(
        text,
        (
            "image agent",
            "thumbnail banao",
            "image banao",
        ),
    )

    embedded_blog_image_requested = _contains_any(
        text,
        (
            "featured image",
            "inline image",
            "featured images",
            "inline images",
        ),
    )

    if blog_requested:
        requested.append(
            (
                "run_blog_agent",
                "ai_blog_agent",
                {
                    "publish": False,
                    "include_image": embedded_blog_image_requested,
                    "telegram_target": "blog",
                },
                "Registered Blog Agent requested for draft preparation only.",
            )
        )

    if explicit_image_agent_requested:
        requested.append(
            (
                "run_image_agent",
                "image_agent",
                {"telegram_target": "image"},
                "Registered Image Agent requested for image preparation.",
            )
        )
    if _is_signal_run_request(text):
        requested.append(
            (
                "run_signal_agent",
                "signal_agent",
                {},
                "Signal Agent may create or deliver a real market signal.",
            )
        )

    if len({item[0] for item in requested}) > 1:
        return _clarification(
            "Request mein multiple agent actions hain. Ek registered agent choose karein."
        )
    if requested:
        action, agent_key, parameters, reason = requested[0]
        return _proposal(
            action,
            agent_key=agent_key,
            parameters=parameters,
            reason=reason,
        )
    if _looks_actionable(text):
        return _clarification(
            "Registered action clear nahi hai. Agent aur requested action specify karein."
        )
    return _no_action()


def _proposal(
    action: str,
    *,
    agent_key: str | None = None,
    risk: IntentRisk | None = None,
    parameters: dict[str, Any] | None = None,
    reason: str,
) -> MasterAIIntentProposal:
    policy = get_action_policy(action)
    if policy is None:
        return _clarification("Requested action registered nahi hai.")
    if agent_key and not _is_registered_agent_key(agent_key):
        return _clarification("Requested agent registered nahi hai.")

    resolved_risk = risk or _risk_for(action, policy.approval)
    status = (
        "APPROVAL_REQUIRED"
        if resolved_risk in {
            IntentRisk.HIGH,
            IntentRisk.APPROVAL_REQUIRED,
        }
        else "RESOLVED"
    )
    if policy.approval == ApprovalLevel.FORBIDDEN:
        status = "BLOCKED"
    return MasterAIIntentProposal(
        status=status,
        action=action,
        agent_key=agent_key,
        risk=resolved_risk,
        parameters=dict(parameters or {}),
        reason=reason,
    )


def _risk_for(action: str, approval: ApprovalLevel) -> IntentRisk:
    if approval != ApprovalLevel.AUTOMATIC:
        return IntentRisk.APPROVAL_REQUIRED
    if action in {
        "list_registered_agents",
        "read_agent_status",
        "read_signal_status",
        "read_system_health",
    }:
        return IntentRisk.SAFE
    return IntentRisk.LOW_RISK


def _retry_target(text: str) -> tuple[str | None, str | None]:
    if _contains_any(text, ("blog agent", "blog")):
        return "run_blog_agent", "ai_blog_agent"
    if _contains_any(text, ("image agent", "image", "thumbnail")):
        return "run_image_agent", "image_agent"
    if _contains_any(text, ("signal agent", "signal")):
        return "run_signal_agent", "signal_agent"
    return None, None


def _is_registered_agent_key(agent_key: str) -> bool:
    return any(agent.agent_key == agent_key for agent in list_registered_agents())


def _is_diagnostic_request(text: str) -> bool:
    return ("status" in text and "agent" in text) or _contains_any(
        text,
        (
            "agents ka status", "agent status", "agent diagnostics",
            "error diagnose", "error check", "error door",
            "master ai status", "master ai ka error",
        ),
    )


def _is_agent_list_request(text: str) -> bool:
    return _contains_any(
        text,
        ("agent list", "agents list", "sab agent batao", "sabhi agent batao"),
    )


def _is_signal_stop_request(text: str) -> bool:
    return "signal" in text and _contains_any(
        text,
        (
            "signal band karo",
            "signal bandh karo",
            "signal stop karo",
            "stop signal",
            "disable signal",
            "signal disable karo",
            "signal agent off",
            "signal off karo",
        ),
    )


def _is_signal_delivery(text: str) -> bool:
    return "signal" in text and _contains_any(
        text,
        (
            "telegram par bhejo", "whatsapp par bhejo", "signal bhejo",
            "send signal", "publish signal",
        ),
    )


def _is_content_publish(text: str) -> bool:
    return _contains_any(
        text,
        ("blog publish", "content publish", "website publish", "post live"),
    )


def _is_signal_run_request(text: str) -> bool:
    return _contains_any(
        text,
        ("signal agent", "signal banao", "signal run", "signal chalao"),
    )


def _is_signal_information_request(text: str) -> bool:
    return _contains_any(
        text,
        (
            "today signal",
            "signal today",
            "aaj ka signal",
            "aaj signal",
            "signal batao",
        ),
    )


def _looks_actionable(text: str) -> bool:
    return bool(set(text.split()) & _ACTION_WORDS) or " agent " in f" {text} "


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _normalize(value: str | None) -> str:
    lowered = str(value or "").strip().lower().replace("_", " ")
    normalized = " ".join(re.sub(r"[^a-z0-9\s/]+", " ", lowered).split())
    return re.sub(r"\bsignle\b", "signal", normalized)


def _clarification(reason: str) -> MasterAIIntentProposal:
    return MasterAIIntentProposal(
        status="CLARIFICATION_REQUIRED",
        reason=reason,
    )


def _no_action() -> MasterAIIntentProposal:
    return MasterAIIntentProposal(status="NO_ACTION")
