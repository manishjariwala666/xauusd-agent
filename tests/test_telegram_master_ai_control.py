"""Tests for Telegram Master AI admin command control."""

from __future__ import annotations

from dataclasses import dataclass

from services.master_orchestrator import OrchestrationProgress
from services.telegram_master_ai_control import (
    SAFE_TELEGRAM_ERROR,
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


def test_master_command_parser_accepts_bot_suffix() -> None:
    assert is_master_command("/master status")
    assert is_master_command("/master@my_bot status")
    assert not is_master_command("hello")
    assert parse_master_command("/master run blog") == ("run", "blog")
    assert parse_master_command("/master") == ("help", None)


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


def test_run_blog_routes_to_master_orchestrator(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    result = handle_master_command_text(
        text="/master run blog",
        telegram_user_id=1001,
        chat_id=55,
        runner=runner,
    )
    assert result.handled is True
    assert result.run_id == 42
    assert result.task_type == "BLOG"
    assert runner.calls[0].source == "TELEGRAM_MASTER_COMMAND"
    assert runner.calls[0].requested_by is None
    assert runner.calls[0].input_payload["telegram_target"] == "blog"
    assert "token" not in str(result.response_text).lower()


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


def test_try_handle_update_does_not_replace_reply_agent(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    ignored = try_handle_telegram_update({"message": {"text": "hello", "chat": {"id": 1}, "from": {"id": 1001}}})
    assert ignored.handled is False

    sent: list[tuple[int | str, str]] = []
    handled = try_handle_telegram_update(
        {"message": {"text": "/master help", "chat": {"id": 1}, "from": {"id": 1001}}},
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    assert handled.handled is True
    assert sent and sent[0][0] == 1
