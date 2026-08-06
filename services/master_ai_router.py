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

MARKET_OUTLOOK_TERMS = (
    "gold outlook",
    "xauusd outlook",
    "market outlook",
    "gold view",
    "gold ka outlook",
    "gold ka view",
    "gold bullish ya bearish",
    "xauusd bullish ya bearish",
)

MACRO_OUTLOOK_TERMS = (
    "macro outlook",
    "macro bias",
    "macro view",
    "dxy impact",
    "yield impact",
    "dollar impact on gold",
    "macro gold bias",
)

NEWS_RISK_TERMS = (
    "news risk",
    "high impact news",
    "economic news",
    "economic calendar",
    "nfp risk",
    "cpi risk",
    "fomc risk",
    "usa news",
    "canada news",
)

WAIT_OR_TRADE_TERMS = (
    "should i wait",
    "safe to trade",
    "trade karna safe hai",
    "wait karu",
    "abhi trade karu",
    "news ke pehle trade",
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

    if _contains_any(clean, WAIT_OR_TRADE_TERMS):
        return MasterAIRoute(
            intent="WAIT_OR_TRADE",
            agent_key="master_ai",
            confidence="HIGH",
            execution_allowed=False,
            reason="Read-only trading-risk assessment requested.",
        )

    if _contains_any(clean, NEWS_RISK_TERMS):
        return MasterAIRoute(
            intent="NEWS_RISK",
            agent_key="economic_calendar_ai_agent",
            confidence="HIGH",
            execution_allowed=False,
            reason="Read-only economic-news risk assessment requested.",
        )

    if _contains_any(clean, MACRO_OUTLOOK_TERMS):
        return MasterAIRoute(
            intent="MACRO_OUTLOOK",
            agent_key="macro_ai_agent",
            confidence="HIGH",
            execution_allowed=False,
            reason="Read-only macro outlook requested.",
        )

    if _contains_any(clean, MARKET_OUTLOOK_TERMS):
        return MasterAIRoute(
            intent="MARKET_OUTLOOK",
            agent_key="master_ai",
            confidence="HIGH",
            execution_allowed=False,
            reason="Unified read-only market intelligence requested.",
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
