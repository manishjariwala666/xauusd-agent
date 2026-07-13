from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import bcrypt
import jwt
import pytest

from services import admin_auth_api, admin_auth_service


ROOT = Path(__file__).resolve().parents[1]
BFF_HEADERS = {"X-Admin-BFF-Key": "b" * 40}
IDENTITY = admin_auth_service.AdminIdentity(
    user_id=7,
    email="admin@example.test",
    role="ADMIN",
)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(admin_auth_api, "verify_bff_secret", lambda _: None)
    app = FastAPI()
    app.include_router(admin_auth_api.router)
    return TestClient(app)


def test_admin_login_returns_session_only_to_authorized_bff(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issued = admin_auth_service.IssuedAdminSession(
        token="server-only-access-token",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        identity=IDENTITY,
    )
    monkeypatch.setattr(admin_auth_api, "login_admin", lambda **_: issued)

    response = client.post(
        "/admin/auth/login",
        headers=BFF_HEADERS,
        json={"email": "admin@example.test", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"
    assert response.json()["access_token"] == "server-only-access-token"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "failure",
    [
        admin_auth_service.AdminInvalidCredentials("invalid"),
        admin_auth_service.AdminAccessForbidden("blocked, pending, user, or unverified"),
    ],
)
def test_login_denies_invalid_or_ineligible_accounts(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    def deny(**_: object) -> None:
        raise failure

    monkeypatch.setattr(admin_auth_api, "login_admin", deny)
    response = client.post(
        "/admin/auth/login",
        headers=BFF_HEADERS,
        json={"email": "person@example.test", "password": "not-returned"},
    )
    assert response.status_code in {401, 403}
    assert "not-returned" not in response.text


def test_rate_limited_login_is_safe(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def limited(**_: object) -> None:
        raise admin_auth_service.AdminLoginRateLimited(300)

    monkeypatch.setattr(admin_auth_api, "login_admin", limited)
    response = client.post(
        "/admin/auth/login",
        headers=BFF_HEADERS,
        json={"email": "admin@example.test", "password": "guess"},
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"
    assert "guess" not in response.text


def test_direct_protected_call_requires_bff_and_bearer(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = client.get("/admin/auth/session", headers=BFF_HEADERS)
    assert response.status_code == 401

    def reject(_: str | None) -> None:
        raise admin_auth_service.AdminAccessForbidden("not trusted")

    monkeypatch.setattr(admin_auth_api, "verify_bff_secret", reject)
    response = client.get(
        "/admin/auth/session",
        headers={"Authorization": "Bearer attacker-controlled"},
    )
    assert response.status_code == 403


def test_expired_session_and_browser_role_manipulation_cannot_grant_access(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def expired(_: str) -> None:
        raise admin_auth_service.AdminSessionInvalid("expired")

    monkeypatch.setattr(admin_auth_api, "validate_admin_session", expired)
    response = client.get(
        "/admin/dashboard/summary?role=ADMIN",
        headers={**BFF_HEADERS, "Authorization": "Bearer expired-token"},
    )
    assert response.status_code == 401


def test_backend_revalidates_identity_for_each_protected_endpoint(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def validate(token: str) -> admin_auth_service.AdminIdentity:
        seen.append(token)
        return IDENTITY

    monkeypatch.setattr(admin_auth_api, "validate_admin_session", validate)
    headers = {**BFF_HEADERS, "Authorization": "Bearer persisted-token"}
    session = client.get("/admin/auth/session", headers=headers)
    dashboard = client.get("/admin/dashboard/summary", headers=headers)
    assert session.status_code == 200
    assert dashboard.status_code == 200
    assert dashboard.json()["cards"][0]["value"] == "Not loaded"
    assert seen == ["persisted-token", "persisted-token"]


def test_logout_revokes_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revoked: list[str] = []

    def logout(**kwargs: str) -> None:
        revoked.append(kwargs["token"])

    monkeypatch.setattr(admin_auth_api, "logout_admin_session", logout)
    response = client.post(
        "/admin/auth/logout",
        headers={**BFF_HEADERS, "Authorization": "Bearer live-token"},
    )
    assert response.status_code == 204
    assert revoked == ["live-token"]


def test_password_check_preserves_bcrypt_compatibility() -> None:
    password_hash = bcrypt.hashpw(b"compatible-password", bcrypt.gensalt())
    assert admin_auth_service._password_matches("compatible-password", password_hash)
    assert not admin_auth_service._password_matches("wrong-password", password_hash)
    assert not admin_auth_service._password_matches("x" * 73, password_hash)


def test_expired_admin_jwt_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        jwt_secret="s" * 40,
        jwt_issuer="phase-one-tests",
    )
    monkeypatch.setattr(admin_auth_service, "get_settings", lambda: settings)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "7",
            "jti": "expired-id",
            "typ": "admin_session",
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=5),
            "iss": settings.jwt_issuer,
            "aud": "admin-web",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(admin_auth_service.AdminSessionInvalid):
        admin_auth_service._decode_admin_token(token, verify_expiration=True)


def test_phase_one_migration_is_additive_and_has_manual_rollback() -> None:
    forward = (ROOT / "migrations/014_admin_auth_foundation.sql").read_text()
    rollback = (ROOT / "migrations/014_admin_auth_foundation.rollback.sql").read_text()
    migration_service = (ROOT / "services/migration_service.py").read_text()

    assert "CREATE TABLE IF NOT EXISTS public.admin_sessions" in forward
    assert "ENABLE ROW LEVEL SECURITY" in forward
    assert "DROP TABLE" not in forward.upper()
    assert "DROP TABLE IF EXISTS public.admin_sessions" in rollback
    assert "014_admin_auth_foundation.sql" not in migration_service


def test_existing_streamlit_authentication_file_is_not_replaced() -> None:
    streamlit_auth = (ROOT / "core/auth.py").read_text()
    assert "def authenticate_credentials" in streamlit_auth
    assert "bcrypt.checkpw" in streamlit_auth
    assert "st.session_state" in streamlit_auth
