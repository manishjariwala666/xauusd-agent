"""Tests for separate Telegram Signal Bot and Master AI Admin Bot routing."""

from __future__ import annotations

from dataclasses import dataclass

from services.master_orchestrator import OrchestrationProgress
from services.telegram_master_ai_control import (
    MASTER_AI_BOT,
    MASTER_AI_BOT_TOKEN_ENV,
    SAFE_TELEGRAM_ERROR,
    SIGNAL_BOT,
    SIGNAL_BOT_TOKEN_ENV,
    get_telegram_bot_token_env,
    handle_master_command_text,
    try_handle_telegram_update,
)
from services.telegram_master_ai_webhook import (
    handle_master_telegram_webhook,
    handle_signal_telegram_master_command_guard,
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
            run_id=101,
            task_id=202,
            status="COMPLETED",
            completed_steps=3,
            total_steps=3,
        )


def update(text: str, *, user_id: int = 1001, chat_id: int = 55) -> dict:
    return {"message": {"text": text, "chat": {"id": chat_id}, "from": {"id": user_id}}}


def test_token_env_names_are_separate() -> None:
    assert get_telegram_bot_token_env(SIGNAL_BOT) == SIGNAL_BOT_TOKEN_ENV
    assert get_telegram_bot_token_env(MASTER_AI_BOT) == MASTER_AI_BOT_TOKEN_ENV
    assert SIGNAL_BOT_TOKEN_ENV == "TELEGRAM_BOT_TOKEN"
    assert MASTER_AI_BOT_TOKEN_ENV == "MASTER_AI_TELEGRAM_BOT_TOKEN"


def test_signal_bot_silently_ignores_master_commands(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    result = try_handle_telegram_update(
        update("/master status"),
        bot_role=SIGNAL_BOT,
        runner=runner,
    )
    assert result.handled is True
    assert result.status == "IGNORED_WRONG_BOT"
    assert result.response_text is None
    assert runner.calls == []


def test_signal_bot_non_master_messages_remain_backward_compatible() -> None:
    result = try_handle_telegram_update(update("hello support"), bot_role=SIGNAL_BOT)
    assert result.handled is False
    assert result.status == "PASS_TO_SIGNAL_BOT"


def test_master_bot_routes_master_command_to_orchestrator(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    sent: list[tuple[int | str, str]] = []
    result = try_handle_telegram_update(
        update("/master run blog"),
        bot_role=MASTER_AI_BOT,
        runner=runner,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    assert result.handled is True
    assert result.run_id == 101
    assert result.task_type == "BLOG"
    assert runner.calls[0].source == "TELEGRAM_MASTER_COMMAND"
    assert runner.calls[0].input_payload["telegram_target"] == "blog"
    assert sent and "Master AI orchestration accepted" in sent[0][1]


def test_master_bot_does_not_process_public_buy_sell_signals(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    sent: list[tuple[int | str, str]] = []
    result = try_handle_telegram_update(
        update("BUY XAUUSD now"),
        bot_role=MASTER_AI_BOT,
        runner=runner,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    assert result.handled is True
    assert result.status == "IGNORED_NON_MASTER_COMMAND"
    assert "Master AI ready" in (result.response_text or "")
    assert runner.calls == []
    assert sent and "Master AI ready" in sent[0][1]


def test_master_commands_use_telegram_admin_user_id_only(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    monkeypatch.setenv("MASTER_AI_TELEGRAM_ADMIN_USER_ID", "9999")
    runner = FakeRunner()
    denied = handle_master_command_text(
        text="/master run image",
        telegram_user_id=9999,
        chat_id=55,
        runner=runner,
    )
    assert denied.status == "UNAUTHORIZED"
    assert runner.calls == []


def test_signal_webhook_guard_returns_early_for_master_command() -> None:
    response = handle_signal_telegram_master_command_guard(update("/master help"))
    assert response is not None
    assert response["bot"] == "signal"
    assert response["ignored"] is True


def test_signal_webhook_guard_allows_normal_messages() -> None:
    assert handle_signal_telegram_master_command_guard(update("normal user message")) is None


def test_master_webhook_returns_safe_error(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    sent: list[tuple[int | str, str]] = []

    def boom(**kwargs):
        raise RuntimeError("/app/private token=secret traceback")

    response = handle_master_telegram_webhook(
        update("/master run signal"),
        runner=boom,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    assert response["ok"] is True
    assert response["bot"] == "master_ai"
    assert sent[-1][1] == SAFE_TELEGRAM_ERROR
    assert "token" not in str(response).lower()
    assert "traceback" not in str(response).lower()
