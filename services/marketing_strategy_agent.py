"""Draft-only marketing campaign strategy agent for VenusRealm."""

from __future__ import annotations

import json
import re
from typing import Any


SUPPORTED_GOALS = {
    "traffic",
    "brand_authority",
    "lead_generation",
    "engagement",
    "backlink_growth",
}

SUPPORTED_CHANNELS = {
    "telegram",
    "whatsapp",
    "linkedin",
    "facebook",
    "instagram",
    "x",
    "pinterest",
    "youtube_community",
    "email",
}

CHANNEL_AGENT_MAP = {
    "telegram": "social_media_agent",
    "whatsapp": "social_media_agent",
    "linkedin": "social_media_agent",
    "facebook": "social_media_agent",
    "instagram": "social_media_agent",
    "x": "social_media_agent",
    "pinterest": "social_media_agent",
    "youtube_community": "social_media_agent",
    "email": "outreach_community_agent",
}


def _clean_text(value: object, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def _normalize_goal(value: object) -> str:
    goal = (
        _clean_text(value, 100)
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    aliases = {
        "traffic_and_authority": "brand_authority",
        "authority": "brand_authority",
        "leads": "lead_generation",
        "backlinks": "backlink_growth",
    }

    goal = aliases.get(goal, goal)

    if goal not in SUPPORTED_GOALS:
        return "traffic"

    return goal


def _select_channels(
    requested: object,
    *,
    goal: str,
) -> list[str]:
    if isinstance(requested, list):
        channels = [
            _clean_text(item, 50)
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            for item in requested
        ]
    else:
        channels = []

    valid = [
        channel
        for channel in channels
        if channel in SUPPORTED_CHANNELS
    ]

    if valid:
        return list(dict.fromkeys(valid))[:8]

    defaults = {
        "traffic": [
            "telegram",
            "whatsapp",
            "linkedin",
            "facebook",
            "x",
        ],
        "brand_authority": [
            "linkedin",
            "x",
            "youtube_community",
            "telegram",
        ],
        "lead_generation": [
            "linkedin",
            "whatsapp",
            "email",
            "telegram",
        ],
        "engagement": [
            "instagram",
            "facebook",
            "x",
            "telegram",
        ],
        "backlink_growth": [
            "linkedin",
            "x",
            "email",
        ],
    }

    return defaults[goal]


def _priority(
    *,
    published: bool,
    goal: str,
    keywords: list[str],
) -> str:
    score = 0

    if published:
        score += 2

    if goal in {
        "lead_generation",
        "brand_authority",
        "backlink_growth",
    }:
        score += 1

    if keywords:
        score += 1

    if score >= 4:
        return "HIGH"

    if score >= 2:
        return "MEDIUM"

    return "LOW"


def build_marketing_strategy(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create a deterministic draft marketing campaign plan."""
    title = _clean_text(
        payload.get("article_title")
        or payload.get("title"),
        240,
    )

    public_url = _clean_text(
        payload.get("public_url"),
        2000,
    )

    publish_status = _clean_text(
        payload.get("publish_status")
        or payload.get("status"),
        50,
    ).upper()

    if not title:
        raise ValueError("Published article title is required.")

    if not public_url:
        raise ValueError("Published article public_url is required.")

    if not re.match(r"^https://", public_url, re.IGNORECASE):
        raise ValueError("Only an HTTPS public_url is allowed.")

    if publish_status != "PUBLISHED":
        raise PermissionError(
            "Marketing Strategy Agent accepts published content only."
        )

    goal = _normalize_goal(payload.get("goal"))
    channels = _select_channels(
        payload.get("channels"),
        goal=goal,
    )

    keywords = [
        _clean_text(item, 120)
        for item in payload.get("keywords", [])
        if _clean_text(item, 120)
    ][:20]

    target_country = _clean_text(
        payload.get("target_country") or "Global",
        100,
    )

    target_language = _clean_text(
        payload.get("target_language") or "English",
        50,
    )

    target_audience = _clean_text(
        payload.get("target_audience")
        or "Readers interested in gold market analysis and disciplined trading education",
        500,
    )

    duration_days = int(payload.get("duration_days") or 14)
    duration_days = max(1, min(duration_days, 90))

    recommended_agents = list(
        dict.fromkeys(
            [
                CHANNEL_AGENT_MAP[channel]
                for channel in channels
                if channel in CHANNEL_AGENT_MAP
            ]
            + (
                ["backlink_research_agent"]
                if goal in {
                    "brand_authority",
                    "backlink_growth",
                }
                else []
            )
            + (
                ["outreach_community_agent"]
                if goal in {
                    "lead_generation",
                    "backlink_growth",
                    "brand_authority",
                }
                else []
            )
            + ["marketing_analytics_agent"]
        )
    )

    campaign_name = _clean_text(
        payload.get("campaign_name")
        or f"{title} Marketing Campaign",
        240,
    )

    campaign_id = _clean_text(
        payload.get("campaign_id")
        or f"campaign-{abs(hash((title, public_url))) % 10_000_000:07d}",
        100,
    )

    return {
        "status": "PLANNED",
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "article_title": title,
        "public_url": public_url,
        "goal": goal.upper(),
        "priority": _priority(
            published=True,
            goal=goal,
            keywords=keywords,
        ),
        "target_country": target_country,
        "target_language": target_language,
        "target_audience": target_audience,
        "keywords": keywords,
        "duration_days": duration_days,
        "channels": channels,
        "recommended_agents": recommended_agents,
        "content_plan": {
            "social_post_variations_per_channel": 2,
            "short_video_script": (
                "instagram" in channels
                or "youtube_community" in channels
            ),
            "backlink_research_required": (
                "backlink_research_agent"
                in recommended_agents
            ),
            "community_outreach_required": (
                "outreach_community_agent"
                in recommended_agents
            ),
        },
        "kpis": [
            "article_clicks",
            "social_engagement",
            "referral_sessions",
            "qualified_leads",
            "backlinks_acquired",
        ],
        "execution_started": False,
        "external_actions_started": False,
        "owner_approval_required": True,
        "master_ai_review_required": True,
        "safe_summary": (
            "Marketing campaign plan prepared. "
            "No post, outreach, backlink or external delivery was executed."
        ),
    }


def run_marketing_strategy_agent(
    payload: dict[str, Any],
) -> str:
    """Return one campaign plan without performing external actions."""
    blocked_actions = (
        "publish_social",
        "send_email",
        "send_telegram",
        "send_whatsapp",
        "create_backlink",
        "post_forum",
        "submit_directory",
        "start_campaign",
    )

    for action in blocked_actions:
        if payload.get(action) is True:
            raise PermissionError(
                f"Marketing Strategy Agent cannot execute {action}."
            )

    result = build_marketing_strategy(payload)

    return json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
    )
