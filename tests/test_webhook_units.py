"""Offline webhook parsing tests."""

from backend import (
    health,
    ready,
    _telegram_media,
    _telegram_webhook_payload,
    _telegram_webhook_secret_matches,
    _whatsapp_content,
)


def test_telegram_photo_metadata() -> None:
    assert _telegram_media(
        {"photo": [{"file_id": "small"}, {"file_id": "large"}]}
    ) == {"type": "photo", "file_id": "large"}


def test_health_is_lightweight_liveness() -> None:
    assert health() == {"status": "healthy"}


def test_ready_checks_database(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSession:
        def execute(self, statement: object) -> None:
            calls.append(str(statement))

    class FakeScope:
        def __enter__(self) -> FakeSession:
            return FakeSession()

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr("backend.session_scope", lambda: FakeScope())

    assert ready() == {"status": "ready", "database": "ok"}
    assert calls


def test_whatsapp_text_content() -> None:
    body, media = _whatsapp_content(
        {"type": "text", "text": {"body": "hello"}}
    )
    assert body == "hello"
    assert media == {}


def test_telegram_webhook_secret_matching_is_strict() -> None:
    assert _telegram_webhook_secret_matches("secret-value", "secret-value")
    assert _telegram_webhook_secret_matches(" secret-value ", "secret-value")
    assert not _telegram_webhook_secret_matches(None, "secret-value")
    assert not _telegram_webhook_secret_matches("", "secret-value")
    assert not _telegram_webhook_secret_matches("wrong", "secret-value")
    assert not _telegram_webhook_secret_matches("secret-value", "")


def test_telegram_webhook_payload_uses_configured_secret() -> None:
    payload = _telegram_webhook_payload(
        "https://xauusd-agent-api-production.up.railway.app/",
        "secret-value",
    )

    assert payload == {
        "url": (
            "https://xauusd-agent-api-production.up.railway.app"
            "/webhooks/telegram"
        ),
        "secret_token": "secret-value",
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": False,
    }
