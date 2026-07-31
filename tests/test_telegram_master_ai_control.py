"""Tests for Telegram Master AI admin command control."""

from __future__ import annotations

from dataclasses import dataclass

from services.master_orchestrator import OrchestrationProgress
from services.telegram_master_ai_control import (
    MASTER_AI_BOT,
    SAFE_TELEGRAM_ERROR,
    SIGNAL_BOT,
    _run_started_text,
    handle_master_command_text,
    help_text,
    is_master_command,
    parse_master_command,
    try_handle_telegram_update,
)


@dataclass
class FakeRunnerCall:
    task_type: str
    title: str
    input_payload: dict
    requested_by: int | None
    source: str


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[FakeRunnerCall] = []

    def __call__(self, **kwargs):
        self.calls.append(FakeRunnerCall(**{key: kwargs[key] for key in FakeRunnerCall.__annotations__}))
        return OrchestrationProgress(
            run_id=42,
            task_id=7,
            status="COMPLETED",
            completed_steps=2,
            total_steps=2,
        )


def update(text: str, *, user_id: int = 1001, chat_id: int = 1) -> dict:
    return {"message": {"text": text, "chat": {"id": chat_id}, "from": {"id": user_id}}}


def test_master_command_parser_accepts_bot_suffix() -> None:
    assert is_master_command("/master status")
    assert is_master_command("/master@my_bot status")
    assert is_master_command("master status")
    assert not is_master_command("hello")
    assert parse_master_command("/master run blog") == ("run", "blog")
    assert parse_master_command("/master") == ("help", None)


def test_master_command_parser_accepts_numbered_ai_toggles() -> None:
    assert parse_master_command("/master list ai") == ("list_ai", None)
    assert parse_master_command("/master on ai 1") == ("on", "1")
    assert parse_master_command("/master off ai 3") == ("off", "3")
    assert parse_master_command("/master enable agent 6") == ("on", "6")


def test_natural_master_ai_error_sentence_reaches_read_only_diagnostics(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    calls: list[str] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control.generate_master_ai_reply",
        lambda message: calls.append(message) or "SAFE_STUB_REPLY",
    )

    result = handle_master_command_text(
        text="Master ai error door karo",
        telegram_user_id=1001,
        chat_id=55,
        status_loader=lambda: [
            {
                "agent_key": "master_ai",
                "display_name": "Master AI",
                "status": "IDLE",
                "is_enabled": True,
            }
        ],
    )

    assert is_master_command("Master ai error door karo") is False
    assert parse_master_command("Master ai error door karo") == ("", None)
    assert result.status == "COMPLETED"
    assert "Master AI: IDLE" in (result.response_text or "")
    assert calls == []
    assert result.response_text != help_text()


def test_help_command_requires_admin(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    result = handle_master_command_text(
        text="/master help",
        telegram_user_id=1001,
        chat_id=55,
    )
    assert result.handled is True
    assert result.response_text == help_text()
    assert result.chat_id == 55


def test_non_admin_is_blocked(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    result = handle_master_command_text(
        text="/master run blog",
        telegram_user_id=9999,
        chat_id=55,
        runner=runner,
    )
    assert result.handled is True
    assert result.status == "UNAUTHORIZED"
    assert "Unauthorized" in (result.response_text or "")
    assert runner.calls == []


def test_run_blog_routes_to_master_orchestrator_on_master_bot(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    result = try_handle_telegram_update(
        update("/master run blog", user_id=1001, chat_id=55),
        bot_role=MASTER_AI_BOT,
        runner=runner,
    )
    assert result.handled is True
    assert result.run_id == 42
    assert result.task_type == "BLOG"
    assert runner.calls[0].source == "TELEGRAM_MASTER_COMMAND"
    assert runner.calls[0].requested_by is None
    assert runner.calls[0].input_payload["telegram_target"] == "blog"
    assert "token" not in str(result.response_text).lower()


def test_master_bot_accepts_natural_blog_text_without_env_flag(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    monkeypatch.delenv("MASTER_AI_ALLOW_NATURAL_COMMANDS", raising=False)
    runner = FakeRunner()
    result = try_handle_telegram_update(
        update("xauusd buy or sell today par SEO blog banao", user_id=1001, chat_id=55),
        bot_role=MASTER_AI_BOT,
        runner=runner,
    )

    assert result.handled is True
    assert result.task_type == "BLOG"
    assert runner.calls[0].input_payload["telegram_target"] == "blog"
    assert runner.calls[0].input_payload["publish"] is False
    assert runner.calls[0].input_payload["include_image"] is False


def test_telegram_blog_started_text_uses_venusrealm_public_url(monkeypatch) -> None:
    def fake_list_content(*, content_type: str, public_only: bool, limit: int):
        assert public_only is True
        assert limit == 1
        if content_type == "AI_BLOG":
            return [
                {
                    "content_type": "AI_BLOG",
                    "slug": "xauusd-usa-market",
                    "seo_slug": "xauusd-usa-market",
                }
            ]
        return []

    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://venusrealm.net")
    monkeypatch.setattr(
        "services.content_service.list_content",
        fake_list_content,
    )
    progress = OrchestrationProgress(
        run_id=42,
        task_id=7,
        status="COMPLETED",
        completed_steps=1,
        total_steps=1,
    )

    text = _run_started_text("blog", progress)

    assert "Blog workflow: DRAFT ONLY." in text
    assert "Latest blog URL:" not in text
    assert "xauusd-buy-sell-signal.streamlit.app" not in text
    assert "streamlit.app" not in text
    assert "xauusd-agent-web-production.up.railway.app" not in text


def test_master_bot_replies_helpfully_to_unknown_admin_text(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    result = try_handle_telegram_update(
        update("hello bhai", user_id=1001, chat_id=55),
        bot_role=MASTER_AI_BOT,
        runner=runner,
    )

    assert result.handled is True
    assert result.status == "AI_CHAT_RESPONSE"
    assert result.response_text
    assert runner.calls == []


def test_status_command_returns_safe_summary(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    monkeypatch.setattr(
        "services.telegram_master_ai_control.list_ai_agents",
        lambda: [
            {
                "agent_key": "ai_blog_agent",
                "display_name": "AI Blog Agent",
                "is_enabled": True,
                "status": "ERROR",
                "queue_size": 0,
                "last_run_at": None,
                "last_error": "/secret/path/token traceback",
            }
        ],
    )
    result = handle_master_command_text(
        text="/master status blog",
        telegram_user_id=1001,
        chat_id=55,
    )
    assert "AI Blog Agent status" in (result.response_text or "")
    assert "Internal agent configuration failed." in (result.response_text or "")
    assert "secret" not in (result.response_text or "").lower()
    assert "traceback" not in (result.response_text or "").lower()


def test_service_exception_returns_fixed_telegram_error(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")

    def boom(**kwargs):
        raise RuntimeError("/app/private/path token=abc traceback")

    result = handle_master_command_text(
        text="/master run image",
        telegram_user_id=1001,
        chat_id=55,
        runner=boom,
    )
    assert result.status == "ERROR"
    assert "Internal agent configuration failed." in (result.response_text or "")
    assert "/app" not in result.response_text
    assert "token" not in result.response_text.lower()
    assert "traceback" not in result.response_text.lower()


def test_master_on_ai_command_uses_numbered_agent_control(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    calls: list[tuple[str, bool]] = []

    def fake_toggle(number: str, enabled: bool) -> dict:
        calls.append((number, enabled))
        return {
            "number": int(number),
            "agent_key": "ai_blog_agent",
            "display_name": "AI Blog Agent",
            "enabled": enabled,
        }

    monkeypatch.setattr(
        "services.telegram_master_ai_control.set_ai_agent_enabled_by_number",
        fake_toggle,
    )
    result = handle_master_command_text(
        text="/master on ai 1",
        telegram_user_id=1001,
        chat_id=55,
    )

    assert result.status == "OK"
    assert calls == [("1", True)]
    assert "AI 1 ON" in (result.response_text or "")
    assert "token" not in (result.response_text or "").lower()


def test_signal_bot_does_not_replace_reply_agent_except_master_suppression(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    ignored = try_handle_telegram_update(update("hello"), bot_role=SIGNAL_BOT)
    assert ignored.handled is False

    sent: list[tuple[int | str, str]] = []
    handled = try_handle_telegram_update(
        update("/master help"),
        bot_role=SIGNAL_BOT,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    assert handled.handled is True
    assert handled.status == "IGNORED_WRONG_BOT"
    assert sent == []



def test_master_ai_chat_memory_keeps_recent_same_chat_context(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    prompts: list[str] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control.generate_master_ai_reply",
        lambda prompt: prompts.append(prompt) or f"reply-{len(prompts)}",
    )
    monkeypatch.setattr(
        "services.telegram_master_ai_control._MASTER_CHAT_MEMORY",
        {},
    )

    first = handle_master_command_text(
        text="Mera naam Manish hai.",
        telegram_user_id=1001,
        chat_id=501,
    )
    second = handle_master_command_text(
        text="Mera naam kya hai?",
        telegram_user_id=1001,
        chat_id=501,
    )

    assert first.status == "AI_CHAT_RESPONSE"
    assert second.status == "AI_CHAT_RESPONSE"
    assert prompts[0] == "Mera naam Manish hai."
    assert "User: Mera naam Manish hai." in prompts[1]
    assert "MASTER AI: reply-1" in prompts[1]
    assert prompts[1].endswith("User: Mera naam kya hai?")


def test_master_ai_chat_memory_is_isolated_per_chat(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    prompts: list[str] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control.generate_master_ai_reply",
        lambda prompt: prompts.append(prompt) or "SAFE_REPLY",
    )
    monkeypatch.setattr(
        "services.telegram_master_ai_control._MASTER_CHAT_MEMORY",
        {},
    )

    handle_master_command_text(
        text="Private project detail alpha.",
        telegram_user_id=1001,
        chat_id=601,
    )
    handle_master_command_text(
        text="Hello from another chat.",
        telegram_user_id=1001,
        chat_id=602,
    )

    assert prompts[1] == "Hello from another chat."
    assert "alpha" not in prompts[1]


def test_master_ai_chat_memory_never_bypasses_signal_approval(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    chat_calls: list[str] = []
    runner_calls: list[dict] = []
    monkeypatch.setattr(
        "services.telegram_master_ai_control.generate_master_ai_reply",
        lambda prompt: chat_calls.append(prompt) or "SAFE_REPLY",
    )
    monkeypatch.setattr(
        "services.telegram_master_ai_control._MASTER_CHAT_MEMORY",
        {},
    )

    handle_master_command_text(
        text="Mera naam Manish hai.",
        telegram_user_id=1001,
        chat_id=701,
    )
    result = handle_master_command_text(
        text="Signal band karo",
        telegram_user_id=1001,
        chat_id=701,
        runner=lambda **kwargs: runner_calls.append(kwargs),
    )

    assert result.status == "APPROVAL_REQUIRED"
    assert "Action: disable_signal_agent" in (result.response_text or "")
    assert "Executed: NO" in (result.response_text or "")
    assert len(chat_calls) == 1
    assert runner_calls == []
