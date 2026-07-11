"""Offline webhook parsing tests."""

from backend import (
    health,
    ready,
    _should_route_generic_telegram_update_to_master,
    _telegram_media,
    _configure_telegram_webhook,
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


def test_generic_telegram_webhook_routes_master_ai_fallbacks() -> None:
    assert _should_route_generic_telegram_update_to_master(
        {"message": {"text": "/master run blog"}}
    )
    assert _should_route_generic_telegram_update_to_master(
        {"message": {"text": "xauusd buy or sell today par SEO blog banao"}}
    )
    assert not _should_route_generic_telegram_update_to_master(
        {"message": {"text": "hello support"}}
    )


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


def test_telegram_webhook_registration_uses_api_domain(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class Settings:
        public_api_url = "https://api.venusrealm.net"
        backend_base_url = "https://xauusd-agent-api-production.up.railway.app"
        telegram_webhook_secret = "secret-value"
        telegram_bot_token = "signal-token"
        master_ai_telegram_bot_token = "master-token"

    def fake_register_single_telegram_webhook(**kwargs: object) -> None:
        calls.append((str(kwargs["bot_name"]), str(kwargs["public_api_url"])))

    monkeypatch.setattr("backend.get_settings", lambda: Settings())
    monkeypatch.setattr(
        "backend._register_single_telegram_webhook",
        fake_register_single_telegram_webhook,
    )

    _configure_telegram_webhook()

    assert calls == [
        ("signal", "https://api.venusrealm.net"),
        ("master_ai", "https://api.venusrealm.net"),
    ]
