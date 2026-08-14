"""Tests for Venus Social Media Agent."""

import json

import pytest

from services.social_media_agent import (
    build_social_media_drafts,
    run_social_media_agent,
)


def _payload() -> dict:
    return {
        "article_title": "XAUUSD Weekly Market Outlook",
        "public_url": (
            "https://venusrealm.net/blog/"
            "xauusd-weekly-market-outlook"
        ),
        "publish_status": "PUBLISHED",
        "campaign_id": "campaign-test-001",
        "channels": [
            "linkedin",
            "facebook",
            "instagram",
            "x",
        ],
        "keywords": [
            "XAUUSD analysis",
            "gold market outlook",
        ],
    }


def test_builds_two_drafts_per_channel() -> None:
    result = build_social_media_drafts(_payload())

    assert result["status"] == "DRAFT_READY"
    assert result["variations_per_channel"] == 2
    assert result["publishing_enabled"] is False
    assert result["external_actions_started"] is False

    for channel in _payload()["channels"]:
        assert len(result["drafts"][channel]) == 2


def test_preserves_public_article_url() -> None:
    result = build_social_media_drafts(_payload())

    for drafts in result["drafts"].values():
        for draft in drafts:
            assert _payload()["public_url"] in draft["caption"]


def test_unpublished_content_is_blocked() -> None:
    payload = _payload()
    payload["publish_status"] = "DRAFT"

    with pytest.raises(PermissionError):
        build_social_media_drafts(payload)


def test_insecure_url_is_blocked() -> None:
    payload = _payload()
    payload["public_url"] = "http://venusrealm.net/test"

    with pytest.raises(ValueError):
        build_social_media_drafts(payload)


@pytest.mark.parametrize(
    "action",
    (
        "publish_social",
        "publish_social_post",
        "post_linkedin",
        "post_facebook",
        "post_instagram",
        "post_x",
        "send_telegram",
        "send_whatsapp",
        "send_email",
        "start_campaign",
    ),
)
def test_external_execution_is_blocked(action: str) -> None:
    payload = _payload()
    payload[action] = True

    with pytest.raises(PermissionError):
        run_social_media_agent(payload)


def test_runner_returns_json_without_external_execution() -> None:
    result = json.loads(run_social_media_agent(_payload()))

    assert result["status"] == "DRAFT_READY"
    assert result["owner_approval_required"] is True
    assert result["master_ai_review_required"] is True
    assert result["external_actions_started"] is False
