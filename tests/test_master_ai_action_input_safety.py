from types import SimpleNamespace

from services.master_ai_tool_router import execute_master_ai_action


def test_safe_payload_overrides_external_action_flags(monkeypatch):
    captured = {}

    def runner(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="COMPLETED", run_id=700, final_summary=None, safe_error=None)

    monkeypatch.setattr(
        "services.master_ai_tool_router._load_completed_step_output",
        lambda run_id, agent_key: "Customer guidance prepared safely.",
    )
    result = execute_master_ai_action(
        "run_customer_support_agent",
        runner=runner,
        input_payload={
            "customer_message": "How do I use the dashboard?",
            "send_whatsapp": True,
            "send_telegram": True,
            "process_payment": True,
        },
    )
    assert result.ok is True
    payload = captured["input_payload"]
    assert payload["send_whatsapp"] is False
    assert payload["send_telegram"] is False
    assert payload["process_payment"] is False


def test_missing_specialist_input_never_creates_orchestration_run():
    calls = []

    def runner(**kwargs):
        calls.append(kwargs)
        raise AssertionError("runner must not be called")

    result = execute_master_ai_action(
        "run_marketing_strategy_agent",
        runner=runner,
        input_payload={"campaign_request": "Make a marketing plan"},
    )
    assert result.ok is False
    assert result.status == "MISSING_INPUT"
    assert "public_url" in result.message
    assert calls == []


def test_social_media_requires_verified_published_content():
    result = execute_master_ai_action(
        "run_social_media_agent",
        runner=lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
        input_payload={
            "article_title": "Gold Guide",
            "public_url": "https://venusrealm.net/blog/gold-guide",
            "publish_status": "DRAFT",
        },
    )
    assert result.ok is False
    assert result.status == "MISSING_INPUT"
    assert "publish_status=PUBLISHED" in result.message


def test_blog_requested_image_is_preserved_while_publish_is_forced_false(monkeypatch):
    captured = {}

    def runner(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="COMPLETED", run_id=701, final_summary=None, safe_error=None)

    monkeypatch.setattr(
        "services.master_ai_tool_router._load_completed_step_output",
        lambda run_id, agent_key: "SEO blog #701 saved as draft with image.",
    )
    result = execute_master_ai_action(
        "run_blog_agent",
        runner=runner,
        input_payload={
            "topic": "XAUUSD risk management",
            "include_image": True,
            "publish": True,
            "owner_approved_publish": True,
        },
    )
    assert result.ok is True
    payload = captured["input_payload"]
    assert payload["include_image"] is True
    assert payload["publish"] is False
    assert "owner_approved_publish" not in payload
