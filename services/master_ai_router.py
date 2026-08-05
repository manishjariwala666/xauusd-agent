"""Deterministic request router for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MasterAIRoute:
    intent: str
    agent_key: str | None
    confidence: str
    execution_allowed: bool
    reason: str


MARKET_TERMS = (
    "xauusd",
    "gold price",
    "current price",
    "live price",
    "cmp",
    "market price",
    "today high",
    "today low",
    "session high",
    "session low",
)

SUPPORT_TERMS = (
    "customer",
    "client",
    "refund",
    "subscription",
    "login",
    "billing",
    "support",
)

MARKETING_TERMS = (
    "marketing plan",
    "social media",
    "backlink",
    "forum posting",
    "campaign",
    "promotion",
)

CMS_TERMS = (
    "create blog",
    "write article",
    "seo article",
    "content draft",
    "cms draft",
)

REVIEW_TERMS = (
    "review article",
    "review draft",
    "check content",
    "content approval",
)

PUBLISH_TERMS = (
    "publish article",
    "publish draft",
    "make live",
    "go live",
)


def _contains_any(message: str, terms: tuple[str, ...]) -> bool:
    return any(term in message for term in terms)


def route_master_ai_request(message: str | None) -> MasterAIRoute:
    """Resolve one administrator message to the safest specialist route."""
    clean = " ".join(str(message or "").strip().lower().split())

    if not clean:
        return MasterAIRoute(
            intent="EMPTY",
            agent_key=None,
            confidence="HIGH",
            execution_allowed=False,
            reason="Message is empty.",
        )

    if _contains_any(clean, MARKET_TERMS):
        return MasterAIRoute(
            intent="MARKET_DATA",
            agent_key="market_data_agent",
            confidence="HIGH",
            execution_allowed=True,
            reason="Live or current XAUUSD market-data intent detected.",
        )

    if _contains_any(clean, SUPPORT_TERMS):
        return MasterAIRoute(
            intent="CUSTOMER_SUPPORT",
            agent_key="customer_support_agent",
            confidence="MEDIUM",
            execution_allowed=False,
            reason="Customer-support intent detected; context is required.",
        )

    if _contains_any(clean, MARKETING_TERMS):
        return MasterAIRoute(
            intent="MARKETING",
            agent_key="marketing_strategy_agent",
            confidence="MEDIUM",
            execution_allowed=False,
            reason="Marketing strategy intent detected.",
        )

    if _contains_any(clean, REVIEW_TERMS):
        return MasterAIRoute(
            intent="CONTENT_REVIEW",
            agent_key="master_content_review_agent",
            confidence="MEDIUM",
            execution_allowed=False,
            reason="Content-review intent detected.",
        )

    if _contains_any(clean, PUBLISH_TERMS):
        return MasterAIRoute(
            intent="PUBLISH",
            agent_key="master_publish_approval_agent",
            confidence="HIGH",
            execution_allowed=False,
            reason="Publishing requires review and explicit owner approval.",
        )

    if _contains_any(clean, CMS_TERMS):
        return MasterAIRoute(
            intent="CMS_DRAFT",
            agent_key="cms_editor_agent",
            confidence="MEDIUM",
            execution_allowed=False,
            reason="CMS draft intent detected.",
        )

    return MasterAIRoute(
        intent="GENERAL_CHAT",
        agent_key=None,
        confidence="LOW",
        execution_allowed=False,
        reason="No specialist route matched; use conversational fallback.",
    )
