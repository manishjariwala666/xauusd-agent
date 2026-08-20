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
    "banao", "chalao", "create", "delete", "deploy", "diagnose", "execute",
    "generate", "karo", "migrate", "publish", "retry", "run", "send",
    "start", "stop", "disable", "off", "bandh",
}

_AGENT_ACTION_REQUESTS: tuple[tuple[tuple[str, ...], str, str, dict[str, Any], str], ...] = (
    (("market data agent", "market data validator", "xauusd market data"), "run_market_data_agent", "market_data_agent", {}, "Registered Market Data Agent requested for read-only validation."),
    (("customer support agent", "support guidance"), "run_customer_support_agent", "customer_support_agent", {}, "Registered Customer Support Agent requested for guidance preparation only."),
    (("marketing strategy agent", "marketing plan"), "run_marketing_strategy_agent", "marketing_strategy_agent", {}, "Registered Marketing Strategy Agent requested for draft planning only."),
    (("social media agent", "social media drafts", "social drafts"), "run_social_media_agent", "social_media_agent", {}, "Registered Social Media Agent requested for draft preparation only."),
    (("cms editor agent", "cms draft", "studio v2 draft"), "run_cms_editor_agent", "cms_editor_agent", {"publish": False}, "Registered CMS Editor Agent requested for draft conversion only."),
    (("content review agent", "master content review", "review cms draft"), "run_master_ai_content_review_agent", "master_content_review_agent", {}, "Registered Master Content Review Agent requested for read-only review."),
    (("publish approval agent", "master publish agent"), "run_master_ai_publish_approval_agent", "master_publish_approval_agent", {}, "Registered publish approval agent requested; publishing requires explicit owner approval."),
    (("announcement agent",), "run_announcement_agent", "announcement_agent", {}, "Announcement Agent may perform real external delivery and requires owner approval."),
    (("seo agent", "seo audit", "seo metadata"), "run_seo_agent", "seo_agent", {}, "SEO Agent can persist production SEO metadata/files and requires owner approval."),
    (("telegram reply agent",), "run_telegram_reply_agent", "telegram_reply_agent", {}, "Telegram Reply Agent may send a real client message and requires owner approval."),
    (("whatsapp reply agent",), "run_whatsapp_reply_agent", "whatsapp_reply_agent", {}, "WhatsApp Reply Agent may send a real client message and requires owner approval."),
)


def resolve_master_ai_intent(message: str | None) -> MasterAIIntentProposal:
    raw = str(message or "").strip()
    text = _normalize(raw)
    if not text:
        return _no_action()

    if _contains_any(text, ("railway deploy", "railway restart", "redeploy railway")):
        return _proposal("restart_railway", reason="Railway deployment or restart changes production service state.")
    if _contains_any(text, ("database migration", "db migration", "migrate database")):
        return _proposal("database_migration", reason="Database migration requires explicit owner approval.")
    if _contains_any(text, ("environment variable", "env variable", "secret change", "token change")):
        return _proposal("modify_environment", reason="Secrets and service configuration require explicit owner approval.")
    if _contains_any(text, ("delete production", "production data delete", "database delete")):
        return _proposal("delete_production_data", reason="Production deletion is permanently blocked.")
    if _is_signal_stop_request(text):
        return _proposal("disable_signal_agent", agent_key="signal_agent", risk=IntentRisk.HIGH, reason="Stopping or disabling the Signal Agent changes live operational state and requires explicit owner approval.")
    if _is_signal_delivery(text):
        return _proposal("publish_signal", agent_key="signal_agent", risk=IntentRisk.HIGH, reason="Real signal delivery requires explicit owner approval.")
    if _is_signal_information_request(text):
        return _proposal("read_signal_status", agent_key="signal_agent", risk=IntentRisk.SAFE, reason="Read-only current XAUUSD Sheet snapshot requested.")
    if _is_content_publish(text):
        return _proposal("publish_website", reason="Publishing content requires explicit owner approval.")

    # Explicit creation/execution of a registered Blog Agent must win over words
    # such as STATUS that may appear only in the requested output contract.
    blog = _blog_request(text, raw)
    if blog is not None:
        return _proposal(
            "run_blog_agent",
            agent_key="ai_blog_agent",
            parameters=blog,
            reason="Registered Blog Agent requested for one real draft execution only.",
        )

    if _contains_any(text, ("retry", "dobara chalao", "phir se chalao")):
        retry_action, agent_key = _retry_target(text)
        if not retry_action:
            return _clarification("Retry ke liye registered automatic agent specify karein.")
        target_policy = get_action_policy(retry_action)
        risk = IntentRisk.LOW_RISK if target_policy and target_policy.approval == ApprovalLevel.AUTOMATIC else IntentRisk.APPROVAL_REQUIRED
        return _proposal("retry_failed_agent", agent_key=agent_key, risk=risk, parameters={"retry_action": retry_action}, reason=f"Retry target is the registered action {retry_action}.")

    if _is_diagnostic_request(text):
        return _proposal("read_agent_status", agent_key="master_ai", reason="Read-only registered-agent diagnostics requested.")
    if _is_agent_list_request(text):
        return _proposal("list_registered_agents", agent_key="master_ai", reason="Read-only registered-agent directory requested.")

    requested: list[tuple[str, str, dict[str, Any], str]] = []
    explicit_image_agent_requested = _contains_any(text, ("image agent", "thumbnail banao", "image banao"))
    if explicit_image_agent_requested:
        requested.append(("run_image_agent", "image_agent", {"telegram_target": "image"}, "Registered Image Agent requested for image preparation."))
    if _is_signal_run_request(text):
        requested.append(("run_signal_agent", "signal_agent", {}, "Signal Agent may create or deliver a real market signal."))
    for phrases, action, agent_key, parameters, reason in _AGENT_ACTION_REQUESTS:
        if _contains_any(text, phrases):
            requested.append((action, agent_key, dict(parameters), reason))

    unique_actions = {item[0] for item in requested}
    if len(unique_actions) > 1:
        return _clarification("Request mein multiple agent actions hain. Ek registered agent choose karein.")
    if requested:
        action, agent_key, parameters, reason = requested[0]
        return _proposal(action, agent_key=agent_key, parameters=parameters, reason=reason)
    if _looks_actionable(text):
        return _clarification("Registered action clear nahi hai. Agent aur requested action specify karein.")
    return _no_action()


def _blog_request(text: str, raw: str) -> dict[str, Any] | None:
    blog_named = _contains_any(
        text,
        ("ai blog agent", "blog agent", "blog draft", "seo blog", "blog post", "article banao"),
    )
    execute_requested = _contains_any(
        text,
        ("execute", "run", "create", "generate", "banao", "chalao", "real ai blog agent"),
    )
    if not (blog_named and execute_requested):
        return None

    params: dict[str, Any] = {
        "publish": False,
        "include_image": _contains_any(text, ("featured image", "inline image", "featured images", "inline images")),
        "include_faq": "faq" in text,
        "include_schema": "schema" in text,
        "include_internal_links": _contains_any(text, ("internal link", "internal links")),
        "include_risk_disclaimer": _contains_any(text, ("risk disclaimer", "trading risk disclaimer")),
        "telegram_target": "blog",
        "owner_request": raw[:12000],
    }

    topic = _line_value(raw, "topic")
    if topic:
        params["topic"] = topic
    audience = _line_value(raw, "target audience")
    if audience:
        params["target_audience"] = audience
    if re.search(r"\busa\b|\bu\.s\.a\b|\bunited states\b", raw, flags=re.I):
        params["location"] = "USA"

    match = re.search(r"(\d{3,4})\s*[–—-]\s*(\d{3,4})\s*words", raw, flags=re.I)
    if match:
        params["target_word_min"] = int(match.group(1))
        params["target_word_max"] = int(match.group(2))

    return params


def _line_value(raw: str, label: str) -> str:
    match = re.search(
        rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$",
        raw,
    )
    return " ".join(match.group(1).split())[:1000] if match else ""


def _proposal(action: str, *, agent_key: str | None = None, risk: IntentRisk | None = None, parameters: dict[str, Any] | None = None, reason: str) -> MasterAIIntentProposal:
    policy = get_action_policy(action)
    if policy is None:
        return _clarification("Requested action registered nahi hai.")
    if agent_key and not _is_registered_agent_key(agent_key):
        return _clarification("Requested agent registered nahi hai.")
    resolved_risk = risk or _risk_for(action, policy.approval)
    status = "APPROVAL_REQUIRED" if resolved_risk in {IntentRisk.HIGH, IntentRisk.APPROVAL_REQUIRED} else "RESOLVED"
    if policy.approval == ApprovalLevel.FORBIDDEN:
        status = "BLOCKED"
    return MasterAIIntentProposal(status=status, action=action, agent_key=agent_key, risk=resolved_risk, parameters=dict(parameters or {}), reason=reason)


def _risk_for(action: str, approval: ApprovalLevel) -> IntentRisk:
    if approval != ApprovalLevel.AUTOMATIC:
        return IntentRisk.APPROVAL_REQUIRED
    if action in {"list_registered_agents", "read_agent_status", "read_signal_status", "read_system_health"}:
        return IntentRisk.SAFE
    return IntentRisk.LOW_RISK


def _retry_target(text: str) -> tuple[str | None, str | None]:
    mappings = (
        (("blog agent", "blog"), "run_blog_agent", "ai_blog_agent"),
        (("image agent", "image", "thumbnail"), "run_image_agent", "image_agent"),
        (("market data agent", "market data"), "run_market_data_agent", "market_data_agent"),
        (("customer support agent", "support guidance"), "run_customer_support_agent", "customer_support_agent"),
        (("marketing strategy agent", "marketing plan"), "run_marketing_strategy_agent", "marketing_strategy_agent"),
        (("social media agent", "social drafts"), "run_social_media_agent", "social_media_agent"),
        (("cms editor agent", "cms draft"), "run_cms_editor_agent", "cms_editor_agent"),
        (("content review agent", "content review"), "run_master_ai_content_review_agent", "master_content_review_agent"),
        (("signal agent", "signal"), "run_signal_agent", "signal_agent"),
    )
    for phrases, action, agent_key in mappings:
        if _contains_any(text, phrases):
            return action, agent_key
    return None, None


def _is_registered_agent_key(agent_key: str) -> bool:
    return any(agent.agent_key == agent_key for agent in list_registered_agents())


def _is_diagnostic_request(text: str) -> bool:
    return _contains_any(text, ("agents ka status", "agent status", "agent ka status", "agent diagnostics", "error diagnose", "error check", "error door", "master ai status", "master ai ka status", "master ai ka error"))


def _is_agent_list_request(text: str) -> bool:
    return _contains_any(text, ("agent list", "agents list", "sab agent batao", "sabhi agent batao"))


def _is_signal_stop_request(text: str) -> bool:
    return "signal" in text and _contains_any(text, ("signal band karo", "signal bandh karo", "signal stop karo", "stop signal", "disable signal", "signal disable karo", "signal agent off", "signal off karo"))


def _is_signal_delivery(text: str) -> bool:
    return "signal" in text and _contains_any(text, ("telegram par bhejo", "whatsapp par bhejo", "signal bhejo", "send signal", "publish signal"))


def _is_content_publish(text: str) -> bool:
    return _contains_any(text, ("blog publish", "content publish", "website publish", "post live"))


def _is_signal_run_request(text: str) -> bool:
    return _contains_any(text, ("signal agent", "signal banao", "signal run", "signal chalao"))


def _is_signal_information_request(text: str) -> bool:
    return _contains_any(text, ("today signal", "signal today", "aaj ka signal", "aaj signal", "signal batao"))


def _looks_actionable(text: str) -> bool:
    return bool(set(text.split()) & _ACTION_WORDS) or " agent " in f" {text} "


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _normalize(value: str | None) -> str:
    lowered = str(value or "").strip().lower().replace("_", " ")
    normalized = " ".join(re.sub(r"[^a-z0-9\s/]+", " ", lowered).split())
    return re.sub(r"\bsignle\b", "signal", normalized)


def _clarification(reason: str) -> MasterAIIntentProposal:
    return MasterAIIntentProposal(status="CLARIFICATION_REQUIRED", reason=reason)


def _no_action() -> MasterAIIntentProposal:
    return MasterAIIntentProposal(status="NO_ACTION")
