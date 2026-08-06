from __future__ import annotations

from types import SimpleNamespace

import pytest

from services import admin_auth_service


def _settings(
    *,
    app_env: str = "development",
    local_admin_preview: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        app_env=app_env,
        local_admin_preview=local_admin_preview,
        local_admin_preview_email="preview@localhost.invalid",
        local_admin_preview_password="local-preview-password",
        admin_session_ttl_minutes=15,
        jwt_secret="j" * 48,
        jwt_issuer="venusrealm-local-tests",
    )


def test_local_preview_is_disabled_without_both_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(
            app_env="production",
            local_admin_preview=True,
        ),
    )

    assert admin_auth_service.local_admin_preview_enabled() is False

    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(
            app_env="development",
            local_admin_preview=False,
        ),
    )

    assert admin_auth_service.local_admin_preview_enabled() is False


def test_local_preview_requires_loopback_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(),
    )

    with pytest.raises(admin_auth_service.AdminAccessForbidden):
        admin_auth_service.login_local_admin_preview(
            email="preview@localhost.invalid",
            password="local-preview-password",
            ip_address="192.168.31.6",
        )


def test_local_preview_rejects_wrong_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(),
    )

    with pytest.raises(admin_auth_service.AdminInvalidCredentials):
        admin_auth_service.login_local_admin_preview(
            email="preview@localhost.invalid",
            password="wrong-password",
            ip_address="127.0.0.1",
        )


def test_local_preview_session_works_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(),
    )

    def database_must_not_be_used():
        raise AssertionError("Database must not be used for local preview auth.")

    monkeypatch.setattr(
        admin_auth_service,
        "session_scope",
        database_must_not_be_used,
    )

    issued = admin_auth_service.login_local_admin_preview(
        email="preview@localhost.invalid",
        password="local-preview-password",
        ip_address="127.0.0.1",
    )

    identity = admin_auth_service.validate_admin_session(
        issued.token,
    )

    assert identity.user_id == -1
    assert identity.email == "preview@localhost.invalid"
    assert identity.role == "ADMIN"


def test_preview_token_is_rejected_when_preview_mode_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(),
    )

    issued = admin_auth_service.login_local_admin_preview(
        email="preview@localhost.invalid",
        password="local-preview-password",
        ip_address="::1",
    )

    monkeypatch.setattr(
        admin_auth_service,
        "get_settings",
        lambda: _settings(local_admin_preview=False),
    )

    with pytest.raises(admin_auth_service.AdminSessionInvalid):
        admin_auth_service.validate_admin_session(
            issued.token,
        )
