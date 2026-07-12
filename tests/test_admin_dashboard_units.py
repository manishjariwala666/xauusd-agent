import inspect
from pathlib import Path

from admin import dashboard
from components import theme


def test_latest_signal_query_uses_existing_market_signal_columns() -> None:
    source = inspect.getsource(dashboard._query_latest_signals)

    assert "sheet_label" in source
    assert "ORDER BY signal_time DESC" in source
    assert "status," not in source
    assert "created_at" not in source


def test_admin_dashboard_has_required_operational_widgets() -> None:
    source = inspect.getsource(dashboard._render_overview)

    assert "Total Blogs" in source
    assert "Published Blogs" in source
    assert "Draft Blogs" in source
    assert "Latest Telegram Master Commands" in source
    assert "Latest WhatsApp Messages" in source
    assert "Google Sheet Sync Status" in source
    assert "Recent Errors" in source


def test_admin_control_room_shell_and_agent_launchpad_exist() -> None:
    header_source = inspect.getsource(dashboard._render_admin_shell_header)
    launchpad_source = inspect.getsource(dashboard._render_agent_launchpad_cards)

    assert "ADMIN CONTROL ROOM" in header_source
    assert "Master AI Brain" in header_source
    assert "Agent Launchpad" in launchpad_source
    assert "ai_blog_agent" in launchpad_source
    assert "signal_agent" in launchpad_source
    assert "whatsapp_reply_agent" in launchpad_source


def test_able_pro_light_admin_v2_shell_exists() -> None:
    dashboard_source = inspect.getsource(dashboard.render_admin_dashboard)
    topbar_source = inspect.getsource(dashboard._render_admin_topbar)
    sidebar_source = inspect.getsource(dashboard._render_admin_light_sidebar)
    kpi_source = inspect.getsource(dashboard._render_admin_light_kpis)
    public_theme_source = inspect.getsource(theme.apply_theme)
    theme_source = inspect.getsource(theme.apply_admin_light_theme)

    assert "apply_admin_light_theme()" in dashboard_source
    assert "selected_page = _render_admin_light_sidebar()" in dashboard_source
    assert "_render_admin_topbar()" in dashboard_source
    assert "_render_admin_light_kpis()" in dashboard_source
    assert "Blog Studio" in dashboard_source
    assert "_render_blog_studio()" in dashboard_source
    assert "Ctrl + K" in topbar_source
    assert "st.radio" in sidebar_source
    assert "Content Manager" in sidebar_source
    assert "Signal Manager" in sidebar_source
    assert "admin-light-kpi-grid" in kpi_source
    assert "--admin-bg" in theme_source
    assert 'header[data-testid="stHeader"]' in public_theme_source
    assert '[data-testid="stDecoration"]' in public_theme_source
    assert 'initial_sidebar_state="expanded"' in Path("app.py").read_text()
    assert 'div[role="radiogroup"] label' in theme_source


def test_admin_ai_agents_has_numbered_on_off_controls() -> None:
    source = inspect.getsource(dashboard._render_numbered_ai_controls)
    render_source = inspect.getsource(dashboard._render_ai_agents)

    assert "AI_AGENT_CONTROL_NUMBERS" in source
    assert "/master on ai 1" in source
    assert "set_ai_agent_enabled_by_number" in source
    assert "_render_numbered_ai_controls(agents)" in render_source


def test_admin_content_list_uses_full_content_service_and_filters() -> None:
    source = inspect.getsource(dashboard._render_content_manager)

    assert "list_content(public_only=False, limit=200)" in source
    assert "WordPress-style blog controls" in source
    assert "Blogs" in source
    assert "Pages" in source
    assert "Announcements" in source
    assert "Signals" in source
    assert "All content" in source
    assert 'if scope_name == "Blogs" and content_options' in source


def test_admin_has_wordpress_style_blog_seo_panel() -> None:
    content_source = inspect.getsource(dashboard._render_content_manager)
    studio_source = inspect.getsource(dashboard._render_blog_studio)
    panel_source = inspect.getsource(dashboard._render_wordpress_style_blog_panel)
    score_source = inspect.getsource(dashboard._seo_readiness_score)

    assert "_render_wordpress_style_blog_panel(selected)" in content_source
    assert "_render_wordpress_style_blog_panel(selected)" in studio_source
    assert "Direct blog control room" in studio_source
    assert "Open Public Blog" in studio_source
    assert "Publish Now" in studio_source
    assert "Blog Post SEO Editor" in panel_source
    assert "Post Preview" in panel_source
    assert "SEO Settings" in panel_source
    assert "FAQ / Schema" in panel_source
    assert "Open Blog Post" in panel_source
    assert "_seo_checklist" in score_source


def test_admin_content_manager_has_blog_view_analytics() -> None:
    content_source = inspect.getsource(dashboard._render_content_manager)
    analytics_source = inspect.getsource(dashboard._render_content_view_analytics)

    assert "_render_content_view_analytics(items)" in content_source
    assert "Blog View Analytics" in analytics_source
    assert "Total Views" in analytics_source
    assert "Needs Boost" in analytics_source
    assert "High views / Low views" in analytics_source


def test_blog_studio_row_contains_wordpress_style_columns() -> None:
    row = dashboard._blog_studio_row(
        {
            "id": 12,
            "title": "XAUUSD Market Outlook",
            "slug": "xauusd-market-outlook",
            "meta_title": "XAUUSD Market Outlook and Risk Control",
            "meta_description": (
                "A practical XAUUSD market outlook with risk controls, "
                "support, resistance, and disciplined trading context."
            ),
            "focus_keyword": "xauusd market outlook",
            "excerpt": "Daily gold market context.",
            "body": "XAUUSD market outlook focuses on support and resistance.",
            "is_published": True,
            "view_count": 7,
            "updated_at": "2026-07-12",
        }
    )

    assert row["id"] == 12
    assert row["status"] == "Published"
    assert row["views"] == 7
    assert row["slug"] == "xauusd-market-outlook"
    assert row["seo_score"].endswith("%")


def test_admin_signal_manager_has_required_manual_fields() -> None:
    source = inspect.getsource(dashboard._render_signal_form)

    for label in (
        "Direction",
        "Entry",
        "Target 1",
        "Target 2",
        "Target 3",
        "Stop loss",
        "Risk level",
        "Timeframe",
        "Note",
        "Send to Telegram public bot/channel",
        "Save to Google Sheet",
    ):
        assert label in source


def test_admin_category_manager_has_route_source_and_seo_fields() -> None:
    source = inspect.getsource(dashboard._render_category_manager)
    link_source = inspect.getsource(dashboard._category_route_url)

    assert "URL Slug" in source
    assert "Public URL Path" in source
    assert "Source Type" in source
    assert "SEO Meta Description" in source
    assert "market_signals" in source
    assert "content_items" in source
    assert "_category_route_url(category)" in source
    assert "route_path" in link_source


def test_user_lead_and_logs_panels_exist() -> None:
    assert hasattr(dashboard, "_render_user_lead_manager")
    assert hasattr(dashboard, "_render_lead_editor")
    assert hasattr(dashboard, "_render_operations_logs")
    assert hasattr(dashboard, "_render_google_sheet_logs")


def test_whatsapp_signal_reply_contains_required_fields() -> None:
    reply = dashboard._build_whatsapp_signal_reply(
        direction="BUY",
        entry="4100",
        target_1="4110",
        target_2="4120",
        target_3="4130",
        stop_loss="4090",
        risk_level="Medium",
        timeframe="Intraday",
        note="Wait for confirmation",
    )

    assert "XAUUSD BUY Signal" in reply
    assert "Targets: 4110, 4120, 4130" in reply
    assert "Risk: Medium" in reply
    assert "Timeframe: Intraday" in reply
