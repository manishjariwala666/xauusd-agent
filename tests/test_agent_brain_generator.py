"""Tests for preview-only Agent Brain Generator."""

import pytest

from services.agent_brain_generator import (
    generate_brain_preview,
    normalize_agent_key,
)


def test_normalizes_agent_key() -> None:
    assert (
        normalize_agent_key("Social Media")
        == "social_media_agent"
    )


def test_generates_safe_support_brain_preview() -> None:
    result = generate_brain_preview({
        "display_name": "Lead Qualification Agent",
        "department": "support",
        "purpose": (
            "Guide website visitors and prepare qualified "
            "new-client lead summaries."
        ),
        "allowed_inputs": [
            "customer_message",
            "contact_details",
        ],
        "output_schema": [
            "intent",
            "lead_score",
        ],
    })

    assert result["state"] == "BRAIN_PREVIEW"
    assert result["agent_key"] == (
        "lead_qualification_agent"
    )
    assert result["execution_enabled"] is False
    assert result["registry_written"] is False
    assert result["runner_written"] is False
    assert "provide_trading_signal" in (
        result["forbidden_actions"]
    )


def test_external_action_infers_high_risk() -> None:
    result = generate_brain_preview({
        "display_name": "Social Publishing Agent",
        "department": "marketing",
        "purpose": (
            "Prepare and publish approved social media posts."
        ),
        "requested_actions": ["publish_social_post"],
    })

    assert result["default_risk"] == "HIGH"
    assert result["owner_approval_required"] is True


def test_critical_agent_has_no_automatic_actions() -> None:
    result = generate_brain_preview({
        "display_name": "Refund Processing Agent",
        "department": "support",
        "purpose": (
            "Review and process customer refund requests."
        ),
        "requested_actions": ["process_refund"],
    })

    assert result["default_risk"] == "CRITICAL"
    assert result["automatic_actions"] == []
    assert result["execution_enabled"] is False


def test_risk_cannot_be_downgraded() -> None:
    result = generate_brain_preview({
        "display_name": "Deployment Agent",
        "department": "general",
        "purpose": (
            "Deploy approved application changes to production."
        ),
        "risk": "LOW",
    })

    assert result["default_risk"] == "CRITICAL"


def test_short_purpose_is_rejected() -> None:
    with pytest.raises(ValueError):
        generate_brain_preview({
            "display_name": "Test Agent",
            "purpose": "Do work",
        })
