"""Tests for Telegram Master AI admin command control."""

from __future__ import annotations

from dataclasses import dataclass

from services.master_orchestrator import OrchestrationProgress
from services.telegram_master_ai_control import (
    MASTER_AI_BOT,
    SAFE_TELEGRAM_ERROR,
    SIGNAL_BOT,
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
    assert not is_master_command("hello")
    assert parse_master_command("/master run blog") == ("run", "blog")
    assert parse_master_command("/master") == ("help", None)


def test_master_command_parser_accepts_numbered_ai_toggles() -> None:
    assert parse_master_command("/master list ai") == ("list_ai", None)
    assert parse_master_command("/master on ai 1") == ("on", "1")
    assert parse_master_command("/master off ai 3") == ("off", "3")
    assert parse_master_command("/master enable agent 6") == ("on", "6")


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
    assert "Latest blog URL" in (result.response_text or "") or "Blog page" in (
        result.response_text or ""
    )


def test_master_bot_replies_helpfully_to_unknown_admin_text(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    result = try_handle_telegram_update(
        update("hello bhai", user_id=1001, chat_id=55),
        bot_role=MASTER_AI_BOT,
        runner=runner,
    )

    assert result.handled is True
    assert result.status == "IGNORED_NON_MASTER_COMMAND"
    assert "Master AI ready" in (result.response_text or "")
    assert runner.calls == []


def test_status_command_returns_safe_summary(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    result = handle_master_command_text(
        text="/master status",
        telegram_user_id=1001,
        chat_id=55,
        status_loader=lambda limit: [
            {
                "run_id": 5,
                "task_type": "BLOG",
                "status": "RUNNING",
                "completed_steps": 1,
                "total_steps": 3,
                "safe_error": "/secret/path/token traceback",
            }
        ],
    )
    assert "#5" in (result.response_text or "")
    assert "BLOG" in (result.response_text or "")
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
    assert result.response_text == SAFE_TELEGRAM_ERROR
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
