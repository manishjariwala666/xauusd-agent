"""Tests for Venus Customer Support Agent."""

import json

import pytest

from services.customer_support_agent import (
    build_customer_support_response,
    run_customer_support_agent,
)


def test_new_client_is_qualified_without_external_action() -> None:
    result = build_customer_support_response({
        "message": (
            "I am a new client and want to join VenusRealm."
        ),
        "name": "Rahul",
        "email": "rahul@example.com",
        "country": "India",
    })

    assert result["intent"] == "new_client_onboarding"
    assert result["lead"]["crm_ready"] is True
    assert result["signal_provided"] is False
    assert result["external_action_started"] is False


def test_signal_request_is_refused() -> None:
    result = build_customer_support_response({
        "message": "Give me a buy signal with entry and stop loss.",
    })

    assert result["intent"] == "restricted_trading_request"
    assert result["signal_provided"] is False
    assert result["trading_advice_provided"] is False


def test_billing_request_requires_human_escalation() -> None:
    result = build_customer_support_response({
        "message": "I need a refund for my subscription.",
        "name": "Client",
        "email": "client@example.com",
    })

    assert result["intent"] == "billing_inquiry"
    assert result["human_escalation_required"] is True
    assert result["refund_action_started"] is False


def test_technical_support_warns_against_sensitive_data() -> None:
    result = build_customer_support_response({
        "message": "My dashboard login is not working.",
    })

    assert result["intent"] == "technical_support"
    assert "OTP" in result["reply"]
    assert result["account_changed"] is False


@pytest.mark.parametrize(
    "flag",
    (
        "give_signal",
        "send_signal",
        "place_trade",
        "change_account",
        "reset_password",
        "process_payment",
        "process_refund",
        "delete_account",
        "send_email",
        "send_whatsapp",
        "send_telegram",
    ),
)
def test_sensitive_execution_is_blocked(flag: str) -> None:
    with pytest.raises(PermissionError):
        run_customer_support_agent({
            "message": "Please help me.",
            flag: True,
        })


def test_runner_returns_json_support_result() -> None:
    result = json.loads(
        run_customer_support_agent({
            "message": "What features does VenusRealm provide?",
        })
    )

    assert result["status"] == "GUIDANCE_READY"
    assert result["intent"] == "product_information"
    assert result["signal_provided"] is False
