"""Draft-only social media content agent for VenusRealm."""

from __future__ import annotations

import json
import re
from typing import Any


SUPPORTED_CHANNELS = (
    "linkedin",
    "facebook",
    "instagram",
    "x",
    "pinterest",
    "youtube_community",
    "telegram",
    "whatsapp",
)

CHANNEL_LIMITS = {
    "linkedin": 1200,
    "facebook": 1000,
    "instagram": 900,
    "x": 260,
    "pinterest": 450,
    "youtube_community": 700,
    "telegram": 900,
    "whatsapp": 700,
}


def _clean(value: object, limit: int = 2000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _normalize_channel(value: object) -> str:
    return (
        _clean(value, 80)
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _hashtags(keywords: list[str], limit: int = 5) -> list[str]:
    tags: list[str] = []

    for keyword in keywords:
        normalized = re.sub(
            r"[^A-Za-z0-9]+",
            "",
            keyword.title(),
        )

        if normalized:
            tags.append(f"#{normalized}")

    defaults = ["#XAUUSD", "#GoldMarket", "#MarketAnalysis"]

    for tag in defaults:
        if tag not in tags:
            tags.append(tag)

    return tags[:limit]


def _channel_drafts(
    *,
    channel: str,
    title: str,
    public_url: str,
    hashtags: list[str],
) -> list[dict[str, str]]:
    tag_line = " ".join(hashtags)

    openings = {
        "linkedin": (
            "New VenusRealm market education update:",
            "A fresh gold-market research article is now available:",
        ),
        "facebook": (
            "New on VenusRealm:",
            "Gold market readers — this new article is live:",
        ),
        "instagram": (
            "New XAUUSD education update ✨",
            "Gold market insight is now live 📊",
        ),
        "x": (
            "New on VenusRealm:",
            "Fresh XAUUSD market education:",
        ),
        "pinterest": (
            "Gold market education from VenusRealm:",
            "Save this XAUUSD research reference:",
        ),
        "youtube_community": (
            "New VenusRealm community update:",
            "Our latest gold-market article is available:",
        ),
        "telegram": (
            "📊 New VenusRealm article:",
            "🟡 Fresh XAUUSD education:",
        ),
        "whatsapp": (
            "New VenusRealm article:",
            "Fresh gold-market education:",
        ),
    }

    ctas = {
        "linkedin": "Read the full article:",
        "facebook": "Read more:",
        "instagram": "Full article:",
        "x": "Read:",
        "pinterest": "Open the guide:",
        "youtube_community": "Read the full article:",
        "telegram": "Read here:",
        "whatsapp": "Read here:",
    }

    limit = CHANNEL_LIMITS[channel]
    drafts: list[dict[str, str]] = []

    for index, opening in enumerate(openings[channel], start=1):
        body = (
            f"{opening}\n\n"
            f"{title}\n\n"
            f"{ctas[channel]} {public_url}\n\n"
            f"{tag_line}"
        )

        body = body[:limit].rstrip()

        drafts.append(
            {
                "variation": str(index),
                "caption": body,
                "cta": ctas[channel],
            }
        )

    return drafts


def build_social_media_drafts(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Prepare platform-specific drafts without external posting."""
    title = _clean(
        payload.get("article_title")
        or payload.get("title"),
        240,
    )

    public_url = _clean(payload.get("public_url"), 2000)

    publish_status = _clean(
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
            "Social Media Agent accepts published content only."
        )

    requested_channels = payload.get("channels") or [
        "linkedin",
        "facebook",
        "instagram",
        "x",
    ]

    if not isinstance(requested_channels, list):
        raise ValueError("channels must be a list.")

    channels = list(
        dict.fromkeys(
            channel
            for channel in (
                _normalize_channel(item)
                for item in requested_channels
            )
            if channel in SUPPORTED_CHANNELS
        )
    )[:8]

    if not channels:
        raise ValueError("No supported social channels were requested.")

    keywords = [
        _clean(item, 120)
        for item in payload.get("keywords", [])
        if _clean(item, 120)
    ][:20]

    hashtags = _hashtags(keywords)

    drafts = {
        channel: _channel_drafts(
            channel=channel,
            title=title,
            public_url=public_url,
            hashtags=hashtags,
        )
        for channel in channels
    }

    return {
        "status": "DRAFT_READY",
        "campaign_id": _clean(payload.get("campaign_id"), 120) or None,
        "article_title": title,
        "public_url": public_url,
        "channels": channels,
        "hashtags": hashtags,
        "drafts": drafts,
        "variations_per_channel": 2,
        "execution_started": False,
        "external_actions_started": False,
        "publishing_enabled": False,
        "owner_approval_required": True,
        "master_ai_review_required": True,
        "safe_summary": (
            "Platform-specific social media drafts prepared. "
            "No social post, Telegram message, WhatsApp message "
            "or external delivery was executed."
        ),
    }


def run_social_media_agent(
    payload: dict[str, Any],
) -> str:
    """Return social drafts while blocking all external actions."""
    blocked_actions = (
        "publish_social",
        "publish_social_post",
        "post_linkedin",
        "post_facebook",
        "post_instagram",
        "post_x",
        "post_pinterest",
        "post_youtube",
        "send_telegram",
        "send_whatsapp",
        "send_email",
        "start_campaign",
    )

    for action in blocked_actions:
        if payload.get(action) is True:
            raise PermissionError(
                f"Social Media Agent cannot execute {action}."
            )

    return json.dumps(
        build_social_media_drafts(payload),
        ensure_ascii=False,
        separators=(",", ":"),
    )
