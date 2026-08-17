from services.master_ai_chat_service import generate_master_ai_reply
from services.master_ai_tool_router import MasterAIToolResult


def test_blog_request_delegates_to_real_blog_action(monkeypatch):
    calls = []
    def fake_execute(action, **kwargs):
        calls.append((action, kwargs))
        return MasterAIToolResult(True, "run_blog_agent", "COMPLETED", "SEO blog #321 saved as draft.", 88)
    monkeypatch.setattr("services.master_ai_chat_service.execute_master_ai_action", fake_execute)
    reply = generate_master_ai_reply("Create an SEO blog draft using ai_blog_agent about XAUUSD.")
    assert calls
    assert calls[0][0] == "run_blog_agent"
    payload = calls[0][1]["input_payload"]
    assert payload["publish"] is False
    assert payload["include_image"] is True
    assert payload["target_word_min"] == 1400
    assert payload["target_word_max"] == 1600
    assert "SEO blog #321 saved as draft." in reply
    assert "Google Sheet Reference" not in reply


def test_publish_request_remains_locked():
    assert "approval-locked" in generate_master_ai_reply("Publish this blog post now.")


def test_blog_validator_enforces_requested_word_range():
    from services.production_agents import _valid_long_form_blog
    def article(words: int) -> dict:
        filler = " ".join(["gold"] * words)
        return {
            "body_markdown": "# XAUUSD Trading Strategy\n\n## Market Structure\n\n### Entry Confirmation\n\n## Risk Management\n\n## Gold Trading Setup\n\n## Trading Checklist\n\n" + filler + "\n\n<details><summary>FAQ</summary>Answer</details>",
            "faq": [{"question": f"Question {i}", "answer": "Answer"} for i in range(6)],
        }
    assert not _valid_long_form_blog(article(1200), minimum_words=1400, maximum_words=1600)
    assert _valid_long_form_blog(article(1450), minimum_words=1400, maximum_words=1600)
    assert not _valid_long_form_blog(article(1700), minimum_words=1400, maximum_words=1600)


def test_blog_with_featured_image_remains_single_blog_action():
    from services.master_ai_intent_resolver import resolve_master_ai_intent
    proposal = resolve_master_ai_intent("Create an SEO blog draft using ai_blog_agent about XAUUSD with a featured image and inline image.")
    assert proposal.status == "RESOLVED"
    assert proposal.action == "run_blog_agent"
    assert proposal.agent_key == "ai_blog_agent"
    assert proposal.parameters["publish"] is False
    assert proposal.parameters["include_image"] is True


def test_ambiguous_agent_request_never_reaches_llm(monkeypatch):
    def fail_llm(*args, **kwargs):
        raise AssertionError("LLM fallback must not run")
    monkeypatch.setattr("services.master_ai_chat_service._generate_gemini_reply", fail_llm)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    reply = generate_master_ai_reply("Blog Agent aur Image Agent dono se content banao")
    assert "Action execute nahi hua" in reply
    assert "multiple agent actions" in reply
    assert "created" not in reply.lower()


def test_unhandled_resolved_action_never_simulates_execution(monkeypatch):
    def fail_llm(*args, **kwargs):
        raise AssertionError("LLM fallback must not run")
    monkeypatch.setattr("services.master_ai_chat_service._generate_gemini_reply", fail_llm)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    reply = generate_master_ai_reply("Image Agent se thumbnail banao")
    assert "execution handler abhi connected nahi hai" in reply
    assert "Koi execution nahi hua" in reply


def test_blog_request_with_status_output_does_not_become_diagnostic():
    from services.master_ai_intent_resolver import resolve_master_ai_intent
    proposal = resolve_master_ai_intent("Create ONE SEO blog DRAFT using ai_blog_agent about XAUUSD with featured image. Return DRAFT_ID, WORD_COUNT and STATUS.")
    assert proposal.status == "RESOLVED"
    assert proposal.action == "run_blog_agent"
    assert proposal.agent_key == "ai_blog_agent"


def test_explicit_agent_status_request_remains_diagnostic():
    from services.master_ai_intent_resolver import resolve_master_ai_intent
    proposal = resolve_master_ai_intent("AI Blog Agent status batao")
    assert proposal.status == "RESOLVED"
    assert proposal.action == "read_agent_status"
    assert proposal.agent_key == "master_ai"


def test_tool_router_preserves_requested_blog_image(monkeypatch):
    from types import SimpleNamespace
    from services.master_ai_tool_router import execute_master_ai_action
    captured = {}
    def runner(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="COMPLETED", run_id=501, final_summary="1/1 steps completed; 0 failed.", safe_error=None)
    monkeypatch.setattr("services.master_ai_tool_router._load_completed_step_output", lambda run_id, agent_key: "SEO blog #987 saved as draft with 1502 words.")
    result = execute_master_ai_action("run_blog_agent", runner=runner, input_payload={"publish": False, "include_image": True})
    assert captured["input_payload"]["publish"] is False
    assert captured["input_payload"]["include_image"] is True
    assert captured["input_payload"]["agent_keys"] == ["ai_blog_agent"]
    assert result.ok is True
    assert result.run_id == 501
    assert result.message == "SEO blog #987 saved as draft with 1502 words."


def test_tool_router_never_returns_progress_summary_as_execution_result(monkeypatch):
    from types import SimpleNamespace
    from services.master_ai_tool_router import execute_master_ai_action
    def runner(**kwargs):
        return SimpleNamespace(status="COMPLETED", run_id=502, final_summary="1/1 steps completed; 0 failed.", safe_error=None)
    monkeypatch.setattr("services.master_ai_tool_router._load_completed_step_output", lambda run_id, agent_key: None)
    result = execute_master_ai_action("run_blog_agent", runner=runner)
    assert result.ok is False
    assert result.status == "UNVERIFIED_RESULT"
    assert "1/1 steps completed" not in result.message


def test_master_ai_blog_router_strips_publish_approval_override(monkeypatch):
    from types import SimpleNamespace
    from services.master_ai_tool_router import execute_master_ai_action
    captured = {}
    def runner(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="COMPLETED", run_id=503, final_summary=None, safe_error=None)
    monkeypatch.setattr("services.master_ai_tool_router._load_completed_step_output", lambda run_id, agent_key: "SEO blog #503 saved as draft with 1499 words.")
    result = execute_master_ai_action("run_blog_agent", runner=runner, input_payload={"publish": True, "owner_approved_publish": True, "include_image": True})
    assert result.ok is True
    assert captured["input_payload"]["publish"] is False
    assert "owner_approved_publish" not in captured["input_payload"]
