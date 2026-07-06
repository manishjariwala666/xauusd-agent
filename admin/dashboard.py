"""Separate role-protected website and signal administration console."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
import re
from typing import Any

from loguru import logger
import streamlit as st
from sqlalchemy import text

from core.auth import ROLE_ADMIN, get_current_role, get_current_user_id
from core.database import session_scope
from services.ai_agent_service import (
    list_ai_agents,
    list_agent_runs,
    run_ai_agent,
    set_ai_agent_enabled,
)
from services.conversation_service import (
    list_conversations,
    send_human_reply,
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
import os
import re
from urllib.parse import quote


def render_admin_dashboard(supabase: Any) -> None:
    """Render admin-only controls without exposing them to user sessions."""
    if get_current_role() != ROLE_ADMIN:
        st.error("Administrator access is required.")
        st.stop()

    st.markdown("## Administration Console")
    (
        command_center_tab,
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
            "Command Center",
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
    with command_center_tab:
        _render_command_center(supabase)
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



def _admin_public_site_url() -> str:
    return (
        os.getenv("PUBLIC_SITE_URL")
        or os.getenv("STREAMLIT_PUBLIC_URL")
        or "https://xauusd-buy-sell-signal.streamlit.app"
    ).rstrip("/")


def _agent_by_key(agents: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    return next((agent for agent in agents if agent.get("agent_key") == key), None)


def _status_badge(value: str | None) -> str:
    normalized = str(value or "unknown").upper()
    if normalized in {"IDLE", "SUCCESS", "COMPLETED", "OK"}:
        return f"✅ {normalized}"
    if normalized in {"RUNNING", "QUEUED", "PROCESSING"}:
        return f"🟡 {normalized}"
    if normalized in {"ERROR", "FAILED", "FAILURE"}:
        return f"🔴 {normalized}"
    return f"⚪ {normalized}"


def _latest_run_summary(runs: list[dict[str, Any]], agent_name: str) -> dict[str, Any] | None:
    wanted = agent_name.lower().replace("_", " ")
    for run in runs:
        name = str(run.get("display_name") or run.get("agent_key") or "").lower().replace("_", " ")
        if wanted in name or name in wanted:
            return run
    return None


def _render_command_center(supabase: Any) -> None:
    """Owner-focused admin dashboard for daily operations."""
    st.subheader("Command Center")
    st.caption(
        "Daily owner controls: Master AI, blogs, sheet sync, signals, and public website checks."
    )

    try:
        agents = list_ai_agents()
        runs = list_agent_runs(limit=12)
        latest_blogs = list_content(content_type="AI_BLOG", public_only=False, limit=6)
    except Exception:
        logger.exception("Command center loading failed")
        st.error("Command center could not load system status.")
        return

    blog_agent = _agent_by_key(agents, "ai_blog_agent")
    signal_agent = _agent_by_key(agents, "signal_agent")
    telegram_agent = _agent_by_key(agents, "telegram_reply_agent")
    whatsapp_agent = _agent_by_key(agents, "whatsapp_reply_agent")

    latest_blog = latest_blogs[0] if latest_blogs else None
    latest_blog_status = "No blog"
    if latest_blog:
        latest_blog_status = (
            "Published"
            if latest_blog.get("is_published") and latest_blog.get("is_public")
            else "Draft / Hidden"
        )

    card_cols = st.columns(4)
    card_cols[0].metric(
        "Master AI Blog",
        _status_badge(blog_agent.get("status") if blog_agent else "missing"),
        f"{blog_agent.get('success_count', 0) if blog_agent else 0} success",
    )
    card_cols[1].metric(
        "Signal Agent",
        _status_badge(signal_agent.get("status") if signal_agent else "missing"),
        f"{signal_agent.get('success_count', 0) if signal_agent else 0} success",
    )
    card_cols[2].metric(
        "Telegram / WhatsApp",
        (
            "✅ Ready"
            if telegram_agent and whatsapp_agent
            else "⚠️ Check setup"
        ),
        "reply agents",
    )
    card_cols[3].metric(
        "Latest Blog",
        latest_blog_status,
        f"#{latest_blog.get('id')}" if latest_blog else "",
    )

    st.divider()

    left, right = st.columns([1.1, 0.9])

    with left:
        st.markdown("### Quick Actions")

        blog_topic = st.text_input(
            "Blog topic",
            value="XAUUSD market structure, risk control, and today market levels",
            key="command_center_blog_topic",
        )
        publish_now = st.checkbox(
            "Publish blog immediately",
            value=True,
            key="command_center_blog_publish",
        )

        action_cols = st.columns(2)

        if action_cols[0].button(
            "Run Blog Now",
            type="primary",
            use_container_width=True,
            key="command_center_run_blog",
        ):
            admin_id = get_current_user_id()
            if admin_id is None:
                st.error("Administrator session is invalid.")
            elif not blog_topic.strip():
                st.warning("Enter a blog topic first.")
            else:
                with st.spinner("Running Blog Agent..."):
                    succeeded, message = run_ai_agent(
                        "ai_blog_agent",
                        triggered_by=admin_id,
                        supabase=supabase,
                        payload={
                            "topic": blog_topic.strip(),
                            "publish": publish_now,
                        },
                    )
                if succeeded:
                    st.success(message)
                else:
                    st.error(message)

        if action_cols[1].button(
            "Sync Sheet Targets",
            use_container_width=True,
            key="command_center_sync_sheet",
        ):
            try:
                from services.xauusd_sheet_signals import append_latest_targets_to_signals

                with st.spinner("Reading Sheet1 and writing Signals tab..."):
                    result = append_latest_targets_to_signals()
            except ModuleNotFoundError:
                st.warning(
                    "Sheet target sync module is not installed yet. "
                    "Next step: add services/xauusd_sheet_signals.py."
                )
            except Exception as exc:
                logger.exception("Command center sheet sync failed")
                st.error(f"Sheet sync failed: {exc}")
            else:
                st.success(
                    f"Sheet sync completed: {result.get('appended', 0)} targets copied. "
                    f"Day High: {result.get('day_high', '')} · "
                    f"Day Low: {result.get('day_low', '')}"
                )

        more_cols = st.columns(2)
        more_cols[0].link_button(
            "Open Public Website",
            _admin_public_site_url(),
            use_container_width=True,
        )
        more_cols[1].link_button(
            "Open Latest Blog",
            (
                _content_public_url(latest_blog)
                if latest_blog
                else _admin_public_site_url()
            ),
            use_container_width=True,
        )

    with right:
        st.markdown("### Today Signal Preview")

        if st.button(
            "Preview Latest Sheet Targets",
            use_container_width=True,
            key="command_center_preview_sheet",
        ):
            try:
                from services.xauusd_sheet_signals import read_latest_target_block

                block = read_latest_target_block()
            except ModuleNotFoundError:
                st.info("Signal preview module will be added in the Sheet sync step.")
            except Exception as exc:
                logger.exception("Command center signal preview failed")
                st.error(f"Could not preview Sheet targets: {exc}")
            else:
                summary = block.get("summary", {})
                st.write(
                    {
                        "date": block.get("date"),
                        "day_high": summary.get("Day High"),
                        "day_low": summary.get("Day Low"),
                        "buy_base": summary.get("Buy Base"),
                        "sell_base": summary.get("Sell Base"),
                        "mode": summary.get("Mode"),
                    }
                )
                st.dataframe(block.get("targets", []), use_container_width=True)

        st.markdown("### Latest Blog")
        if latest_blog:
            st.write(f"**{latest_blog.get('title')}**")
            st.caption(
                f"Status: {latest_blog_status} · "
                f"Created: {latest_blog.get('created_at') or '-'}"
            )
            if latest_blog.get("image_url"):
                st.image(str(latest_blog["image_url"]), use_container_width=True)
            else:
                st.info("No image_url. Public page uses fallback banner.")
        else:
            st.info("No blog content found yet.")

    st.divider()
    st.markdown("### Recent Activity")

    activity: list[dict[str, Any]] = []
    for run in runs[:8]:
        activity.append(
            {
                "Run": f"#{run.get('id')}",
                "Agent": run.get("display_name") or run.get("agent_key"),
                "Status": run.get("status"),
                "Started": run.get("started_at"),
                "Summary": run.get("result") or run.get("error") or "",
            }
        )

    if activity:
        st.dataframe(activity, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity found.")


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



def _content_public_url(item: dict[str, Any]) -> str:
    """Build public Streamlit article URL for a content row."""
    slug = str(
        item.get("seo_slug")
        or item.get("slug")
        or item.get("id")
        or ""
    ).strip()
    if not slug:
        return ""

    base_url = (
        os.getenv("PUBLIC_SITE_URL")
        or os.getenv("STREAMLIT_PUBLIC_URL")
        or "https://xauusd-buy-sell-signal.streamlit.app"
    ).rstrip("/")

    return f"{base_url}/?post={quote(slug)}"


def _content_duplicate_key(item: dict[str, Any]) -> str:
    """Group duplicates by content type + normalized title."""
    content_type = str(item.get("content_type") or "").strip()
    title = str(item.get("title") or "").strip().lower()
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    return f"{content_type}:{title or item.get('id')}"


def _duplicate_content_groups(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if item.get("content_type") == "PROFIT_SCREENSHOT":
            continue
        key = _content_duplicate_key(item)
        groups.setdefault(key, []).append(item)

    duplicate_groups = [group for group in groups.values() if len(group) > 1]
    for group in duplicate_groups:
        group.sort(
            key=lambda row: str(row.get("published_at") or row.get("created_at") or ""),
            reverse=True,
        )
    duplicate_groups.sort(key=lambda group: len(group), reverse=True)
    return duplicate_groups


def _update_content_publish_state(
    item: dict[str, Any],
    *,
    is_public: bool,
    is_published: bool,
) -> None:
    admin_id = get_current_user_id()
    if admin_id is None:
        st.error("Administrator session is invalid.")
        return

    save_content(
        content_id=int(item["id"]),
        content_type=str(item["content_type"]),
        title=str(item["title"]),
        excerpt=str(item.get("excerpt") or ""),
        body=str(item.get("body") or ""),
        category_id=item.get("category_id"),
        image_url=str(item.get("image_url") or ""),
        external_url=str(item.get("external_url") or ""),
        is_public=is_public,
        is_published=is_published,
        created_by=admin_id,
    )


def _render_content_manager() -> None:
    st.subheader("Posts, Announcements, Advisory & Analysis")
    try:
        categories = list_categories(public_only=False)
        items = list_content(public_only=False, limit=200)
    except Exception:
        logger.exception("Admin content manager loading failed")
        st.error("Content manager is temporarily unavailable.")
        return

    duplicate_groups = _duplicate_content_groups(items)
    if duplicate_groups:
        total_duplicates = sum(len(group) - 1 for group in duplicate_groups)
        st.warning(
            f"{total_duplicates} duplicate content records found. "
            "Public page now hides duplicate cards, but you can unpublish old records here."
        )
        with st.expander("Review duplicate records", expanded=False):
            for group in duplicate_groups[:12]:
                latest = group[0]
                st.markdown(f"**{latest.get('title', 'Untitled')}**")
                for record in group:
                    status = "Published" if record.get("is_published") else "Draft"
                    visibility = "Public" if record.get("is_public") else "Private"
                    st.write(
                        f"#{record['id']} · {record.get('content_type')} · "
                        f"{status} · {visibility} · "
                        f"{record.get('published_at') or record.get('created_at') or ''}"
                    )

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

    if selected:
        st.markdown("#### Selected content tools")
        tool_cols = st.columns(3)

        public_url = _content_public_url(selected)
        if public_url:
            tool_cols[0].link_button(
                "Open Public Article",
                public_url,
                use_container_width=True,
            )

        if selected.get("is_published"):
            if tool_cols[1].button(
                "Quick Unpublish",
                key=f"quick_unpublish_{selected['id']}",
                use_container_width=True,
            ):
                try:
                    _update_content_publish_state(
                        selected,
                        is_public=bool(selected.get("is_public")),
                        is_published=False,
                    )
                except Exception:
                    logger.exception("Quick unpublish failed")
                    st.error("Could not unpublish content.")
                else:
                    st.success("Content unpublished.")
                    st.rerun()
        else:
            if tool_cols[1].button(
                "Quick Publish",
                key=f"quick_publish_{selected['id']}",
                use_container_width=True,
            ):
                try:
                    _update_content_publish_state(
                        selected,
                        is_public=True,
                        is_published=True,
                    )
                except Exception:
                    logger.exception("Quick publish failed")
                    st.error("Could not publish content.")
                else:
                    st.success("Content published.")
                    st.rerun()

        if tool_cols[2].button(
            "Refresh Content List",
            key=f"refresh_content_{selected['id']}",
            use_container_width=True,
        ):
            st.rerun()

        if selected.get("image_url"):
            st.caption("Image preview")
            st.image(str(selected["image_url"]), width=320)
        elif selected.get("content_type") == "AI_BLOG":
            st.info(
                "This AI blog has no image_url. Public page will show the fallback "
                "XAUUSD research banner."
            )
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
        conversations = list_conversations()
    except Exception:
        logger.exception("AI agent list failed")
        st.error("AI agent controls are temporarily unavailable.")
        return

    admin_id = get_current_user_id()
    if admin_id is None:
        st.error("Administrator session is invalid.")
        return

    failed_agents = [
        agent for agent in agents if agent.get("last_error")
    ]
    if failed_agents:
        with st.expander(
            f"Operational Error Summary ({len(failed_agents)})",
            expanded=False,
        ):
            for failed_agent in failed_agents:
                st.warning(
                    f"{failed_agent['display_name']}: "
                    f"{_safe_admin_error(failed_agent['last_error'])}"
                )

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
                    "Next scheduled run: "
                    f"{agent['next_scheduled_run_at'] or 'Not scheduled'}"
                )
                duration = agent.get("last_duration_ms")
                st.caption(
                    "Processing time: "
                    f"{int(duration) / 1000:.2f}s"
                    if duration is not None
                    else "Processing time: —"
                )
                metric1, metric2, metric3 = st.columns(3)
                metric1.metric("Success", int(agent["success_count"] or 0))
                metric2.metric("Failure", int(agent["failure_count"] or 0))
                metric3.metric("Queue", int(agent["queue_size"] or 0))
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

                agent_key = str(agent["agent_key"])
                payload = _agent_manual_payload(agent_key, conversations)
                validation_error = _validate_manual_payload(agent_key, payload)
                if validation_error:
                    st.warning(validation_error)

                if st.button(
                    "Manual Run",
                    key=f"agent_run_{agent['agent_key']}",
                    use_container_width=True,
                    disabled=(
                        not enabled
                        or status == "RUNNING"
                        or validation_error is not None
                    ),
                ):
                    succeeded, message = run_ai_agent(
                        agent_key=agent_key,
                        triggered_by=admin_id,
                        supabase=supabase,
                        payload=payload,
                    )
                    (st.success if succeeded else st.error)(message)
                    st.rerun()

    st.divider()
    st.markdown("### Execution Logs")
    try:
        runs = list_agent_runs()
    except Exception:
        logger.exception("AI execution history failed")
        st.error("Execution history is temporarily unavailable.")
    else:
        if runs:
            _render_agent_execution_logs(runs)
        else:
            st.info("No AI agent executions have been recorded.")

    with st.expander("Conversation & Human Takeover"):
        if not conversations:
            st.info("No Telegram or WhatsApp conversations yet.")
        else:
            options = {
                (
                    f"#{item['id']} · {item['channel']} · "
                    f"{item['external_user_id']}"
                ): item
                for item in conversations
            }
            selected_label = st.selectbox(
                "Conversation",
                list(options),
                key="human_takeover_conversation",
            )
            selected = options[selected_label]
            st.caption(selected.get("last_message") or "No message text")
            reply = st.text_area(
                "Admin reply",
                key="human_takeover_reply",
            )
            if st.button(
                "Send as Admin and Pause AI",
                type="primary",
                key="human_takeover_send",
            ):
                try:
                    send_human_reply(
                        int(selected["id"]),
                        admin_id,
                        reply,
                    )
                except Exception:
                    logger.exception("Human takeover reply failed")
                    st.error("Admin reply could not be delivered.")
                else:
                    st.success(
                        "Reply delivered. AI is paused for this conversation."
                    )
                    st.rerun()


def _validate_manual_payload(
    agent_key: str,
    payload: dict[str, Any],
) -> str | None:
    """Return safe user-facing validation errors before manual execution."""
    if agent_key in {"telegram_reply_agent", "whatsapp_reply_agent"}:
        if not payload.get("conversation_id"):
            return "Select a conversation before running this reply agent."
    if agent_key == "image_agent":
        if not (payload.get("prompt") or payload.get("content_id")):
            return "Enter an image brief or select content before running Image Agent."
    if agent_key == "ai_blog_agent":
        if not payload.get("topic"):
            return "Enter a blog topic before running Blog Agent."
    if agent_key == "announcement_agent":
        if not payload.get("message"):
            return "Enter a broadcast message before running Announcement Agent."
    return None


def _safe_text(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    text_value = str(value)
    secret_markers = (
        "key",
        "token",
        "secret",
        "password",
        "authorization",
        "private",
        "credential",
    )
    lowered = text_value.lower()
    if any(marker in lowered for marker in secret_markers):
        return "[redacted]"
    return text_value


def _render_agent_execution_logs(runs: list[dict[str, Any]]) -> None:
    """Render execution history with expandable safe details."""
    summary_rows = []
    for run in runs:
        summary_rows.append(
            {
                "ID": run.get("id"),
                "Agent": run.get("display_name"),
                "Status": run.get("status"),
                "Trigger": run.get("trigger_type"),
                "Started": run.get("started_at"),
                "Duration ms": run.get("duration_ms"),
                "Summary": _safe_text(run.get("result_summary")),
                "Error": _safe_text(run.get("error_message")),
            }
        )

    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    latest_ten = runs[:10]
    st.markdown("#### Latest 10 Execution Details")
    for run in latest_ten:
        title = (
            f"#{run.get('id')} · {run.get('display_name')} · "
            f"{run.get('status')} · {run.get('started_at')}"
        )
        with st.expander(title):
            col1, col2, col3 = st.columns(3)
            col1.metric("Status", _safe_text(run.get("status")))
            col2.metric("Trigger", _safe_text(run.get("trigger_type")))
            duration = run.get("duration_ms")
            col3.metric(
                "Duration",
                f"{int(duration) / 1000:.2f}s"
                if duration is not None
                else "—",
            )
            st.write("**Started:**", _safe_text(run.get("started_at")))
            st.write("**Finished:**", _safe_text(run.get("finished_at")))
            st.write("**Output summary:**")
            st.info(_safe_text(run.get("result_summary"), "No output summary stored."))
            if run.get("error_message"):
                st.write("**Safe error:**")
                st.error(_safe_text(run.get("error_message")))


def _agent_manual_payload(
    agent_key: str,
    conversations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Collect task input without displaying prompts or internal reasoning."""
    if agent_key == "ai_blog_agent":
        return {
            "topic": st.text_input(
                "Blog topic",
                key="manual_blog_topic",
            ),
            "publish": st.checkbox(
                "Publish immediately",
                value=False,
                key="manual_blog_publish",
            ),
        }
    if agent_key == "announcement_agent":
        return {
            "message": st.text_area(
                "Broadcast message",
                key="manual_announcement_message",
            ),
            "send_telegram": st.checkbox(
                "Telegram",
                value=True,
                key="manual_announcement_telegram",
            ),
            "send_whatsapp": st.checkbox(
                "WhatsApp",
                value=True,
                key="manual_announcement_whatsapp",
            ),
        }
    if agent_key == "image_agent":
        return {
            "prompt": st.text_area(
                "Image brief",
                key="manual_image_prompt",
            )
        }
    if agent_key in {"telegram_reply_agent", "whatsapp_reply_agent"}:
        channel = (
            "TELEGRAM"
            if agent_key == "telegram_reply_agent"
            else "WHATSAPP"
        )
        available = [
            item for item in conversations if item["channel"] == channel
        ]
        labels = {
            f"#{item['id']} · {item['external_user_id']}": item["id"]
            for item in available
        }
        selected = st.selectbox(
            "Conversation",
            ["No conversation", *labels],
            key=f"manual_conversation_{agent_key}",
        )
        return {
            "conversation_id": labels.get(selected),
        }
    return {}


def _safe_admin_error(value: Any) -> str:
    """Hide paths, URLs, and secret-like values in dashboard summaries."""
    message = str(value).splitlines()[0].strip()
    message = re.sub(r"https?://\S+", "[redacted-url]", message)
    message = re.sub(
        r"(?:[A-Za-z]:)?[/\\][\w./\\-]+",
        "[redacted-path]",
        message,
    )
    message = re.sub(
        r"(?i)(token|secret|password|api[_ -]?key)\s*[=:]\s*\S+",
        r"\1=[redacted]",
        message,
    )
    return message[:500] or "Internal operation failed."


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
