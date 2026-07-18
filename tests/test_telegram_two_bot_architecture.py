"""Tests for separate Telegram Signal Bot and Master AI Admin Bot routing."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event
import urllib.error

import pytest

from services.master_orchestrator import OrchestrationProgress
from services.telegram_master_ai_control import (
    MASTER_AI_BOT,
    MASTER_AI_BOT_TOKEN_ENV,
    SAFE_TELEGRAM_ERROR,
    SIGNAL_BOT,
    SIGNAL_BOT_TOKEN_ENV,
    get_telegram_bot_token_env,
    handle_master_command_text,
    help_text,
    try_handle_telegram_update,
)
from services.telegram_master_ai_webhook import (
    MasterTelegramDeliveryError,
    _PENDING_MASTER_DELIVERIES,
    _SEEN_MASTER_UPDATE_KEYS,
    handle_master_telegram_webhook,
    handle_signal_telegram_master_command_guard,
    send_master_ai_bot_message,
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


def update(
    text: str,
    *,
    user_id: int = 1001,
    chat_id: int = 55,
    update_id: int | None = None,
) -> dict:
    payload = {
        "message": {
            "text": text,
            "chat": {"id": chat_id},
            "from": {"id": user_id},
        }
    }
    if update_id is not None:
        payload["update_id"] = update_id
    return payload


@pytest.fixture(autouse=True)
def clear_master_webhook_delivery_state():
    _SEEN_MASTER_UPDATE_KEYS.clear()
    _PENDING_MASTER_DELIVERIES.clear()
    yield
    _SEEN_MASTER_UPDATE_KEYS.clear()
    _PENDING_MASTER_DELIVERIES.clear()


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


def test_master_help_invokes_sender(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    sent: list[tuple[int | str, str]] = []

    response = handle_master_telegram_webhook(
        update("/master help", update_id=5001),
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )

    assert response["ok"] is True
    assert response["status"] == "OK"
    assert sent == [(55, help_text())]


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_master_sender_rejects_telegram_http_errors(monkeypatch, status_code) -> None:
    monkeypatch.setattr(
        "services.telegram_master_ai_webhook._master_bot_token",
        lambda: "test-token",
    )

    def fail_request(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "https://api.telegram.invalid",
            status_code,
            "rejected",
            None,
            None,
        )

    monkeypatch.setattr(
        "services.telegram_master_ai_webhook.urllib.request.urlopen",
        fail_request,
    )

    with pytest.raises(RuntimeError, match="Telegram send failed"):
        send_master_ai_bot_message(55, "test")


def test_master_sender_rejects_timeout(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.telegram_master_ai_webhook._master_bot_token",
        lambda: "test-token",
    )

    def timeout(*_args, **_kwargs):
        raise TimeoutError

    monkeypatch.setattr(
        "services.telegram_master_ai_webhook.urllib.request.urlopen",
        timeout,
    )

    with pytest.raises(RuntimeError, match="Telegram send failed"):
        send_master_ai_bot_message(55, "test")


@pytest.mark.parametrize("body", [b"not-json", b'{"ok": false}'])
def test_master_sender_rejects_malformed_or_unsuccessful_body(
    monkeypatch,
    body,
) -> None:
    monkeypatch.setattr(
        "services.telegram_master_ai_webhook._master_bot_token",
        lambda: "test-token",
    )

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return body

    monkeypatch.setattr(
        "services.telegram_master_ai_webhook.urllib.request.urlopen",
        lambda *_args, **_kwargs: Response(),
    )

    with pytest.raises(RuntimeError, match="Telegram send failed"):
        send_master_ai_bot_message(55, "test")


def test_failed_delivery_retry_reuses_response_without_rerunning(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner = FakeRunner()
    attempts = 0
    sent: list[tuple[int | str, str]] = []
    telegram_update = update("/master run blog", update_id=5002)

    def flaky_sender(chat_id, text):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("delivery failed")
        sent.append((chat_id, text))

    with pytest.raises(MasterTelegramDeliveryError):
        handle_master_telegram_webhook(
            telegram_update,
            runner=runner,
            sender=flaky_sender,
        )

    response = handle_master_telegram_webhook(
        telegram_update,
        runner=runner,
        sender=flaky_sender,
    )

    assert response["ok"] is True
    assert len(runner.calls) == 1
    assert len(sent) == 1


def test_successful_duplicate_update_stays_suppressed(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    sent: list[tuple[int | str, str]] = []
    telegram_update = update("/master help", update_id=5003)

    first = handle_master_telegram_webhook(
        telegram_update,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    duplicate = handle_master_telegram_webhook(
        telegram_update,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )

    assert first["ok"] is True
    assert duplicate["duplicate"] is True
    assert duplicate["status"] == "DUPLICATE_IGNORED"
    assert len(sent) == 1


def test_concurrent_duplicate_executes_runner_once(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    runner_entered = Event()
    release_runner = Event()
    second_started = Event()
    calls: list[int] = []
    sent: list[tuple[int | str, str]] = []
    telegram_update = update("/master run blog", update_id=5004)

    def blocking_runner(**_kwargs):
        calls.append(1)
        runner_entered.set()
        assert release_runner.wait(timeout=2)
        return OrchestrationProgress(
            run_id=102,
            task_id=203,
            status="COMPLETED",
            completed_steps=1,
            total_steps=1,
        )

    def invoke():
        return handle_master_telegram_webhook(
            telegram_update,
            runner=blocking_runner,
            sender=lambda chat_id, text: sent.append((chat_id, text)),
        )

    def invoke_second():
        second_started.set()
        return invoke()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(invoke)
        assert runner_entered.wait(timeout=2)
        second = pool.submit(invoke_second)
        assert second_started.wait(timeout=2)
        release_runner.set()
        responses = [first.result(timeout=2), second.result(timeout=2)]

    assert calls == [1]
    assert len(sent) == 1
    assert sorted(response.get("duplicate", False) for response in responses) == [
        False,
        True,
    ]


def test_equal_update_id_is_namespaced_by_source_and_bot_role(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    telegram_update = update("/master help", update_id=5005)
    sent: list[tuple[int | str, str]] = []

    dedicated = handle_master_telegram_webhook(
        telegram_update,
        bot_role=MASTER_AI_BOT,
        webhook_source="/webhooks/telegram/master",
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    generic = handle_master_telegram_webhook(
        telegram_update,
        bot_role=MASTER_AI_BOT,
        webhook_source="/webhooks/telegram",
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    signal_role = handle_master_telegram_webhook(
        telegram_update,
        bot_role=SIGNAL_BOT,
        webhook_source="/webhooks/telegram/master",
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )

    assert dedicated.get("duplicate") is None
    assert generic.get("duplicate") is None
    assert signal_role.get("duplicate") is None
    assert signal_role["status"] == "IGNORED_WRONG_BOT"
    assert len(sent) == 2


def test_same_chat_different_sender_fallback_keys_do_not_collide(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_IDS", "1001,1002")
    sent: list[tuple[int | str, str]] = []

    first = handle_master_telegram_webhook(
        update("/master help", user_id=1001),
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    second = handle_master_telegram_webhook(
        update("/master help", user_id=1002),
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )

    assert first.get("duplicate") is None
    assert second.get("duplicate") is None
    assert len(sent) == 2


def test_different_chat_never_receives_pending_cached_response(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    first_update = update("/master help", chat_id=55, update_id=5006)
    second_update = update("/master help", chat_id=66, update_id=5006)
    sent: list[tuple[int | str, str]] = []

    with pytest.raises(MasterTelegramDeliveryError):
        handle_master_telegram_webhook(
            first_update,
            sender=lambda *_args: (_ for _ in ()).throw(
                RuntimeError("delivery failed")
            ),
        )

    handle_master_telegram_webhook(
        second_update,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    handle_master_telegram_webhook(
        first_update,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )

    assert [chat_id for chat_id, _ in sent] == [66, 55]


def test_pending_retry_revalidates_sender_identity_before_reuse(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_ID", "1001")
    monkeypatch.setenv("TELEGRAM_ADMIN_USER_IDS", "1001,1002")
    calls: list[int] = []
    sent: list[tuple[int | str, str]] = []

    def counting_runner(**_kwargs):
        run_id = len(calls) + 1
        calls.append(run_id)
        return OrchestrationProgress(
            run_id=run_id,
            task_id=run_id,
            status="COMPLETED",
            completed_steps=1,
            total_steps=1,
        )

    first_update = update(
        "/master run blog",
        user_id=1001,
        update_id=5007,
    )
    colliding_update = update(
        "/master run blog",
        user_id=1002,
        update_id=5007,
    )

    with pytest.raises(MasterTelegramDeliveryError):
        handle_master_telegram_webhook(
            first_update,
            runner=counting_runner,
            sender=lambda *_args: (_ for _ in ()).throw(
                RuntimeError("delivery failed")
            ),
        )
    handle_master_telegram_webhook(
        colliding_update,
        runner=counting_runner,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )
    handle_master_telegram_webhook(
        first_update,
        runner=counting_runner,
        sender=lambda chat_id, text: sent.append((chat_id, text)),
    )

    assert calls == [1, 2]
    assert "Run: #2" in sent[0][1]
    assert "Run: #1" in sent[1][1]
