"""Separate role-protected website and signal administration console."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from typing import Any

from loguru import logger
import streamlit as st
from sqlalchemy import text

from core.auth import ROLE_ADMIN, get_current_role, get_current_user_id
from core.database import session_scope
from services.ai_agent_service import (
    list_ai_agents,
    run_ai_agent,
    set_ai_agent_enabled,
)
from services.content_service import (
    CONTENT_TYPES,
    PAYMENT_STATES,
    delete_content,
    get_site_setting,
    list_categories,
    list_content,
    list_payment_reviews,
    review_payment,
    save_category,
    save_content,
    save_site_setting,
    upload_profit_screenshot,
)
from services.google_sheets import GoogleSheetsService
from services.market_data import MarketDataService
from services.telegram_service import TelegramService
from user.dashboard import render_signal_feed


def render_admin_dashboard(supabase: Any) -> None:
    """Render admin-only controls without exposing them to user sessions."""
    if get_current_role() != ROLE_ADMIN:
        st.error("Administrator access is required.")
        st.stop()

    st.markdown("## Administration Console")
    (
        overview_tab,
        payments_tab,
        content_tab,
        categories_tab,
        proof_tab,
        channels_tab,
        signals_tab,
        automation_tab,
        ai_agents_tab,
    ) = st.tabs(
        [
            "Overview",
            "Payments",
            "Content",
            "Categories",
            "Profit Proof",
            "Channel Links",
            "Signals",
            "Pipeline",
            "AI Agents",
        ]
    )
    with overview_tab:
        _render_overview()
    with payments_tab:
        _render_payment_reviews()
    with content_tab:
        _render_content_manager()
    with categories_tab:
        _render_category_manager()
    with proof_tab:
        _render_profit_screenshots(supabase)
    with channels_tab:
        _render_channel_settings()
    with signals_tab:
        _render_signal_form()
        st.divider()
        render_signal_feed(supabase, "No signal has been published.")
    with automation_tab:
        _render_pipeline_health()
        st.divider()
        _render_telegram_test(supabase)
    with ai_agents_tab:
        _render_ai_agents(supabase)


def _render_overview() -> None:
    try:
        with session_scope() as session:
            metrics = (
                session.execute(
                    text(
                        """
                        SELECT
                            (SELECT COUNT(*) FROM public.users)
                                AS registered_users,
                            (
                                SELECT COUNT(*)
                                FROM public.subscriptions
                                WHERE payment_status IN (
                                    'PENDING',
                                    'UNDER_REVIEW'
                                )
                            ) AS payment_reviews,
                            (
                                SELECT COUNT(*)
                                FROM public.content_items
                                WHERE is_published = TRUE
                            ) AS published_content,
                            (
                                SELECT COUNT(*)
                                FROM public.content_categories
                                WHERE is_active = TRUE
                            ) AS active_categories
                        """
                    )
                )
                .mappings()
                .one()
            )
    except Exception:
        logger.exception("Admin overview loading failed")
        st.error("Overview metrics are temporarily unavailable.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registered Users", int(metrics["registered_users"]))
    col2.metric("Payment Reviews", int(metrics["payment_reviews"]))
    col3.metric("Published Content", int(metrics["published_content"]))
    col4.metric("Active Categories", int(metrics["active_categories"]))
    st.info(
        "AI-generated drafts may be reviewed and published here, but agent "
        "prompts, credentials, and internal reasoning are never displayed."
    )


def _render_payment_reviews() -> None:
    st.subheader("USDT Payment Reviews")
    try:
        users = list_payment_reviews()
    except Exception:
        logger.exception("Payment review list failed")
        st.error("Payment records are temporarily unavailable.")
        return
    if not users:
        st.info("No registered users.")
        return

    reviewer_id = get_current_user_id()
    if reviewer_id is None:
        st.error("Administrator session is invalid.")
        return
    for user in users:
        with st.container(border=True):
            details, decision = st.columns([2.2, 1.2])
            with details:
                st.markdown(f"**{user['email']}**")
                st.caption(
                    f"Email: {'Verified' if user['email_verified'] else 'Unverified'} · "
                    f"WhatsApp: {user.get('whatsapp') or '—'}"
                )
                st.write(f"Current status: **{user['payment_status']}**")
                st.code(user.get("transaction_id") or "No TXID submitted")
                if user.get("amount_usdt") or user.get("network"):
                    st.caption(
                        f"Amount: {user.get('amount_usdt') or '—'} USDT · "
                        f"Network: {user.get('network') or '—'}"
                    )
            with decision:
                status = st.selectbox(
                    "Decision",
                    PAYMENT_STATES,
                    index=PAYMENT_STATES.index(user["payment_status"]),
                    key=f"payment_status_{user['user_id']}",
                )
                note = st.text_area(
                    "Review note",
                    value=user.get("review_note") or "",
                    key=f"payment_note_{user['user_id']}",
                )
                if st.button(
                    "Save Decision",
                    key=f"payment_save_{user['user_id']}",
                    use_container_width=True,
                ):
                    try:
                        review_payment(
                            user_id=int(user["user_id"]),
                            payment_status=status,
                            reviewer_id=reviewer_id,
                            review_note=note,
                        )
                    except Exception:
                        logger.exception("Payment review update failed")
                        st.error("Payment status could not be updated.")
                    else:
                        st.success(
                            "Payment status updated. User must sign in again "
                            "to refresh access."
                        )
                        st.rerun()


def _render_content_manager() -> None:
    st.subheader("Posts, Announcements, Advisory & Analysis")
    try:
        categories = list_categories(public_only=False)
        items = list_content(public_only=False, limit=200)
    except Exception:
        logger.exception("Admin content manager loading failed")
        st.error("Content manager is temporarily unavailable.")
        return

    options = {"Create new": None}
    options.update(
        {
            f"#{item['id']} · {item['title']}": item
            for item in items
            if item["content_type"] != "PROFIT_SCREENSHOT"
        }
    )
    selection = st.selectbox("Select content", list(options))
    selected = options[selection]
    category_options = {"Uncategorized": None}
    category_options.update(
        {category["title"]: category["id"] for category in categories}
    )
    selected_category = (
        next(
            (
                name
                for name, category_id in category_options.items()
                if selected and category_id == selected.get("category_id")
            ),
            "Uncategorized",
        )
    )

    with st.form("content_editor"):
        content_type = st.selectbox(
            "Content type",
            CONTENT_TYPES[:-1],
            index=(
                CONTENT_TYPES[:-1].index(selected["content_type"])
                if selected and selected["content_type"] in CONTENT_TYPES[:-1]
                else 0
            ),
        )
        title = st.text_input("Title", value=selected["title"] if selected else "")
        excerpt = st.text_area(
            "Short excerpt",
            value=(selected.get("excerpt") or "") if selected else "",
        )
        body = st.text_area(
            "Content",
            value=(selected.get("body") or "") if selected else "",
            height=220,
        )
        category_name = st.selectbox(
            "Category",
            list(category_options),
            index=list(category_options).index(selected_category),
        )
        image_url = st.text_input(
            "Image URL",
            value=(selected.get("image_url") or "") if selected else "",
        )
        external_url = st.text_input(
            "External resource URL",
            value=(selected.get("external_url") or "") if selected else "",
        )
        col1, col2 = st.columns(2)
        is_public = col1.checkbox(
            "Visible publicly",
            value=bool(selected["is_public"]) if selected else True,
        )
        is_published = col2.checkbox(
            "Published",
            value=bool(selected["is_published"]) if selected else False,
        )
        submitted = st.form_submit_button(
            "Save Content",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        admin_id = get_current_user_id()
        if admin_id is None:
            st.error("Administrator session is invalid.")
            return
        try:
            save_content(
                content_id=int(selected["id"]) if selected else None,
                content_type=content_type,
                title=title,
                excerpt=excerpt,
                body=body,
                category_id=category_options[category_name],
                image_url=image_url,
                external_url=external_url,
                is_public=is_public,
                is_published=is_published,
                created_by=admin_id,
            )
        except Exception as exc:
            logger.exception("Content save failed")
            st.error(str(exc) if isinstance(exc, ValueError) else "Save failed.")
        else:
            st.success("Content saved.")
            st.rerun()
    if selected and st.button("Delete Selected Content", type="secondary"):
        try:
            delete_content(int(selected["id"]))
        except Exception:
            logger.exception("Content delete failed")
            st.error("Content could not be deleted.")
        else:
            st.success("Content deleted.")
            st.rerun()


def _render_category_manager() -> None:
    st.subheader("Website Categories")
    try:
        categories = list_categories(public_only=False)
    except Exception:
        logger.exception("Category manager loading failed")
        st.error("Categories are temporarily unavailable.")
        return
    options = {"Create new": None}
    options.update(
        {f"#{item['id']} · {item['title']}": item for item in categories}
    )
    selected = options[st.selectbox("Select category", list(options))]
    with st.form("category_editor"):
        title = st.text_input("Title", value=selected["title"] if selected else "")
        slug = st.text_input("Slug", value=selected["slug"] if selected else "")
        description = st.text_area(
            "Description",
            value=(selected.get("description") or "") if selected else "",
        )
        icon = st.text_input(
            "Icon",
            value=(selected.get("icon") or "") if selected else "",
        )
        order = st.number_input(
            "Display order",
            min_value=0,
            value=int(selected["display_order"]) if selected else 100,
        )
        col1, col2 = st.columns(2)
        is_public = col1.checkbox(
            "Public",
            value=bool(selected["is_public"]) if selected else True,
        )
        is_active = col2.checkbox(
            "Active",
            value=bool(selected["is_active"]) if selected else True,
        )
        submitted = st.form_submit_button(
            "Save Category",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        try:
            save_category(
                category_id=int(selected["id"]) if selected else None,
                title=title,
                slug=slug,
                description=description,
                icon=icon,
                display_order=int(order),
                is_public=is_public,
                is_active=is_active,
            )
        except Exception as exc:
            logger.exception("Category save failed")
            st.error(str(exc) if isinstance(exc, ValueError) else "Save failed.")
        else:
            st.success("Category saved.")
            st.rerun()


def _render_profit_screenshots(supabase: Any) -> None:
    st.subheader("Profit Screenshot Publishing")
    uploaded = st.file_uploader(
        "Upload screenshot",
        type=["png", "jpg", "jpeg", "webp"],
    )
    title = st.text_input("Public caption")
    is_public = st.checkbox("Visible publicly", value=True)
    if st.button(
        "Upload and Publish",
        type="primary",
        use_container_width=True,
        disabled=uploaded is None,
    ):
        admin_id = get_current_user_id()
        if uploaded is None or admin_id is None:
            st.error("Upload and administrator session are required.")
            return
        try:
            image_url = upload_profit_screenshot(
                supabase,
                file_name=uploaded.name,
                file_bytes=uploaded.getvalue(),
            )
            save_content(
                content_type="PROFIT_SCREENSHOT",
                title=title.strip() or "Published Trading Result",
                excerpt="Historical community result. Individual outcomes vary.",
                body="",
                category_id=None,
                image_url=image_url,
                external_url="",
                is_public=is_public,
                is_published=True,
                created_by=admin_id,
            )
        except Exception:
            logger.exception("Profit screenshot publication failed")
            st.error("Screenshot could not be published.")
        else:
            st.success("Profit screenshot published.")
            st.rerun()

    try:
        items = list_content(
            content_type="PROFIT_SCREENSHOT",
            public_only=False,
            limit=50,
        )
    except Exception:
        items = []
    for item in items:
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                if item.get("image_url"):
                    st.image(item["image_url"], width=260)
                st.write(item["title"])
            with right:
                st.caption(
                    "Published" if item["is_published"] else "Draft"
                )
                if st.button("Delete", key=f"delete_proof_{item['id']}"):
                    delete_content(int(item["id"]))
                    st.rerun()


def _render_channel_settings() -> None:
    st.subheader("Protected Invite Links")
    st.caption(
        "These links are loaded server-side and shown only to payment-verified "
        "users. Leave blank to use environment-configured fallback values."
    )
    admin_id = get_current_user_id()
    if admin_id is None:
        st.error("Administrator session is invalid.")
        return
    try:
        telegram = get_site_setting("telegram_invite_url")
        whatsapp = get_site_setting("whatsapp_invite_url")
        proof = get_site_setting("profit_proof_telegram_url")
    except Exception:
        logger.exception("Protected setting loading failed")
        telegram = whatsapp = proof = ""
    with st.form("channel_settings"):
        telegram_value = st.text_input(
            "Private Telegram invite URL",
            value=telegram,
            type="password",
        )
        whatsapp_value = st.text_input(
            "Private WhatsApp invite URL",
            value=whatsapp,
            type="password",
        )
        proof_value = st.text_input(
            "Public profit-proof Telegram URL",
            value=proof,
        )
        submitted = st.form_submit_button(
            "Save Protected Links",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        try:
            save_site_setting(
                "telegram_invite_url",
                telegram_value,
                admin_id,
            )
            save_site_setting(
                "whatsapp_invite_url",
                whatsapp_value,
                admin_id,
            )
            save_site_setting(
                "profit_proof_telegram_url",
                proof_value,
                admin_id,
            )
        except Exception:
            logger.exception("Protected channel setting save failed")
            st.error("Links could not be saved.")
        else:
            st.success("Protected links updated.")


def _render_signal_form() -> None:
    st.subheader("Publish XAUUSD Signal")
    with st.form("admin_signal_form"):
        left, right = st.columns(2)
        with left:
            side = st.radio("Direction", ["BUY", "SELL"], horizontal=True)
            entry = st.text_input("Entry price or zone")
            stop_loss = st.text_input("Stop loss")
        with right:
            tp1 = st.text_input("Take profit 1")
            tp2 = st.text_input("Take profit 2")
            confidence = st.selectbox(
                "Confidence",
                ["Standard", "High", "Very High"],
            )
        note = st.text_area("Risk note or execution instruction")
        submitted = st.form_submit_button(
            "Publish to Verified Users",
            type="primary",
            use_container_width=True,
        )
    if not submitted:
        return
    if not all((entry.strip(), stop_loss.strip(), tp1.strip())):
        st.warning("Entry, stop loss, and take profit 1 are required.")
        return
    payload = {
        "side": side,
        "entry": entry.strip(),
        "stop_loss": stop_loss.strip(),
        "tp1": tp1.strip(),
        "tp2": tp2.strip() or "—",
        "confidence": confidence,
        "note": note.strip()
        or "Apply appropriate position sizing and risk controls.",
    }
    try:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    INSERT INTO public.signals (message, sender)
                    VALUES (:message, :sender)
                    """
                ),
                {
                    "message": "XAU_SIGNAL_V1:" + json.dumps(payload),
                    "sender": "Admin",
                },
            )
    except Exception:
        logger.exception("Signal publication failed")
        st.error("Signal could not be published.")
        return
    st.success(f"{side} signal published successfully.")


def _render_pipeline_health() -> None:
    st.subheader("Backend Pipeline Health")
    try:
        with session_scope() as session:
            summary = (
                session.execute(
                    text(
                        """
                        SELECT COUNT(*) AS total,
                               COUNT(*) FILTER (
                                   WHERE telegram_sent_at IS NULL
                                     AND signal_type IN ('BUY', 'SELL')
                               ) AS pending,
                               COUNT(*) FILTER (
                                   WHERE delivery_error IS NOT NULL
                               ) AS errors,
                               MAX(updated_at) AS last_update
                        FROM public.market_signals
                        """
                    )
                )
                .mappings()
                .one()
            )
    except Exception:
        logger.exception("Pipeline health query failed")
        st.error("Pipeline health is temporarily unavailable.")
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Market Signals", summary["total"])
    col2.metric("Pending Telegram", summary["pending"])
    col3.metric("Delivery Errors", summary["errors"])
    st.caption(f"Last database update: {summary['last_update'] or 'No data'}")
    st.info(
        "Only operational status is displayed. Agent prompts and internal "
        "processing logic remain private."
    )


def _render_ai_agents(supabase: Any) -> None:
    """Render the protected AI-agent control surface for administrators."""
    if get_current_role() != ROLE_ADMIN:
        st.error("Administrator access is required.")
        st.stop()

    st.subheader("AI Agents")
    st.caption(
        "Operational controls only. Prompts, credentials, and internal "
        "reasoning are never displayed."
    )
    try:
        agents = list_ai_agents()
    except Exception:
        logger.exception("AI agent list failed")
        st.error("AI agent controls are temporarily unavailable.")
        return

    admin_id = get_current_user_id()
    if admin_id is None:
        st.error("Administrator session is invalid.")
        return

    columns = st.columns(2)
    for index, agent in enumerate(agents):
        with columns[index % 2]:
            with st.container(border=True):
                st.markdown(f"### {agent['display_name']}")
                status = str(agent["status"])
                status_icon = {
                    "IDLE": "⚪",
                    "RUNNING": "🟡",
                    "ERROR": "🔴",
                }.get(status, "⚪")
                st.write(f"**Status:** {status_icon} {status.title()}")
                st.caption(
                    f"Last run: {agent['last_run_at'] or 'Never'}"
                )
                st.caption(
                    f"Last error: {agent['last_error'] or 'None'}"
                )

                enabled = st.toggle(
                    "Enabled",
                    value=bool(agent["is_enabled"]),
                    key=f"agent_enabled_{agent['agent_key']}",
                )
                if enabled != bool(agent["is_enabled"]):
                    try:
                        set_ai_agent_enabled(
                            str(agent["agent_key"]),
                            enabled,
                        )
                    except Exception:
                        logger.exception(
                            "AI agent toggle failed: {}",
                            agent["agent_key"],
                        )
                        st.error("Agent setting could not be updated.")
                    else:
                        st.rerun()

                if st.button(
                    "Manual Run",
                    key=f"agent_run_{agent['agent_key']}",
                    use_container_width=True,
                    disabled=not enabled or status == "RUNNING",
                ):
                    succeeded, message = run_ai_agent(
                        agent_key=str(agent["agent_key"]),
                        triggered_by=admin_id,
                        supabase=supabase,
                    )
                    (st.success if succeeded else st.error)(message)
                    st.rerun()


def _render_telegram_test(supabase: Any) -> None:
    st.subheader("Test Automated Telegram Signal")
    with st.form("telegram_connectivity_test"):
        use_sheet = st.checkbox(
            "Use latest Google Sheet BUY/SELL row",
            value=True,
        )
        direction = st.radio(
            "Fallback direction",
            ["BUY", "SELL"],
            horizontal=True,
        )
        target = st.text_input("Fallback target price")
        stop_loss = st.text_input("Fallback stop loss")
        submitted = st.form_submit_button(
            "Send Test Telegram Signal",
            type="primary",
            use_container_width=True,
        )
    if not submitted:
        return
    try:
        target_value = _optional_decimal(target)
        stop_value = _optional_decimal(stop_loss)
    except ValueError as exc:
        st.warning(str(exc))
        return
    delivered, message = trigger_test_signal(
        supabase=supabase,
        direction=direction,
        target_price=target_value,
        stop_loss=stop_value,
        use_google_sheet=use_sheet,
    )
    (st.success if delivered else st.error)(message)


def trigger_test_signal(
    supabase: Any,
    direction: str = "BUY",
    target_price: Decimal | None = None,
    stop_loss: Decimal | None = None,
    use_google_sheet: bool = True,
) -> tuple[bool, str]:
    """Send a real TEST SIGNAL using current credentials and services."""
    normalized_direction = direction.strip().upper()
    if normalized_direction not in {"BUY", "SELL"}:
        return False, "Test direction must be BUY or SELL."
    label = "TEST SIGNAL · Admin connectivity check"
    if use_google_sheet:
        try:
            sheet_signal = GoogleSheetsService().get_latest_signal()
        except Exception:
            logger.exception("Google Sheet test enrichment failed")
            sheet_signal = None
        if sheet_signal:
            normalized_direction = sheet_signal.direction
            target_price = sheet_signal.target_price or target_price
            stop_loss = sheet_signal.stop_loss or stop_loss
            label = f"TEST SIGNAL · {sheet_signal.label}"
    try:
        market_price = MarketDataService(supabase).fetch_current_price()
        if market_price is None:
            return False, "Current XAUUSD price could not be fetched."
        delivered = TelegramService(supabase).send_test_signal(
            {
                "signal_type": normalized_direction,
                "price": float(market_price.price),
                "target_price": (
                    float(target_price)
                    if target_price is not None
                    else None
                ),
                "stop_loss": (
                    float(stop_loss) if stop_loss is not None else None
                ),
                "sheet_label": label,
                "source": market_price.source,
                "signal_time": market_price.observed_at.isoformat(),
            }
        )
    except Exception:
        logger.exception("Admin Telegram connectivity test failed")
        return False, "Telegram test failed. Check credentials and logs."
    return (
        (True, "TEST SIGNAL delivered to Telegram successfully.")
        if delivered
        else (False, "Telegram rejected the test signal.")
    )


def _optional_decimal(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Target and stop loss must be numeric.") from exc
