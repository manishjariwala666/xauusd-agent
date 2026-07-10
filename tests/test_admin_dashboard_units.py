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
