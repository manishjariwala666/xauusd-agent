"""Offline tests for deterministic production-agent behavior."""

from services.production_agents import _seo_issues, _slugify
from services.telegram_service import TelegramService


def test_all_production_agent_runners_exist() -> None:
    from services.production_agents import RUNNERS

    assert set(RUNNERS) == {
        "ai_blog_agent",
        "telegram_reply_agent",
        "whatsapp_reply_agent",
        "signal_agent",
        "announcement_agent",
        "seo_agent",
        "image_agent",
    }


def test_slug_is_safe_and_stable() -> None:
    assert _slugify("XAUUSD: Risk & Reward!") == "xauusd-risk-reward"


def test_seo_issue_detection() -> None:
    issues = _seo_issues(
        {
            "meta_title": "",
            "meta_description": "",
            "focus_keyword": "",
            "slug": "",
        }
    )
    assert len(issues) == 4


def test_telegram_signal_formatter_escapes_html() -> None:
    message = TelegramService.format_message(
        {
            "signal_type": "BUY",
            "price": 2300,
            "target_price": 2320,
            "stop_loss": 2280,
            "sheet_label": "<unsafe>",
            "source": "test",
        }
    )
    assert "&lt;unsafe&gt;" in message
    assert "<unsafe>" not in message
