"""Separate role-protected website and signal administration console."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
import re
from typing import Any

from loguru import logger
import streamlit as st
from sqlalchemy import text

from components.theme import apply_admin_light_theme
from core.auth import ROLE_ADMIN, get_current_role, get_current_user_id
from core.database import session_scope
from services.ai_agent_service import (
    AI_AGENT_CONTROL_NUMBERS,
    list_ai_agents,
    list_agent_runs,
    run_ai_agent,
    set_ai_agent_enabled_by_number,
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
from services.google_sheets_service import (
    PrivateGoogleSheetsService,
    GoogleSheetsServiceError,
    google_sheets_disabled_reason,
    is_google_sheets_configured,
)
from services.market_data import MarketDataService
from services.telegram_service import TelegramService
from user.dashboard import render_signal_feed
import os
from urllib.parse import quote


def render_admin_dashboard(supabase: Any) -> None:
    """Render admin-only controls without exposing them to user sessions."""
    if get_current_role() != ROLE_ADMIN:
        st.error("Administrator access is required.")
        st.stop()

    apply_admin_light_theme()
    _render_admin_light_sidebar()
    _render_admin_topbar()
    _render_admin_shell_header()
    _render_admin_light_kpis()
    (
        command_center_tab,
        overview_tab,
        payments_tab,
        content_tab,
        categories_tab,
        proof_tab,
        channels_tab,
        signals_tab,
        users_tab,
        logs_tab,
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
            "Users / Leads",
            "Logs",
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
        _render_signal_form(supabase)
        st.divider()
        render_signal_feed(supabase, "No signal has been published.")
    with users_tab:
        _render_user_lead_manager()
    with logs_tab:
        _render_operations_logs()
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


def _render_admin_light_sidebar() -> None:
    """Add a clean Able-Pro-style admin navigation map to the sidebar."""
    st.sidebar.markdown(
        """
        <div class="admin-sidebar-brand">AI Market <small>pro</small></div>
        <div class="admin-sidebar-section">Dashboard</div>
        <div class="admin-sidebar-item active">🏠 Command Center</div>
        <div class="admin-sidebar-item">📊 Analytics Overview</div>
        <div class="admin-sidebar-section">Operations</div>
        <div class="admin-sidebar-item">✍️ Content Manager</div>
        <div class="admin-sidebar-item">📡 Signal Manager</div>
        <div class="admin-sidebar-item">🤖 AI Agents</div>
        <div class="admin-sidebar-section">Channels</div>
        <div class="admin-sidebar-item">💬 Telegram</div>
        <div class="admin-sidebar-item">🟢 WhatsApp</div>
        <div class="admin-sidebar-item">📗 Google Sheet</div>
        """,
        unsafe_allow_html=True,
    )


def _render_admin_topbar() -> None:
    """Render the visual top navigation expected from a SaaS admin panel."""
    st.markdown(
        """
        <section class="admin-topbar">
            <div class="admin-menu-button">☰</div>
            <div class="admin-search-pill">🔎 <span>Ctrl + K · Search commands, blogs, signals</span></div>
            <div></div>
            <div class="admin-topbar-actions">
                <div class="admin-icon-button">▣</div>
                <div class="admin-icon-button">⚙</div>
                <div class="admin-icon-button">🔔</div>
                <div class="admin-avatar">AI</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_admin_shell_header() -> None:
    """Render an Able-Pro-inspired admin command-room header."""
    st.markdown(
        """
        <section class="admin-hero">
            <div>
                <div class="eyebrow">ADMIN CONTROL ROOM · MASTER AI OPS</div>
                <h1>AI Market Analytics Pro</h1>
                <p>
                    Manage content, XAUUSD signals, users, Google Sheet logs,
                    Telegram broadcasts, WhatsApp replies, and production AI
                    agents from one secure dashboard.
                </p>
                <div class="admin-chip-row">
                    <span>Master AI Brain</span>
                    <span>Public Signal Broadcast</span>
                    <span>Sheet Log Book</span>
                    <span>Website CMS</span>
                </div>
            </div>
            <div class="admin-hero-orb">🚀</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_admin_light_kpis() -> None:
    """Show first-glance admin health cards without changing core queries."""
    kpis = {
        "blogs": "—",
        "signals": "—",
        "users": "—",
        "errors": "—",
    }
    try:
        with session_scope() as session:
            rows = (
                session.execute(
                    text(
                        """
                        SELECT
                            (
                                SELECT COUNT(*)
                                FROM public.content_items
                                WHERE content_type IN ('BLOG', 'AI_BLOG')
                            ) AS blogs,
                            (
                                SELECT COUNT(*)
                                FROM public.market_signals
                            ) AS signals,
                            (
                                SELECT COUNT(*)
                                FROM public.users
                            ) AS users,
                            (
                                SELECT COUNT(*)
                                FROM public.master_ai_events
                                WHERE severity IN ('ERROR', 'CRITICAL')
                            ) AS errors
                        """
                    )
                )
                .mappings()
                .one()
            )
            kpis = {key: str(int(rows[key] or 0)) for key in kpis}
    except Exception:
        logger.debug("Able Pro admin KPI cards are using safe fallback values.")

    st.markdown(
        f"""
        <section class="admin-light-kpi-grid">
            <div class="admin-light-kpi">
                <div>
                    <div class="value">{kpis["blogs"]}</div>
                    <div class="label">Total Blogs</div>
                    <div class="trend">↗ CMS ready</div>
                </div>
                <div class="admin-kpi-icon">✍️</div>
            </div>
            <div class="admin-light-kpi">
                <div>
                    <div class="value">{kpis["signals"]}</div>
                    <div class="label">XAUUSD Signals</div>
                    <div class="trend">↗ broadcast stack</div>
                </div>
                <div class="admin-kpi-icon">📡</div>
            </div>
            <div class="admin-light-kpi">
                <div>
                    <div class="value">{kpis["users"]}</div>
                    <div class="label">Users / Leads</div>
                    <div class="trend">↗ CRM view</div>
                </div>
                <div class="admin-kpi-icon">👥</div>
            </div>
            <div class="admin-light-kpi">
                <div>
                    <div class="value">{kpis["errors"]}</div>
                    <div class="label">System Errors</div>
                    <div class="trend">↗ logs tracked</div>
                </div>
                <div class="admin-kpi-icon">🛡️</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


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

    _render_agent_launchpad_cards(agents)

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


def _render_agent_launchpad_cards(agents: list[dict[str, Any]]) -> None:
    """Show high-level agent controls without revealing prompts/secrets."""
    agent_roles = [
        (
            "ai_blog_agent",
            "Blog Agent",
            "Creates SEO-safe market content.",
            "✍️",
        ),
        (
            "signal_agent",
            "Signal Agent",
            "Processes XAUUSD buy/sell workflows.",
            "📡",
        ),
        (
            "seo_agent",
            "SEO Agent",
            "Reviews metadata, FAQ, and schema.",
            "🔎",
        ),
        (
            "image_agent",
            "Image Agent",
            "Creates optional editorial visuals.",
            "🎨",
        ),
        (
            "telegram_reply_agent",
            "Telegram Agent",
            "Handles Telegram admin/member replies.",
            "💬",
        ),
        (
            "whatsapp_reply_agent",
            "WhatsApp Agent",
            "Keeps WhatsApp limited to signal replies.",
            "📱",
        ),
    ]
    st.markdown("### Agent Launchpad")
    columns = st.columns(3)
    for index, (agent_key, title, description, icon) in enumerate(agent_roles):
        agent = _agent_by_key(agents, agent_key)
        status = _status_badge(agent.get("status") if agent else "missing")
        success_count = int(agent.get("success_count") or 0) if agent else 0
        failure_count = int(agent.get("failure_count") or 0) if agent else 0
        with columns[index % 3]:
            st.markdown(
                f"""
                <div class="admin-agent-card">
                    <div class="admin-agent-icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{description}</p>
                    <div class="admin-agent-status">{status}</div>
                    <div class="admin-agent-meta">
                        <span>{success_count} success</span>
                        <span>{failure_count} failed</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


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
                            ) AS active_categories,
                            (
                                SELECT COUNT(*)
                                FROM public.content_items
                                WHERE content_type IN ('BLOG', 'AI_BLOG')
                            ) AS total_blogs,
                            (
                                SELECT COUNT(*)
                                FROM public.content_items
                                WHERE content_type IN ('BLOG', 'AI_BLOG')
                                  AND is_published = TRUE
                            ) AS published_blogs,
                            (
                                SELECT COUNT(*)
                                FROM public.content_items
                                WHERE content_type IN ('BLOG', 'AI_BLOG')
                                  AND is_published = FALSE
                            ) AS draft_blogs
                        """
                    )
                )
                .mappings()
                .one()
            )
            latest_signals = _query_latest_signals(session)
            latest_master_commands = _query_latest_master_commands(session)
            latest_whatsapp_messages = _query_latest_channel_messages(
                session,
                "WHATSAPP",
            )
            recent_errors = _query_recent_errors(session)
    except Exception:
        logger.exception("Admin overview loading failed")
        st.error("Overview metrics are temporarily unavailable.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registered Users", int(metrics["registered_users"]))
    col2.metric("Payment Reviews", int(metrics["payment_reviews"]))
    col3.metric("Published Content", int(metrics["published_content"]))
    col4.metric("Active Categories", int(metrics["active_categories"]))

    blog_cols = st.columns(3)
    blog_cols[0].metric("Total Blogs", int(metrics["total_blogs"]))
    blog_cols[1].metric("Published Blogs", int(metrics["published_blogs"]))
    blog_cols[2].metric("Draft Blogs", int(metrics["draft_blogs"]))

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("### Latest Signals")
        _render_small_table(
            latest_signals,
            empty_message="No market signals found.",
        )
        st.markdown("### Latest Telegram Master Commands")
        _render_small_table(
            latest_master_commands,
            empty_message="No Telegram Master commands found.",
        )
    with right:
        st.markdown("### Latest WhatsApp Messages")
        _render_small_table(
            latest_whatsapp_messages,
            empty_message="No WhatsApp messages found.",
        )
        st.markdown("### Google Sheet Sync Status")
        _render_google_sheet_sync_status()

    st.markdown("### Recent Errors")
    _render_small_table(
        recent_errors,
        empty_message="No recent system errors found.",
    )
    st.info(
        "AI-generated drafts may be reviewed and published here, but agent "
        "prompts, credentials, and internal reasoning are never displayed."
    )


def _query_latest_signals(session: Any) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            text(
                """
                SELECT signal_type AS type,
                       price,
                       target_price AS target,
                       stop_loss,
                       source,
                       sheet_label,
                       signal_time
                FROM public.market_signals
                ORDER BY signal_time DESC
                LIMIT 6
                """
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def _query_latest_master_commands(session: Any) -> list[dict[str, Any]]:
    if not _table_exists(session, "master_ai_events"):
        return []
    rows = (
        session.execute(
            text(
                """
                SELECT event_type,
                       severity,
                       message,
                       created_at
                FROM public.master_ai_events
                WHERE event_type IN (
                    'TELEGRAM_MASTER_COMMAND',
                    'TELEGRAM_MASTER_WEBHOOK'
                )
                   OR message ILIKE '%telegram%'
                ORDER BY created_at DESC
                LIMIT 6
                """
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def _query_latest_channel_messages(
    session: Any,
    channel: str,
) -> list[dict[str, Any]]:
    if not _table_exists(session, "ai_conversations") or not _table_exists(
        session,
        "ai_messages",
    ):
        return []
    rows = (
        session.execute(
            text(
                """
                SELECT m.sender_type,
                       LEFT(m.body, 180) AS message,
                       c.external_user_id,
                       m.created_at
                FROM public.ai_messages m
                JOIN public.ai_conversations c
                  ON c.id = m.conversation_id
                WHERE c.channel = :channel
                ORDER BY m.created_at DESC
                LIMIT 6
                """
            ),
            {"channel": channel.upper()},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def _query_recent_errors(session: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if _table_exists(session, "master_ai_events"):
        rows.extend(
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT 'Master AI' AS source,
                           severity AS status,
                           LEFT(message, 220) AS message,
                           created_at
                    FROM public.master_ai_events
                    WHERE severity IN ('ERROR', 'CRITICAL')
                    ORDER BY created_at DESC
                    LIMIT 4
                    """
                )
            )
            .mappings()
            .all()
        )
    if _table_exists(session, "ai_agent_runs"):
        rows.extend(
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT agent_key AS source,
                           status,
                           LEFT(error, 220) AS message,
                           COALESCE(finished_at, started_at) AS created_at
                    FROM public.ai_agent_runs
                    WHERE error IS NOT NULL AND error <> ''
                    ORDER BY COALESCE(finished_at, started_at) DESC
                    LIMIT 4
                    """
                )
            )
            .mappings()
            .all()
        )
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return rows[:6]


def _table_exists(session: Any, table_name: str) -> bool:
    return bool(
        session.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": f"public.{table_name}"},
        ).scalar_one_or_none()
    )


def _column_exists(session: Any, table_name: str, column_name: str) -> bool:
    return bool(
        session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND column_name = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar_one_or_none()
    )


def _render_small_table(
    rows: list[dict[str, Any]],
    *,
    empty_message: str,
) -> None:
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(empty_message)


def _render_google_sheet_sync_status() -> None:
    if not is_google_sheets_configured():
        st.warning(f"Google Sheet safe-disabled: {google_sheets_disabled_reason()}")
        return
    try:
        service = PrivateGoogleSheetsService()
        service.ensure_required_tabs()
        rows = service.read_rows("errors", limit=1)
    except GoogleSheetsServiceError as exc:
        st.warning(f"Google Sheet not ready: {exc}")
    except Exception:
        logger.exception("Google Sheet sync status check failed")
        st.error("Google Sheet sync check failed.")
    else:
        st.success("Google Sheet connected and required tabs are ready.")
        if rows:
            st.caption(f"Latest Sheet error row: {rows[-1]}")


def _render_user_lead_manager() -> None:
    st.subheader("User / Lead Manager")
    try:
        with session_scope() as session:
            optional_columns = {
                column: _column_exists(session, "users", column)
                for column in ("name", "phone", "telegram_id", "source")
            }
            select_parts = [
                "u.id",
                (
                    "u.name"
                    if optional_columns["name"]
                    else "''::text AS name"
                ),
                (
                    "u.phone"
                    if optional_columns["phone"]
                    else "''::text AS phone"
                ),
                "u.email",
                (
                    "u.telegram_id"
                    if optional_columns["telegram_id"]
                    else "''::text AS telegram_id"
                ),
                "u.whatsapp AS whatsapp_number",
                "u.payment_status AS subscription_status",
                (
                    "u.source"
                    if optional_columns["source"]
                    else "''::text AS source"
                ),
                "u.created_at",
            ]
            rows = [
                dict(row)
                for row in (
                session.execute(
                    text(
                        f"""
                        SELECT {", ".join(select_parts)}
                        FROM public.users u
                        ORDER BY u.created_at DESC
                        LIMIT 200
                        """
                    )
                )
                .mappings()
                .all()
                )
            ]
    except Exception:
        logger.exception("User lead manager loading failed")
        st.error("User/lead manager is temporarily unavailable.")
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )
    _render_lead_editor(rows, optional_columns)


def _render_lead_editor(
    rows: list[dict[str, Any]],
    optional_columns: dict[str, bool],
) -> None:
    st.markdown("### Edit Lead Details")
    if not rows:
        st.info("No users or leads found.")
        return

    options = {
        f"#{row['id']} · {row.get('email') or row.get('phone') or 'lead'}": row
        for row in rows
    }
    selected = options[st.selectbox("Select user/lead", list(options))]
    with st.form("lead_editor"):
        name = st.text_input("Name", value=str(selected.get("name") or ""))
        phone = st.text_input("Phone", value=str(selected.get("phone") or ""))
        telegram_id = st.text_input(
            "Telegram ID",
            value=str(selected.get("telegram_id") or ""),
        )
        whatsapp = st.text_input(
            "WhatsApp number",
            value=str(selected.get("whatsapp_number") or ""),
        )
        source = st.text_input("Source", value=str(selected.get("source") or ""))
        status = st.selectbox(
            "Subscription status",
            PAYMENT_STATES,
            index=(
                PAYMENT_STATES.index(selected["subscription_status"])
                if selected.get("subscription_status") in PAYMENT_STATES
                else 0
            ),
        )
        submitted = st.form_submit_button(
            "Update Lead",
            type="primary",
            use_container_width=True,
        )
    if not submitted:
        return

    updates = {
        "whatsapp": whatsapp.strip(),
        "payment_status": status,
    }
    if optional_columns.get("name"):
        updates["name"] = name.strip()
    if optional_columns.get("phone"):
        updates["phone"] = phone.strip()
    if optional_columns.get("telegram_id"):
        updates["telegram_id"] = telegram_id.strip()
    if optional_columns.get("source"):
        updates["source"] = source.strip()

    assignments = ", ".join(f"{column} = :{column}" for column in updates)
    try:
        with session_scope() as session:
            session.execute(
                text(
                    f"""
                    UPDATE public.users
                    SET {assignments}, updated_at = NOW()
                    WHERE id = :user_id
                    """
                ),
                {**updates, "user_id": selected["id"]},
            )
    except Exception:
        logger.exception("Lead update failed")
        st.error("Lead could not be updated.")
    else:
        st.success("Lead updated.")
        st.rerun()


def _render_operations_logs() -> None:
    st.subheader("Operations Logs")
    db_tab, sheet_tab = st.tabs(["Database Logs", "Google Sheet Logs"])
    with db_tab:
        try:
            with session_scope() as session:
                st.markdown("### Telegram Master Logs")
                _render_small_table(
                    _query_latest_master_commands(session),
                    empty_message="No Telegram Master logs found.",
                )
                st.markdown("### WhatsApp Message Logs")
                _render_small_table(
                    _query_latest_channel_messages(session, "WHATSAPP"),
                    empty_message="No WhatsApp message logs found.",
                )
                st.markdown("### Error Logs")
                _render_small_table(
                    _query_recent_errors(session),
                    empty_message="No recent error logs found.",
                )
        except Exception:
            logger.exception("Database logs loading failed")
            st.error("Database logs are temporarily unavailable.")
    with sheet_tab:
        _render_google_sheet_logs()


def _render_google_sheet_logs() -> None:
    log_tabs = {
        "Telegram Master": "telegram_master_logs",
        "Telegram Public Signals": "telegram_public_signals",
        "WhatsApp Messages": "whatsapp_messages",
        "Google Sheet Sync": "xauusd_signals",
        "Errors": "errors",
    }
    selected_label = st.selectbox("Google Sheet log tab", list(log_tabs))
    if not is_google_sheets_configured():
        st.warning(f"Google Sheet logs safe-disabled: {google_sheets_disabled_reason()}")
        return
    try:
        rows = PrivateGoogleSheetsService().read_rows(
            log_tabs[selected_label],
            limit=50,
        )
    except GoogleSheetsServiceError as exc:
        st.warning(f"Google Sheet logs not ready: {exc}")
    except Exception:
        logger.exception("Google Sheet logs loading failed")
        st.error("Google Sheet logs could not be loaded.")
    else:
        _render_small_table(
            rows,
            empty_message=f"No {selected_label} rows found.",
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


def _category_public_url(category_slug: str, subcategory_slug: str = "") -> str:
    base_url = _admin_public_site_url()
    if subcategory_slug:
        return f"{base_url}/category/{quote(category_slug)}/{quote(subcategory_slug)}"
    return f"{base_url}/category/{quote(category_slug)}"


def _slug_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


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
        slug=str(item.get("slug") or item.get("seo_slug") or item["id"]),
        subcategory=str(item.get("subcategory") or ""),
        status="published" if is_published else "draft",
        meta_title=str(item.get("meta_title") or ""),
        meta_description=str(item.get("meta_description") or ""),
        focus_keyword=str(item.get("focus_keyword") or ""),
        faq=item.get("faq") or [],
        schema_jsonld=item.get("schema_jsonld") or {},
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

    _render_content_view_analytics(items)

    content_scopes = {
        "Blogs": {"BLOG", "AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"},
        "Pages": {"PAGE"},
        "Announcements": {"ANNOUNCEMENT"},
        "Signals": {"SIGNAL_POST"},
        "All content": None,
    }
    scope_name = st.selectbox(
        "Content list",
        list(content_scopes),
        help="Filter the editor list without changing any saved records.",
    )
    allowed_types = content_scopes[scope_name]
    visible_items = [
        item for item in items
        if item["content_type"] != "PROFIT_SCREENSHOT"
        and (
            allowed_types is None
            or str(item.get("content_type") or "").upper() in allowed_types
        )
    ]

    options = {"Create new": None}
    options.update(
        {
            f"#{item['id']} · {item['title']}": item
            for item in visible_items
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
        if str(selected.get("content_type") or "").upper() in {
            "BLOG",
            "AI_BLOG",
            "ADVISORY",
            "ANALYSIS",
            "EDUCATION",
        }:
            _render_wordpress_style_blog_panel(selected)
        _render_selected_content_metadata(selected)
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
        slug = st.text_input(
            "Slug",
            value=(
                selected.get("slug")
                or selected.get("seo_slug")
                or ""
            ) if selected else "",
            help="Clean URL slug, for example: xauusd-usa-market-outlook",
        )
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
        subcategory = st.text_input(
            "Subcategory",
            value=(selected.get("subcategory") or "") if selected else "",
            help="Optional public grouping such as USA Market, Gold News, Strategy.",
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
        status_options = ["draft", "published"]
        selected_status = (
            "published"
            if selected and selected.get("is_published")
            else str((selected or {}).get("status") or "draft").lower()
        )
        status = col2.selectbox(
            "Status",
            status_options,
            index=(
                status_options.index(selected_status)
                if selected_status in status_options
                else 0
            ),
        )
        with st.expander("SEO metadata"):
            meta_title = st.text_input(
                "Meta title",
                value=(selected.get("meta_title") or "") if selected else "",
            )
            meta_description = st.text_area(
                "Meta description",
                value=(selected.get("meta_description") or "") if selected else "",
                height=90,
            )
            focus_keyword = st.text_input(
                "Focus keyword",
                value=(selected.get("focus_keyword") or "") if selected else "",
            )
            faq = st.text_area(
                "FAQ JSON",
                value=json.dumps(
                    selected.get("faq") or [],
                    ensure_ascii=False,
                    indent=2,
                ) if selected else "[]",
                height=120,
            )
            schema_jsonld = st.text_area(
                "Schema JSON-LD",
                value=json.dumps(
                    selected.get("schema_jsonld") or {},
                    ensure_ascii=False,
                    indent=2,
                ) if selected else "{}",
                height=140,
            )
            image_prompt = st.text_area(
                "Image prompt",
                value=(selected.get("image_prompt") or "") if selected else "",
                height=90,
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
                slug=slug,
                subcategory=subcategory,
                image_url=image_url,
                external_url=external_url,
                is_public=is_public,
                is_published=status == "published",
                status=status,
                meta_title=meta_title,
                meta_description=meta_description,
                focus_keyword=focus_keyword,
                faq=faq,
                schema_jsonld=schema_jsonld,
                image_prompt=image_prompt,
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


def _render_selected_content_metadata(selected: dict[str, Any]) -> None:
    """Show CMS/SEO fields for quick review without exposing internals."""
    st.markdown("#### Content metadata")
    meta_cols = st.columns(5)
    meta_cols[0].metric("Type", str(selected.get("content_type") or "—"))
    meta_cols[1].metric(
        "Status",
        "Published" if selected.get("is_published") else "Draft",
    )
    meta_cols[2].metric(
        "Category",
        str(selected.get("category_title") or "Uncategorized"),
    )
    meta_cols[3].metric(
        "Subcategory",
        str(selected.get("subcategory") or "—"),
    )
    meta_cols[4].metric("Views", int(selected.get("view_count") or 0))
    last_viewed = str(selected.get("last_viewed_at") or "").strip()
    if last_viewed:
        st.caption(f"Last viewed: {last_viewed}")

    with st.expander("View SEO metadata / FAQ / schema"):
        st.write(
            {
                "slug": selected.get("slug") or selected.get("seo_slug") or "",
                "meta_title": selected.get("meta_title") or "",
                "meta_description": selected.get("meta_description") or "",
                "focus_keyword": selected.get("focus_keyword") or "",
                "image_prompt": selected.get("image_prompt") or "",
            }
        )
        st.markdown("**FAQ**")
        st.json(selected.get("faq") or [])
        st.markdown("**Schema JSON-LD**")
        st.json(selected.get("schema_jsonld") or {})


def _render_content_view_analytics(items: list[dict[str, Any]]) -> None:
    """Surface public post performance without relying on third-party analytics."""
    public_posts = [
        item for item in items
        if item.get("is_public")
        and item.get("is_published")
        and str(item.get("content_type") or "").upper()
        in {"BLOG", "AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"}
    ]
    if not public_posts:
        return

    total_views = sum(int(item.get("view_count") or 0) for item in public_posts)
    high_view_posts = sorted(
        public_posts,
        key=lambda item: int(item.get("view_count") or 0),
        reverse=True,
    )[:5]
    low_view_posts = sorted(
        public_posts,
        key=lambda item: (
            int(item.get("view_count") or 0),
            str(item.get("published_at") or item.get("created_at") or ""),
        ),
    )[:5]

    st.markdown("#### Blog View Analytics")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Public Posts", len(public_posts))
    metric_cols[1].metric("Total Views", total_views)
    metric_cols[2].metric(
        "Needs Boost",
        sum(1 for item in public_posts if int(item.get("view_count") or 0) == 0),
    )

    with st.expander("High views / Low views", expanded=False):
        left, right = st.columns(2)
        with left:
            st.caption("High views")
            _render_admin_post_analytics_list(high_view_posts)
        with right:
            st.caption("Low views")
            _render_admin_post_analytics_list(low_view_posts)


def _render_admin_post_analytics_list(items: list[dict[str, Any]]) -> None:
    if not items:
        st.info("No posts available.")
        return
    for item in items:
        title = str(item.get("title") or "Untitled post")
        views = int(item.get("view_count") or 0)
        public_url = _content_public_url(item)
        if public_url:
            st.markdown(f"- [{title}]({public_url}) · {views} views")
        else:
            st.markdown(f"- {title} · {views} views")


def _render_wordpress_style_blog_panel(selected: dict[str, Any]) -> None:
    """Show a WordPress-style blog post and SEO review panel."""
    st.markdown("### Blog Post SEO Editor")
    public_url = _content_public_url(selected)
    slug = str(selected.get("slug") or selected.get("seo_slug") or "").strip()
    title = str(selected.get("title") or "")
    meta_title = str(selected.get("meta_title") or "")
    meta_description = str(selected.get("meta_description") or "")
    focus_keyword = str(selected.get("focus_keyword") or "")
    excerpt = str(selected.get("excerpt") or "")
    body = str(selected.get("body") or "")

    score = _seo_readiness_score(
        title=title,
        slug=slug,
        meta_title=meta_title,
        meta_description=meta_description,
        focus_keyword=focus_keyword,
        excerpt=excerpt,
        body=body,
    )
    status_label = "Published" if selected.get("is_published") else "Draft"
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("SEO Score", f"{score}%")
    kpi_cols[1].metric("Post Status", status_label)
    kpi_cols[2].metric("Focus Keyword", focus_keyword or "Missing")
    kpi_cols[3].metric("Slug", slug or "Missing")

    preview_tab, seo_tab, schema_tab = st.tabs(
        ["Post Preview", "SEO Settings", "FAQ / Schema"]
    )
    with preview_tab:
        st.caption("WordPress-style public snippet preview")
        st.markdown(f"#### {meta_title or title or 'Untitled post'}")
        st.caption(public_url or "Public URL will appear after slug is saved.")
        st.write(meta_description or excerpt or "Meta description is missing.")
        if public_url:
            st.link_button(
                "Open Blog Post",
                public_url,
                use_container_width=True,
            )
        st.markdown("**Article body preview**")
        st.markdown(body[:2200] or "_No article body yet._")

    with seo_tab:
        checklist = _seo_checklist(
            title=title,
            slug=slug,
            meta_title=meta_title,
            meta_description=meta_description,
            focus_keyword=focus_keyword,
            excerpt=excerpt,
            body=body,
        )
        for item in checklist:
            icon = "✅" if item["ok"] else "⚠️"
            st.write(f"{icon} {item['label']}")
        st.info(
            "Edit Title, Slug, Meta title, Meta description, Focus keyword, "
            "and Body in the Save Content form below. This panel is for quick "
            "WordPress-style review."
        )

    with schema_tab:
        st.markdown("**FAQ JSON**")
        st.json(selected.get("faq") or [])
        st.markdown("**Schema JSON-LD**")
        st.json(selected.get("schema_jsonld") or {})
        st.markdown("**Image Prompt**")
        st.code(str(selected.get("image_prompt") or "No image prompt saved."))


def _seo_readiness_score(
    *,
    title: str,
    slug: str,
    meta_title: str,
    meta_description: str,
    focus_keyword: str,
    excerpt: str,
    body: str,
) -> int:
    checks = _seo_checklist(
        title=title,
        slug=slug,
        meta_title=meta_title,
        meta_description=meta_description,
        focus_keyword=focus_keyword,
        excerpt=excerpt,
        body=body,
    )
    passed = sum(1 for item in checks if item["ok"])
    return int((passed / max(len(checks), 1)) * 100)


def _seo_checklist(
    *,
    title: str,
    slug: str,
    meta_title: str,
    meta_description: str,
    focus_keyword: str,
    excerpt: str,
    body: str,
) -> list[dict[str, Any]]:
    keyword = focus_keyword.strip().lower()
    combined = " ".join([title, slug, meta_title, meta_description, body]).lower()
    return [
        {
            "label": "Title is present and readable",
            "ok": 20 <= len(title.strip()) <= 90,
        },
        {
            "label": "SEO slug is present",
            "ok": bool(slug.strip()),
        },
        {
            "label": "Meta title is 30-70 characters",
            "ok": 30 <= len(meta_title.strip()) <= 70,
        },
        {
            "label": "Meta description is 120-165 characters",
            "ok": 120 <= len(meta_description.strip()) <= 165,
        },
        {
            "label": "Focus keyword is present in SEO fields",
            "ok": bool(keyword and keyword in combined),
        },
        {
            "label": "Excerpt is present",
            "ok": bool(excerpt.strip()),
        },
        {
            "label": "Article body has useful length",
            "ok": len(body.split()) >= 250,
        },
    ]


def _render_category_manager() -> None:
    st.subheader("Website Categories")
    try:
        categories = list_categories(public_only=False)
        subcategories = list_content(
            content_type="SUBCATEGORY",
            public_only=False,
            limit=200,
        )
    except Exception:
        logger.exception("Category manager loading failed")
        st.error("Categories are temporarily unavailable.")
        return
    if categories:
        st.markdown("### Public Category Links")
        st.dataframe(
            [
                {
                    "title": category["title"],
                    "slug": category["slug"],
                    "public_link": _category_public_url(str(category["slug"])),
                    "active": category["is_active"],
                    "public": category["is_public"],
                }
                for category in categories
            ],
            use_container_width=True,
            hide_index=True,
        )
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

    st.divider()
    _render_subcategory_manager(categories, subcategories)


def _render_subcategory_manager(
    categories: list[dict[str, Any]],
    subcategories: list[dict[str, Any]],
) -> None:
    st.subheader("Website Subcategories")
    category_options = {
        category["title"]: category
        for category in categories
        if category.get("is_active")
    }
    if not category_options:
        st.info("Create an active category before adding subcategories.")
        return

    if subcategories:
        st.dataframe(
            [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "slug": item.get("slug") or item.get("seo_slug") or "",
                    "category": item.get("category_title") or "Uncategorized",
                    "public_link": _category_public_url(
                        str(item.get("category_slug") or ""),
                        _slug_fragment(
                            str(item.get("slug") or item.get("seo_slug") or item["title"])
                        ),
                    ) if item.get("category_slug") else "",
                    "published": item.get("is_published"),
                }
                for item in subcategories
            ],
            use_container_width=True,
            hide_index=True,
        )

    options = {"Create new subcategory": None}
    options.update(
        {
            f"#{item['id']} · {item['title']}": item
            for item in subcategories
        }
    )
    selected = options[st.selectbox("Select subcategory", list(options))]
    selected_category = next(
        (
            title for title, category in category_options.items()
            if selected and category["id"] == selected.get("category_id")
        ),
        next(iter(category_options)),
    )

    with st.form("subcategory_editor"):
        title = st.text_input(
            "Subcategory title",
            value=(selected.get("title") or "") if selected else "",
        )
        slug = st.text_input(
            "Subcategory slug",
            value=(
                selected.get("slug")
                or selected.get("seo_slug")
                or ""
            ) if selected else "",
        )
        category_name = st.selectbox(
            "Parent category",
            list(category_options),
            index=list(category_options).index(selected_category),
        )
        excerpt = st.text_area(
            "Description",
            value=(selected.get("excerpt") or "") if selected else "",
        )
        is_public = st.checkbox(
            "Visible publicly",
            value=bool(selected["is_public"]) if selected else True,
        )
        is_published = st.checkbox(
            "Published",
            value=bool(selected["is_published"]) if selected else True,
        )
        submitted = st.form_submit_button(
            "Save Subcategory",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return
    admin_id = get_current_user_id()
    if admin_id is None:
        st.error("Administrator session is invalid.")
        return
    parent_category = category_options[category_name]
    try:
        save_content(
            content_id=int(selected["id"]) if selected else None,
            content_type="SUBCATEGORY",
            title=title,
            slug=slug or title,
            excerpt=excerpt,
            body=excerpt,
            category_id=int(parent_category["id"]),
            subcategory=slug or title,
            image_url="",
            external_url="",
            is_public=is_public,
            is_published=is_published,
            status="published" if is_published else "draft",
            created_by=admin_id,
        )
    except Exception as exc:
        logger.exception("Subcategory save failed")
        st.error(str(exc) if isinstance(exc, ValueError) else "Save failed.")
    else:
        st.success("Subcategory saved.")
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
    st.subheader("Settings")
    st.caption(
        "Operational IDs and website settings are stored server-side. "
        "Bot tokens, API keys, and passwords are never displayed here."
    )
    admin_id = get_current_user_id()
    if admin_id is None:
        st.error("Administrator session is invalid.")
        return
    setting_keys = [
        "telegram_invite_url",
        "telegram_public_chat_id",
        "whatsapp_invite_url",
        "whatsapp_phone_number_id",
        "profit_proof_telegram_url",
        "google_sheet_id",
        "feature_public_blog",
        "feature_public_signals",
        "feature_whatsapp_reply",
        "feature_google_sheet_sync",
        "website_hero_title",
        "website_hero_subtitle",
        "website_announcement_text",
        "master_ai_blog_default_status",
    ]
    try:
        values = {key: get_site_setting(key) for key in setting_keys}
    except Exception:
        logger.exception("Protected setting loading failed")
        values = {key: "" for key in setting_keys}
    with st.form("channel_settings"):
        st.markdown("#### Channel IDs")
        telegram_value = st.text_input(
            "Private Telegram invite URL",
            value=values["telegram_invite_url"],
            type="password",
        )
        telegram_public_chat_id = st.text_input(
            "Telegram public channel/chat ID",
            value=values["telegram_public_chat_id"],
        )
        whatsapp_value = st.text_input(
            "Private WhatsApp invite URL",
            value=values["whatsapp_invite_url"],
            type="password",
        )
        whatsapp_phone_number_id = st.text_input(
            "WhatsApp phone number ID",
            value=values["whatsapp_phone_number_id"],
        )
        proof_value = st.text_input(
            "Public profit-proof Telegram URL",
            value=values["profit_proof_telegram_url"],
        )
        google_sheet_id = st.text_input(
            "Google Sheet ID",
            value=values["google_sheet_id"],
        )
        st.markdown("#### Feature Toggles")
        toggle_cols = st.columns(4)
        feature_public_blog = toggle_cols[0].checkbox(
            "Public blog",
            value=_setting_enabled(values["feature_public_blog"], default=True),
        )
        feature_public_signals = toggle_cols[1].checkbox(
            "Public signals",
            value=_setting_enabled(values["feature_public_signals"], default=True),
        )
        feature_whatsapp_reply = toggle_cols[2].checkbox(
            "WhatsApp reply",
            value=_setting_enabled(values["feature_whatsapp_reply"], default=True),
        )
        feature_google_sheet_sync = toggle_cols[3].checkbox(
            "Google Sheet sync",
            value=_setting_enabled(values["feature_google_sheet_sync"], default=True),
        )
        st.markdown("#### Website Settings")
        website_hero_title = st.text_input(
            "Website hero title",
            value=values["website_hero_title"],
        )
        website_hero_subtitle = st.text_area(
            "Website hero subtitle",
            value=values["website_hero_subtitle"],
        )
        website_announcement_text = st.text_area(
            "Website announcement text",
            value=values["website_announcement_text"],
        )
        master_ai_blog_default_status = st.selectbox(
            "Master AI blog default status",
            ["published", "draft"],
            index=(
                1
                if values["master_ai_blog_default_status"].strip().lower()
                == "draft"
                else 0
            ),
        )
        submitted = st.form_submit_button(
            "Save Settings",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        try:
            updates = {
                "telegram_invite_url": telegram_value,
                "telegram_public_chat_id": telegram_public_chat_id,
                "whatsapp_invite_url": whatsapp_value,
                "whatsapp_phone_number_id": whatsapp_phone_number_id,
                "profit_proof_telegram_url": proof_value,
                "google_sheet_id": google_sheet_id,
                "feature_public_blog": str(feature_public_blog).lower(),
                "feature_public_signals": str(feature_public_signals).lower(),
                "feature_whatsapp_reply": str(feature_whatsapp_reply).lower(),
                "feature_google_sheet_sync": str(feature_google_sheet_sync).lower(),
                "website_hero_title": website_hero_title,
                "website_hero_subtitle": website_hero_subtitle,
                "website_announcement_text": website_announcement_text,
                "master_ai_blog_default_status": master_ai_blog_default_status,
            }
            for key, value in updates.items():
                save_site_setting(key, value, admin_id)
        except Exception:
            logger.exception("Protected channel setting save failed")
            st.error("Settings could not be saved.")
        else:
            st.success("Settings updated.")


def _setting_enabled(value: str, *, default: bool) -> bool:
    cleaned = str(value or "").strip().lower()
    if cleaned in {"true", "1", "yes", "on"}:
        return True
    if cleaned in {"false", "0", "no", "off"}:
        return False
    return default


def _render_signal_form(supabase: Any) -> None:
    st.subheader("Signal Manager")
    with st.form("admin_signal_form"):
        left, right = st.columns(2)
        with left:
            direction = st.radio("Direction", ["BUY", "SELL"], horizontal=True)
            entry = st.text_input("Entry")
            target_1 = st.text_input("Target 1")
            target_2 = st.text_input("Target 2")
            target_3 = st.text_input("Target 3")
            stop_loss = st.text_input("Stop loss")
        with right:
            risk_level = st.selectbox(
                "Risk level",
                ["Low", "Medium", "High"],
            )
            timeframe = st.selectbox(
                "Timeframe",
                ["Scalp", "Intraday", "Swing"],
            )
            send_telegram = st.checkbox(
                "Send to Telegram public bot/channel",
                value=True,
            )
            save_sheet = st.checkbox("Save to Google Sheet", value=True)
        note = st.text_area("Note")
        submitted = st.form_submit_button(
            "Create Signal",
            type="primary",
            use_container_width=True,
        )
    if not submitted:
        return

    try:
        entry_value = _required_decimal(entry, "Entry")
        target_1_value = _required_decimal(target_1, "Target 1")
        target_2_value = _optional_decimal(target_2)
        target_3_value = _optional_decimal(target_3)
        stop_loss_value = _required_decimal(stop_loss, "Stop loss")
    except ValueError as exc:
        st.warning(str(exc))
        return

    whatsapp_reply = _build_whatsapp_signal_reply(
        direction=direction,
        entry=entry,
        target_1=target_1,
        target_2=target_2,
        target_3=target_3,
        stop_loss=stop_loss,
        risk_level=risk_level,
        timeframe=timeframe,
        note=note,
    )
    payload = {
        "signal_type": direction,
        "price": entry_value,
        "target_price": target_1_value,
        "target_1": target_1_value,
        "target_2": target_2_value,
        "target_3": target_3_value,
        "stop_loss": stop_loss_value,
        "source": "ADMIN_PANEL",
        "sheet_label": f"Manual {direction} · {timeframe}",
        "risk_level": risk_level,
        "timeframe": timeframe,
        "note": note.strip(),
        "whatsapp_reply": whatsapp_reply,
    }
    try:
        with session_scope() as session:
            signal_id = session.execute(
                text(
                    """
                    INSERT INTO public.market_signals (
                        symbol, price, signal_type, target_price,
                        target_1, target_2, target_3, stop_loss, source,
                        sheet_label, risk_level, timeframe, note,
                        whatsapp_reply, signal_time, updated_at
                    )
                    VALUES (
                        'XAUUSD', :price, :signal_type, :target_price,
                        :target_1, :target_2, :target_3, :stop_loss, :source,
                        :sheet_label, :risk_level, :timeframe, :note,
                        :whatsapp_reply, NOW(), NOW()
                    )
                    RETURNING id
                    """
                ),
                payload,
            ).scalar_one()
    except Exception:
        logger.exception("Signal publication failed")
        st.error("Signal could not be published.")
        return

    payload["id"] = signal_id
    telegram_sent = False
    if send_telegram:
        try:
            telegram_sent = TelegramService(supabase).send_signal(payload)
        except Exception:
            logger.exception("Manual signal Telegram delivery failed")

    sheet_saved = False
    if save_sheet:
        sheet_saved = _log_manual_signal_to_sheets(payload)

    st.success(f"{direction} signal saved successfully.")
    if send_telegram:
        (st.success if telegram_sent else st.warning)(
            "Telegram public signal sent."
            if telegram_sent
            else "Signal saved, but Telegram delivery did not complete."
        )
    if save_sheet:
        (st.success if sheet_saved else st.warning)(
            "Signal saved to Google Sheet."
            if sheet_saved
            else "Signal saved, but Google Sheet logging did not complete."
        )
    st.markdown("#### Prepared WhatsApp Reply")
    st.code(whatsapp_reply, language="text")


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

    _render_numbered_ai_controls(agents)

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


def _render_numbered_ai_controls(agents: list[dict[str, Any]]) -> None:
    """Render owner-friendly numbered AI ON/OFF controls."""
    st.markdown("### Numbered AI ON/OFF Control")
    st.caption(
        "Same numbers work in Master AI Telegram, for example: "
        "`/master on ai 1` or `/master off ai 3`."
    )
    by_key = {str(agent["agent_key"]): agent for agent in agents}
    columns = st.columns(2)
    for index, (number, agent_key, display_name) in enumerate(
        AI_AGENT_CONTROL_NUMBERS
    ):
        agent = by_key.get(agent_key)
        enabled = bool(agent.get("is_enabled")) if agent else False
        status = str(agent.get("status") or "MISSING") if agent else "MISSING"
        with columns[index % 2]:
            with st.container(border=True):
                st.markdown(f"**AI {number}: {display_name}**")
                st.caption(f"Key: `{agent_key}` · Status: {status}")
                label = "Turn OFF" if enabled else "Turn ON"
                button_type = "secondary" if enabled else "primary"
                if st.button(
                    label,
                    key=f"numbered_ai_toggle_{number}",
                    type=button_type,
                    use_container_width=True,
                    disabled=agent is None,
                ):
                    try:
                        set_ai_agent_enabled_by_number(number, not enabled)
                    except Exception:
                        logger.exception(
                            "Numbered AI toggle failed: {}",
                            agent_key,
                        )
                        st.error("AI setting could not be updated.")
                    else:
                        st.rerun()

    st.info(
        "Safe production default: AI agents can be enabled for explicit Master "
        "AI commands. Background auto schedules stay controlled separately; "
        "only the daily XAUUSD signal schedule is automatic."
    )


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
        raise ValueError("Signal price fields must be numeric.") from exc


def _required_decimal(value: str, label: str) -> Decimal:
    parsed = _optional_decimal(value)
    if parsed is None:
        raise ValueError(f"{label} is required.")
    return parsed


def _build_whatsapp_signal_reply(
    *,
    direction: str,
    entry: str,
    target_1: str,
    target_2: str,
    target_3: str,
    stop_loss: str,
    risk_level: str,
    timeframe: str,
    note: str,
) -> str:
    targets = [target_1.strip()]
    targets.extend(
        target.strip()
        for target in (target_2, target_3)
        if target.strip()
    )
    lines = [
        f"XAUUSD {direction.upper()} Signal",
        f"Entry: {entry.strip()}",
        f"Targets: {', '.join(targets)}",
        f"Stop Loss: {stop_loss.strip()}",
        f"Risk: {risk_level}",
        f"Timeframe: {timeframe}",
    ]
    if note.strip():
        lines.append(f"Note: {note.strip()}")
    lines.append("Manage risk carefully. No guaranteed profit.")
    return "\n".join(lines)


def _log_manual_signal_to_sheets(signal: dict[str, Any]) -> bool:
    try:
        service = PrivateGoogleSheetsService()
        service.append_row(
            "xauusd_signals",
            {
                "source": "admin_panel",
                "status": "created",
                "direction": signal["signal_type"],
                "entry": signal["price"],
                "target_1": signal["target_1"],
                "target_2": signal.get("target_2") or "",
                "target_3": signal.get("target_3") or "",
                "stop_loss": signal["stop_loss"],
                "risk_level": signal["risk_level"],
                "notes": signal.get("note") or "",
            },
        )
        service.append_row(
            "telegram_public_signals",
            {
                "status": "queued_or_sent",
                "direction": signal["signal_type"],
                "entry": signal["price"],
                "target_1": signal["target_1"],
                "target_2": signal.get("target_2") or "",
                "target_3": signal.get("target_3") or "",
                "stop_loss": signal["stop_loss"],
                "notes": signal.get("note") or "",
            },
        )
        service.append_row(
            "whatsapp_messages",
            {
                "status": "prepared",
                "message": signal["whatsapp_reply"],
                "reply": signal["whatsapp_reply"],
                "notes": f"Manual signal #{signal.get('id')}",
            },
        )
    except Exception:
        logger.exception("Manual signal Google Sheet logging failed")
        return False
    return True
