import inspect

from admin import dashboard


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


def test_admin_content_list_uses_full_content_service_and_filters() -> None:
    source = inspect.getsource(dashboard._render_content_manager)

    assert "list_content(public_only=False, limit=200)" in source
    assert "Blogs" in source
    assert "Pages" in source
    assert "Announcements" in source
    assert "Signals" in source
    assert "All content" in source


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
