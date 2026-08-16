from services.master_ai_chat_service import generate_master_ai_reply
from services.master_ai_tool_router import MasterAIToolResult


def test_blog_request_delegates_to_real_blog_action(monkeypatch):
    calls = []

    def fake_execute(action, **kwargs):
        calls.append((action, kwargs))
        return MasterAIToolResult(
            ok=True,
            action="run_blog_agent",
            status="COMPLETED",
            message="SEO blog #321 saved as draft.",
            run_id=88,
        )

    monkeypatch.setattr(
        "services.master_ai_chat_service.execute_master_ai_action",
        fake_execute,
    )

    reply = generate_master_ai_reply(
        "Create an SEO blog draft using ai_blog_agent about XAUUSD."
    )

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
    reply = generate_master_ai_reply(
        "Publish this blog post now."
    )

    assert "approval-locked" in reply

def test_blog_validator_enforces_requested_word_range():
    from services.production_agents import _valid_long_form_blog

    def article(words: int) -> dict:
        filler = " ".join(["gold"] * words)
        return {
            "body_markdown": (
                "# XAUUSD Trading Strategy\n\n"
                "## Market Structure\n\n"
                "### Entry Confirmation\n\n"
                "## Risk Management\n\n"
                "## Gold Trading Setup\n\n"
                "## Trading Checklist\n\n"
                f"{filler}\n\n"
                "<details><summary>FAQ</summary>Answer</details>"
            ),
            "faq": [
                {"question": f"Question {i}", "answer": "Answer"}
                for i in range(6)
            ],
        }

    assert not _valid_long_form_blog(
        article(1200),
        minimum_words=1400,
        maximum_words=1600,
    )

    assert _valid_long_form_blog(
        article(1450),
        minimum_words=1400,
        maximum_words=1600,
    )

    assert not _valid_long_form_blog(
        article(1700),
        minimum_words=1400,
        maximum_words=1600,
    )
