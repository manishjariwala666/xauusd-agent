"""Safe website customer support and lead guidance agent."""

from __future__ import annotations

import json
import re
from typing import Any


SUPPORTED_INTENTS = {
    "general_inquiry",
    "product_information",
    "pricing_inquiry",
    "new_client_onboarding",
    "technical_support",
    "billing_inquiry",
    "partnership_inquiry",
    "human_support",
}

HIGH_RISK_TERMS = (
    "refund",
    "chargeback",
    "legal",
    "lawyer",
    "complaint",
    "fraud",
    "account hacked",
    "unauthorized payment",
    "delete my account",
)

SIGNAL_TERMS = (
    "buy signal",
    "sell signal",
    "give signal",
    "entry price",
    "stop loss",
    "take profit",
    "guaranteed profit",
    "which trade",
    "should i buy",
    "should i sell",
)


def _clean(value: object, limit: int = 1000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _detect_intent(message: str) -> str:
    normalized = message.casefold()

    if any(
        term in normalized
        for term in (
            "human",
            "person",
            "support team",
            "agent se baat",
            "call me",
        )
    ):
        return "human_support"

    if any(
        term in normalized
        for term in (
            "login",
            "password",
            "dashboard",
            "not working",
            "error",
            "access",
            "technical",
        )
    ):
        return "technical_support"

    if any(
        term in normalized
        for term in (
            "payment",
            "invoice",
            "billing",
            "refund",
            "renewal",
            "chargeback",
        )
    ):
        return "billing_inquiry"

    if any(
        term in normalized
        for term in (
            "price",
            "pricing",
            "plan",
            "subscription",
            "package",
            "cost",
        )
    ):
        return "pricing_inquiry"

    if any(
        term in normalized
        for term in (
            "partner",
            "partnership",
            "affiliate",
            "business proposal",
        )
    ):
        return "partnership_inquiry"

    if any(
        term in normalized
        for term in (
            "new client",
            "start",
            "sign up",
            "register",
            "onboarding",
            "how to join",
        )
    ):
        return "new_client_onboarding"

    if any(
        term in normalized
        for term in (
            "feature",
            "service",
            "what is venusrealm",
            "how it works",
            "platform",
        )
    ):
        return "product_information"

    return "general_inquiry"


def _lead_score(
    *,
    intent: str,
    has_name: bool,
    has_contact: bool,
    message: str,
) -> str:
    score = 0

    if intent in {
        "pricing_inquiry",
        "new_client_onboarding",
        "partnership_inquiry",
    }:
        score += 2

    if has_name:
        score += 1

    if has_contact:
        score += 2

    normalized = message.casefold()

    if any(
        term in normalized
        for term in (
            "ready to start",
            "want to join",
            "buy plan",
            "subscribe",
            "contact me",
        )
    ):
        score += 2

    if score >= 5:
        return "HOT"

    if score >= 3:
        return "WARM"

    return "COLD"


def build_customer_support_response(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create one safe support and lead-guidance response."""
    message = _clean(
        payload.get("message")
        or payload.get("customer_message"),
        5000,
    )

    if not message:
        raise ValueError("Customer message is required.")

    normalized = message.casefold()

    if any(term in normalized for term in SIGNAL_TERMS):
        return {
            "status": "GUIDANCE_READY",
            "intent": "restricted_trading_request",
            "reply": (
                "Main customer support aur platform guidance ke liye hoon. "
                "Main buy/sell signal, entry, stop-loss, take-profit ya personal "
                "trading recommendation provide nahi karta. Main VenusRealm ke "
                "features, plans, onboarding aur account-support process samjha "
                "sakta hoon."
            ),
            "lead": None,
            "signal_provided": False,
            "trading_advice_provided": False,
            "human_escalation_required": False,
            "external_action_started": False,
        }

    intent = _detect_intent(message)

    name = _clean(
        payload.get("name")
        or payload.get("customer_name"),
        120,
    )

    email = _clean(payload.get("email"), 320)
    phone = _clean(
        payload.get("phone")
        or payload.get("whatsapp"),
        80,
    )

    country = _clean(
        payload.get("country") or "Not provided",
        100,
    )

    contact_available = bool(email or phone)

    high_risk = any(
        term in normalized
        for term in HIGH_RISK_TERMS
    )

    escalation_required = (
        high_risk
        or intent in {
            "human_support",
            "billing_inquiry",
            "partnership_inquiry",
        }
    )

    replies = {
        "general_inquiry": (
            "Namaste! Main VenusRealm website support assistant hoon. "
            "Main platform features, plans, onboarding aur technical guidance "
            "mein help kar sakta hoon. Aap kis cheez ke baare mein jaanna "
            "chahte hain?"
        ),
        "product_information": (
            "VenusRealm ek gold-market analysis aur educational platform hai. "
            "Main aapko available features, dashboard workflow aur onboarding "
            "process step-by-step samjha sakta hoon. Aap beginner hain ya "
            "pehle se trading platforms use karte hain?"
        ),
        "pricing_inquiry": (
            "Main available plan information aur plan comparison explain kar "
            "sakta hoon. Final pricing aur subscription confirmation official "
            "checkout ya support team se verify hogi. Aap individual plan, "
            "business plan ya trial information dekhna chahte hain?"
        ),
        "new_client_onboarding": (
            "Main aapko new-client onboarding mein guide karunga: account "
            "registration, email verification, dashboard access aur platform "
            "features samajhna. Aap apna naam aur preferred contact method "
            "share kar sakte hain."
        ),
        "technical_support": (
            "Technical issue diagnose karne ke liye browser/device, exact error "
            "message aur issue kis page par aa raha hai ye details bhejiye. "
            "Password, OTP, card number ya private credentials share mat kijiye."
        ),
        "billing_inquiry": (
            "Billing, payment, invoice ya refund request ko human support team "
            "review karegi. Main request details collect kar sakta hoon, lekin "
            "payment, refund ya subscription change khud execute nahi karunga."
        ),
        "partnership_inquiry": (
            "Partnership request ko business team review karegi. Company name, "
            "proposal summary, website aur preferred contact details share "
            "kijiye. Main isse qualified business lead ke roop mein prepare "
            "karunga."
        ),
        "human_support": (
            "Main aapki request human support ke liye prepare kar raha hoon. "
            "Kripya apna naam, email ya WhatsApp aur short issue summary share "
            "kijiye. Sensitive credentials share mat kijiye."
        ),
    }

    lead_score = _lead_score(
        intent=intent,
        has_name=bool(name),
        has_contact=contact_available,
        message=message,
    )

    missing_fields: list[str] = []

    if not name:
        missing_fields.append("name")

    if not contact_available and intent in {
        "pricing_inquiry",
        "new_client_onboarding",
        "partnership_inquiry",
        "human_support",
        "billing_inquiry",
    }:
        missing_fields.append("email_or_whatsapp")

    lead = {
        "name": name or None,
        "email": email or None,
        "phone": phone or None,
        "country": country,
        "intent": intent,
        "lead_score": lead_score,
        "missing_fields": missing_fields,
        "crm_ready": bool(name and contact_available),
    }

    return {
        "status": "GUIDANCE_READY",
        "intent": intent,
        "reply": replies[intent],
        "lead": lead,
        "signal_provided": False,
        "trading_advice_provided": False,
        "account_changed": False,
        "payment_action_started": False,
        "refund_action_started": False,
        "human_escalation_required": escalation_required,
        "external_action_started": False,
        "owner_review_required": escalation_required,
        "safe_summary": (
            "Customer guidance and lead qualification prepared. "
            "No signal, account, payment or external action was executed."
        ),
    }


def run_customer_support_agent(
    payload: dict[str, Any],
) -> str:
    """Return support guidance without executing sensitive actions."""
    forbidden_flags = (
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
    )

    for flag in forbidden_flags:
        if payload.get(flag) is True:
            raise PermissionError(
                f"Customer Support Agent cannot execute {flag}."
            )

    result = build_customer_support_response(payload)

    return json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
    )
