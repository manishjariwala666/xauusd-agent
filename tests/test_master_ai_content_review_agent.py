"""Tests for Master AI Content Review Agent."""

import json

import pytest

from services.master_ai_content_review_agent import (
    APPROVE,
    NEEDS_CHANGES,
    REJECT,
    review_cms_document,
    run_master_ai_content_review_agent,
)


def _document() -> dict:
    body = " ".join(
        ["Educational XAUUSD market content with risk control."] * 80
    )

    return {
        "id": None,
        "title": "XAUUSD Risk Management Guide",
        "slug": "xauusd-risk-management-guide",
        "excerpt": (
            "A practical educational guide to XAUUSD risk management, "
            "position sizing and disciplined trading decisions."
        ),
        "status": "draft",
        "categoryId": None,
        "tags": ["xauusd", "risk"],
        "featuredMediaId": 4,
        "blocks": [
            {
                "id": "heading-1",
                "type": "heading",
                "level": 1,
                "text": "XAUUSD Risk Management Guide",
            },
            {
                "id": "paragraph-1",
                "type": "paragraph",
                "html": f"<p>{body}</p>",
            },
            {
                "id": "heading-2",
                "type": "heading",
                "level": 2,
                "text": "Trading Risk Disclaimer",
            },
            {
                "id": "paragraph-2",
                "type": "paragraph",
                "html": (
                    "<p>Educational content only. Trading involves risk "
                    "and is not financial advice.</p>"
                ),
            },
        ],
        "seo": {
            "metaTitle": "XAUUSD Risk Management Guide",
            "metaDescription": (
                "Learn practical XAUUSD risk management, disciplined "
                "position sizing and essential trading safeguards."
            ),
            "focusKeyword": "XAUUSD risk management",
            "canonicalUrl": "",
            "robotsIndex": False,
            "robotsFollow": False,
            "schemaJsonLd": None,
        },
    }


def test_clean_draft_is_approved_for_owner_review() -> None:
    result = review_cms_document(_document())

    assert result["decision"] == APPROVE
    assert result["publish_allowed"] is False
    assert result["owner_approval_required"] is True


def test_missing_featured_image_needs_changes() -> None:
    document = _document()
    document["featuredMediaId"] = None

    result = review_cms_document(document)

    assert result["decision"] == NEEDS_CHANGES
    assert "Featured image is missing." in result["warnings"]


def test_guaranteed_profit_claim_is_rejected() -> None:
    document = _document()
    document["blocks"].append({
        "id": "unsafe",
        "type": "paragraph",
        "html": "<p>This strategy provides guaranteed profit.</p>",
    })

    result = review_cms_document(document)

    assert result["decision"] == REJECT
    assert result["critical_issues"]


def test_runner_never_publishes_or_delivers() -> None:
    with pytest.raises(PermissionError):
        run_master_ai_content_review_agent({
            "document": _document(),
            "publish": True,
        })

    with pytest.raises(PermissionError):
        run_master_ai_content_review_agent({
            "document": _document(),
            "send_telegram": True,
        })

    with pytest.raises(PermissionError):
        run_master_ai_content_review_agent({
            "document": _document(),
            "send_whatsapp": True,
        })


def test_runner_returns_json_review() -> None:
    result = json.loads(
        run_master_ai_content_review_agent({
            "document": _document(),
        })
    )

    assert result["decision"] == APPROVE
    assert result["owner_approval_required"] is True
