"""Tests for guarded Publish Approval Agent."""

import json

import pytest

from services.master_ai_publish_approval_agent import (
    run_master_ai_publish_approval_agent,
    validate_publish_approval,
)


def _draft() -> dict:
    return {
        "id": 101,
        "content_type": "AI_BLOG",
        "title": "Gold Risk Guide",
        "slug": "gold-risk-guide",
        "status": "draft",
        "scheduled_at": None,
    }


def _approved_payload() -> dict:
    return {
        "content_id": 101,
        "actor_id": 7,
        "request_id": "publish-request-101",
        "master_review_decision": "APPROVE",
        "owner_approved_publish": True,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("master_review_decision", "NEEDS_CHANGES"),
        ("master_review_decision", "REJECT"),
        ("owner_approved_publish", False),
    ),
)
def test_missing_approval_gate_is_blocked(
    field: str,
    value: object,
) -> None:
    payload = _approved_payload()
    payload[field] = value

    with pytest.raises(PermissionError):
        validate_publish_approval(payload, _draft())


def test_already_published_content_is_blocked() -> None:
    content = _draft()
    content["status"] = "published"

    with pytest.raises(ValueError):
        validate_publish_approval(
            _approved_payload(),
            content,
        )


def test_scheduled_content_is_blocked() -> None:
    content = _draft()
    content["scheduled_at"] = "2026-08-06T12:00:00Z"

    with pytest.raises(PermissionError):
        validate_publish_approval(
            _approved_payload(),
            content,
        )


@pytest.mark.parametrize(
    "field",
    (
        "send_telegram",
        "send_whatsapp",
        "delete",
        "unpublish",
    ),
)
def test_unrelated_sensitive_actions_are_blocked(
    field: str,
) -> None:
    payload = _approved_payload()
    payload[field] = True

    with pytest.raises(PermissionError):
        validate_publish_approval(payload, _draft())


def test_approved_draft_publishes_once(monkeypatch) -> None:
    transitions: list[dict] = []

    monkeypatch.setattr(
        "services.master_ai_publish_approval_agent.get_admin_content",
        lambda **_: _draft(),
    )

    def fake_transition(**kwargs):
        transitions.append(kwargs)
        return {
            **_draft(),
            "status": "published",
        }

    monkeypatch.setattr(
        "services.master_ai_publish_approval_agent.transition_content",
        fake_transition,
    )

    monkeypatch.setattr(
        "services.master_ai_publish_approval_agent.public_content_url",
        lambda content_type, slug: (
            f"https://venusrealm.net/blog/{slug}"
        ),
    )

    result = json.loads(
        run_master_ai_publish_approval_agent(
            _approved_payload()
        )
    )

    assert result["status"] == "PUBLISHED"
    assert result["public_url"] == (
        "https://venusrealm.net/blog/gold-risk-guide"
    )
    assert result["telegram_delivery_started"] is False
    assert result["whatsapp_delivery_started"] is False
    assert transitions == [{
        "kind": "posts",
        "content_id": 101,
        "actor_id": 7,
        "action": "publish",
        "request_id": "publish-request-101",
    }]
