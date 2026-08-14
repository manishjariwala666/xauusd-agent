"""Tests for Venus Marketing Strategy Agent."""

import json

import pytest

from services.marketing_strategy_agent import (
    build_marketing_strategy,
    run_marketing_strategy_agent,
)


def _payload() -> dict:
    return {
        "article_title": "XAUUSD Weekly Market Outlook",
        "public_url": (
            "https://venusrealm.net/blog/"
            "xauusd-weekly-market-outlook"
        ),
        "publish_status": "PUBLISHED",
        "goal": "brand_authority",
        "target_country": "India",
        "target_language": "English",
        "target_audience": (
            "Gold traders and market analysis readers"
        ),
        "keywords": [
            "XAUUSD analysis",
            "gold market outlook",
        ],
    }


def test_campaign_plan_is_draft_only() -> None:
    result = build_marketing_strategy(_payload())

    assert result["status"] == "PLANNED"
    assert result["execution_started"] is False
    assert result["external_actions_started"] is False
    assert result["owner_approval_required"] is True
    assert result["master_ai_review_required"] is True


def test_brand_campaign_recommends_marketing_team() -> None:
    result = build_marketing_strategy(_payload())

    assert "social_media_agent" in result["recommended_agents"]
    assert "backlink_research_agent" in result["recommended_agents"]
    assert "outreach_community_agent" in result["recommended_agents"]
    assert "marketing_analytics_agent" in result["recommended_agents"]


def test_unpublished_content_is_blocked() -> None:
    payload = _payload()
    payload["publish_status"] = "DRAFT"

    with pytest.raises(PermissionError):
        build_marketing_strategy(payload)


def test_insecure_url_is_blocked() -> None:
    payload = _payload()
    payload["public_url"] = "http://venusrealm.net/test"

    with pytest.raises(ValueError):
        build_marketing_strategy(payload)


@pytest.mark.parametrize(
    "action",
    (
        "publish_social",
        "send_email",
        "send_telegram",
        "send_whatsapp",
        "create_backlink",
        "post_forum",
        "submit_directory",
        "start_campaign",
    ),
)
def test_external_execution_is_blocked(
    action: str,
) -> None:
    payload = _payload()
    payload[action] = True

    with pytest.raises(PermissionError):
        run_marketing_strategy_agent(payload)


def test_runner_returns_json_campaign() -> None:
    result = json.loads(
        run_marketing_strategy_agent(_payload())
    )

    assert result["status"] == "PLANNED"
    assert result["goal"] == "BRAND_AUTHORITY"
    assert result["channels"]
