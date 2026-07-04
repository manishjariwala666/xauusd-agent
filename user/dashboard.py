"""Payment-aware user dashboard with server-side premium gating."""

from __future__ import annotations

from datetime import datetime
import html
import json
import logging
from typing import Any

import streamlit as st

from config import get_settings
from core.auth import (
    get_current_user_id,
    get_payment_status,
    is_payment_verified,
)
from services.content_service import (
    PAYMENT_NOT_STARTED,
    PAYMENT_PENDING,
    PAYMENT_REJECTED,
    PAYMENT_UNDER_REVIEW,
    PAYMENT_VERIFIED,
    get_site_setting,
    get_user_payment,
    list_member_content,
    submit_payment,
)


LOGGER = logging.getLogger(__name__)
_SIGNAL_PREFIX = "XAU_SIGNAL_V1:"


def render_user_dashboard(supabase: Any) -> None:
    """Render payment states and gate every premium resource server-side."""
    settings = get_settings()
    user_id = get_current_user_id()
    if user_id is None:
        st.error("Your account session is invalid.")
        st.stop()

    try:
        payment = get_user_payment(user_id)
        payment_status = str(
            payment.get("payment_status")
            or get_payment_status()
            or PAYMENT_NOT_STARTED
        )
    except Exception:
        LOGGER.exception("Unable to load user payment state.")
        payment = {"payment_status": get_payment_status()}
        payment_status = get_payment_status()

    st.markdown("## Member Dashboard")
    st.caption(
        "Manage subscription verification and access protected market content."
    )
    _render_payment_status(payment_status, payment)

    if not is_payment_verified() or payment_status != PAYMENT_VERIFIED:
        _render_payment_instructions(
            user_id=user_id,
            payment_status=payment_status,
            wallet=settings.usdt_wallet_address,
            network=settings.usdt_network,
            price=settings.subscription_price_usdt,
        )
        st.markdown(
            """
            <div class="locked-box">
                🔒 Premium signals, paid content, Telegram, and WhatsApp links
                unlock only after payment status becomes VERIFIED.
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_risk_warning()
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Primary Market", "XAUUSD")
    col2.metric("Subscription", "Verified")
    col3.metric("Risk Guideline", "Max 1%")

    _render_premium_access()
    if st.button("Refresh Signals", use_container_width=False):
        st.rerun()
    render_signal_feed(supabase, "No active signal is available right now.")
    _render_member_content()
    _render_risk_warning()


def render_signal_feed(supabase: Any, empty_message: str) -> None:
    """Load recent admin signals; callers must enforce access authorization."""
    try:
        response = (
            supabase.table("signals")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
    except Exception:
        LOGGER.exception("Signal feed query failed.")
        st.error("Signal feed is temporarily unavailable.")
        return

    signals = response.data or []
    if not signals:
        st.info(empty_message)
        return
    for signal in signals:
        _render_signal(signal)


def _render_premium_access() -> None:
    if not is_payment_verified():
        return
    settings = get_settings()
    try:
        telegram_url = get_site_setting("telegram_invite_url")
        whatsapp_url = get_site_setting("whatsapp_invite_url")
    except Exception:
        LOGGER.exception("Protected invite-link loading failed.")
        telegram_url = ""
        whatsapp_url = ""
    telegram_url = telegram_url or settings.telegram_invite_url
    whatsapp_url = whatsapp_url or settings.support_whatsapp_url
    with st.expander("Verified Member Access", expanded=True):
        if telegram_url:
            st.link_button(
                "Open Private Telegram Channel",
                telegram_url,
                use_container_width=True,
            )
        if whatsapp_url:
            st.link_button(
                "Open Private WhatsApp Channel",
                whatsapp_url,
                use_container_width=True,
            )
        if not (telegram_url or whatsapp_url):
            st.info("Premium contact links are being configured.")


def _render_payment_status(
    payment_status: str,
    payment: dict[str, Any],
) -> None:
    labels = {
        PAYMENT_NOT_STARTED: (
            "Payment not started",
            "Complete payment when ready.",
        ),
        PAYMENT_PENDING: (
            "Payment pending",
            "Your transaction was submitted.",
        ),
        PAYMENT_UNDER_REVIEW: (
            "Payment under review",
            "An administrator is verifying your transaction.",
        ),
        PAYMENT_VERIFIED: (
            "Payment verified",
            "Premium access is active.",
        ),
        PAYMENT_REJECTED: (
            "Payment rejected",
            payment.get("review_note")
            or "Review the transaction details and submit again.",
        ),
    }
    title, detail = labels.get(
        payment_status,
        ("Payment status unavailable", "Contact support for assistance."),
    )
    css_class = (
        "status-verified"
        if payment_status == PAYMENT_VERIFIED
        else "status-rejected"
        if payment_status == PAYMENT_REJECTED
        else ""
    )
    st.markdown(
        f"""
        <div class="status-banner {css_class}">
            <strong>{html.escape(title)}</strong><br>
            <span class="nav-note">{html.escape(str(detail))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_payment_instructions(
    *,
    user_id: int,
    payment_status: str,
    wallet: str,
    network: str,
    price: str,
) -> None:
    st.markdown("### USDT Payment Verification")
    if not wallet or not network or not price:
        st.warning(
            "Payment instructions are temporarily unavailable. "
            "Please contact support."
        )
        return
    col1, col2 = st.columns(2)
    col1.metric("Amount", f"{price} USDT")
    col2.metric("Network", network)
    st.code(wallet, language=None)
    st.caption(
        "Send only USDT using the exact network shown. Incorrect-network "
        "transactions may be unrecoverable."
    )

    if payment_status in {PAYMENT_PENDING, PAYMENT_UNDER_REVIEW}:
        st.info("Your existing submission is being processed.")
        return

    with st.form("payment_submission_form"):
        transaction_id = st.text_input(
            "USDT transaction ID (TXID)",
            help="Enter the public blockchain transaction identifier.",
        )
        confirmed = st.checkbox(
            "I confirm the amount and network match the instructions above."
        )
        submitted = st.form_submit_button(
            "Submit Payment for Review",
            type="primary",
            use_container_width=True,
        )
    if not submitted:
        return
    if not confirmed:
        st.warning("Confirm the payment details before submitting.")
        return
    try:
        submit_payment(
            user_id=user_id,
            transaction_id=transaction_id,
            amount_usdt=price,
            network=network,
        )
    except Exception as exc:
        LOGGER.exception("Payment submission failed.")
        message = (
            str(exc)
            if isinstance(exc, ValueError)
            else "Payment submission failed."
        )
        st.error(message)
        return
    st.success("Payment submitted. Status is now PENDING.")
    st.rerun()


def _render_member_content() -> None:
    try:
        items = list_member_content(limit=12)
    except Exception:
        LOGGER.exception("Member content loading failed.")
        st.error("Premium content is temporarily unavailable.")
        return
    if not items:
        return
    st.markdown("### Premium Research")
    for item in items:
        title = (
            f"{str(item['content_type']).replace('_', ' ')} · "
            f"{item['title']}"
        )
        with st.expander(title):
            if item.get("image_url"):
                st.image(item["image_url"], use_container_width=True)
            st.write(item.get("body") or item.get("excerpt") or "")
            if item.get("external_url"):
                st.link_button("Open Resource", item["external_url"])


def _render_risk_warning() -> None:
    st.markdown(
        """
        <div class="risk-box">
            Trading involves substantial risk. Signals and analysis are
            informational only; they do not guarantee returns or replace
            independent financial judgment.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_signal(row: dict[str, Any]) -> None:
    message = str(row.get("message", ""))
    payload = _parse_signal(message)
    sender = html.escape(str(row.get("sender", "Admin")))
    created_at = html.escape(_format_time(row.get("created_at")))
    if payload is None:
        st.markdown(
            f"""
            <div class="signal-card signal-info">
                <div class="signal-title">Market Update</div>
                <div class="signal-note">{html.escape(message)}</div>
                <div class="signal-time">{sender} · {created_at}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    side = payload["side"]
    css_class = "signal-buy" if side == "BUY" else "signal-sell"
    fields = (
        ("Entry", payload.get("entry", "—")),
        ("Stop Loss", payload.get("stop_loss", "—")),
        ("Take Profit 1", payload.get("tp1", "—")),
        ("Take Profit 2", payload.get("tp2", "—")),
    )
    values = "".join(
        '<div class="signal-value">'
        f'<div class="signal-label">{html.escape(label)}</div>'
        f'<div class="signal-number">{html.escape(str(value))}</div>'
        "</div>"
        for label, value in fields
    )
    st.markdown(
        f"""
        <div class="signal-card {css_class}">
            <div class="signal-title">XAUUSD {side}</div>
            <div class="signal-grid">{values}</div>
            <div class="signal-note">
                {html.escape(str(payload.get("note", "")))}
            </div>
            <div class="signal-time">{sender} · {created_at}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _parse_signal(message: str) -> dict[str, Any] | None:
    if not message.startswith(_SIGNAL_PREFIX):
        return None
    try:
        payload = json.loads(message[len(_SIGNAL_PREFIX) :])
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if payload.get("side") in {"BUY", "SELL"} else None


def _format_time(value: Any) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y · %I:%M %p")
    except ValueError:
        return str(value)[:16].replace("T", " ")
