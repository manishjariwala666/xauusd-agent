from services.master_ai_tool_router import execute_master_ai_action


def test_tool_router_returns_safe_value_error_message(monkeypatch):
    def failing_runner(**kwargs):
        raise ValueError("Google Sheets credentials are unavailable.")

    result = execute_master_ai_action(
        "run_image_agent",
        source="TEST",
        runner=failing_runner,
    )

    assert result.ok is False
    assert result.status == "ERROR"
    assert "ValueError" not in result.message
    assert "Google Sheets credentials are unavailable." in result.message
    assert "Next action:" in result.message


def test_unknown_action_remains_blocked():
    result = execute_master_ai_action("delete_everything", source="TEST")

    assert result.ok is False
    assert result.status == "UNKNOWN_ACTION"
