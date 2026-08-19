"""Real PostgreSQL validation for the isolated Phase 1.5 admin environment."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

import bcrypt
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services import admin_auth_api, admin_auth_service


ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("TEST_ADMIN_DATABASE_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_ADMIN_DATABASE_URL must point to isolated PostgreSQL",
)

TEST_PASSWORD = "Staging-only-password-42!"
TEST_SETTINGS = SimpleNamespace(
    jwt_secret="phase-1-5-isolated-jwt-secret-value-000000000000",
    jwt_issuer="phase-1-5-staging",
    admin_bff_shared_secret="phase-1-5-bff-shared-secret-value-000000000000",
    admin_session_ttl_minutes=15,
    admin_login_window_seconds=900,
    admin_login_max_attempts=5,
)

USERS = (
    (101, "approved-admin@phase15.invalid", "ADMIN", True, "APPROVED"),
    (102, "normal-user@phase15.invalid", "USER", True, "APPROVED"),
    (103, "blocked-admin@phase15.invalid", "ADMIN", True, "BLOCKED"),
    (104, "pending-admin@phase15.invalid", "ADMIN", True, "PENDING"),
    (105, "unverified-admin@phase15.invalid", "ADMIN", False, "APPROVED"),
)


@pytest.fixture(scope="module")
def engine():
    database_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    forward = (ROOT / "migrations/014_admin_auth_foundation.sql").read_text()
    rollback = (ROOT / "migrations/014_admin_auth_foundation.rollback.sql").read_text()
    with database_engine.begin() as connection:
        connection.exec_driver_sql(
            """
            DO $$ BEGIN CREATE ROLE anon; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            DO $$ BEGIN CREATE ROLE authenticated; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            CREATE TABLE IF NOT EXISTS public.users (
                id BIGINT PRIMARY KEY,
                email TEXT NOT NULL,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'USER',
                email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                approval_status TEXT NOT NULL DEFAULT 'PENDING',
                last_login_at TIMESTAMPTZ
            );
            """
        )
        connection.exec_driver_sql(forward)
        connection.exec_driver_sql(rollback)
        remaining_after_rollback = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM pg_tables
                WHERE schemaname = 'public' AND tablename LIKE 'admin_%'
                """
            )
        ).scalar_one()
        assert remaining_after_rollback == 0
        connection.exec_driver_sql(forward)
    yield database_engine
    with database_engine.begin() as connection:
        connection.exec_driver_sql(rollback)
        connection.exec_driver_sql("DROP TABLE IF EXISTS public.users")
    database_engine.dispose()


@pytest.fixture(autouse=True)
def isolated_rows(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    password_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE public.admin_auth_audit_events, "
                "public.admin_login_attempts, public.admin_sessions, public.users"
            )
        )
        for user_id, email, role, verified, approval in USERS:
            connection.execute(
                text(
                    """
                    INSERT INTO public.users (
                        id, email, password_hash, role,
                        email_verified, approval_status
                    ) VALUES (
                        :id, :email, :password_hash, :role,
                        :verified, :approval
                    )
                    """
                ),
                {
                    "id": user_id,
                    "email": email,
                    "password_hash": password_hash,
                    "role": role,
                    "verified": verified,
                    "approval": approval,
                },
            )

    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    @contextmanager
    def isolated_session_scope() -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(admin_auth_service, "get_settings", lambda: TEST_SETTINGS)
    monkeypatch.setattr(admin_auth_service, "session_scope", isolated_session_scope)


def _login(email: str, *, ip: str = "192.0.2.10"):
    return admin_auth_service.login_admin(
        email=email,
        password=TEST_PASSWORD,
        ip_address=ip,
        user_agent="phase-1.5-integration-test",
        request_id="phase-1.5-request",
    )


def test_migration_objects_indexes_constraints_and_rls(engine) -> None:
    with engine.connect() as connection:
        tables = set(
            connection.execute(
                text(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public' AND tablename LIKE 'admin_%'
                    """
                )
            ).scalars()
        )
        indexes = set(
            connection.execute(
                text(
                    """
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public' AND tablename LIKE 'admin_%'
                    """
                )
            ).scalars()
        )
        foreign_keys = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM pg_constraint
                WHERE contype = 'f'
                  AND conrelid IN (
                    'public.admin_sessions'::regclass,
                    'public.admin_auth_audit_events'::regclass
                  )
                """
            )
        ).scalar_one()
        check_constraints = set(
            connection.execute(
                text(
                    """
                    SELECT conname FROM pg_constraint
                    WHERE contype = 'c'
                      AND conrelid = 'public.admin_auth_audit_events'::regclass
                    """
                )
            ).scalars()
        )
        rls_tables = set(
            connection.execute(
                text(
                    """
                    SELECT relname FROM pg_class
                    WHERE relrowsecurity = TRUE
                      AND relname LIKE 'admin_%'
                    """
                )
            ).scalars()
        )
        expiry_type = connection.execute(
            text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'admin_sessions'
                  AND column_name = 'expires_at'
                """
            )
        ).scalar_one()

    assert tables == {
        "admin_sessions",
        "admin_login_attempts",
        "admin_auth_audit_events",
    }
    assert {
        "admin_sessions_user_active_idx",
        "admin_sessions_expiry_idx",
        "admin_login_attempts_email_window_idx",
        "admin_login_attempts_ip_window_idx",
        "admin_auth_audit_user_created_idx",
        "admin_auth_audit_event_created_idx",
    }.issubset(indexes)
    assert foreign_keys == 2
    assert "admin_auth_audit_outcome_check" in check_constraints
    assert rls_tables == tables
    assert expiry_type == "timestamp with time zone"


def test_approved_admin_login_session_expiry_revocation_and_logout(engine) -> None:
    issued = _login("approved-admin@phase15.invalid")
    identity = admin_auth_service.validate_admin_session(issued.token)
    assert identity.role == "ADMIN"
    assert identity.email == "approved-admin@phase15.invalid"

    claims = admin_auth_service._decode_admin_token(
        issued.token,
        verify_expiration=True,
    )
    token_hash = admin_auth_service._identifier_hash(
        claims["jti"],
        TEST_SETTINGS.jwt_secret,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE public.admin_sessions "
                "SET expires_at = :expired WHERE token_id_hash = :token_hash"
            ),
            {
                "expired": datetime.now(timezone.utc) - timedelta(seconds=1),
                "token_hash": token_hash,
            },
        )
    with pytest.raises(admin_auth_service.AdminSessionInvalid):
        admin_auth_service.validate_admin_session(issued.token)

    current = _login("approved-admin@phase15.invalid", ip="192.0.2.11")
    admin_auth_service.logout_admin_session(
        token=current.token,
        ip_address="192.0.2.11",
        user_agent="phase-1.5-integration-test",
        request_id="logout-request",
    )
    with pytest.raises(admin_auth_service.AdminSessionInvalid):
        admin_auth_service.validate_admin_session(current.token)


@pytest.mark.parametrize(
    "email",
    [
        "normal-user@phase15.invalid",
        "blocked-admin@phase15.invalid",
        "pending-admin@phase15.invalid",
        "unverified-admin@phase15.invalid",
    ],
)
def test_non_admin_blocked_pending_and_unverified_are_forbidden(email: str) -> None:
    with pytest.raises(admin_auth_service.AdminAccessForbidden):
        _login(email, ip=f"192.0.2.{USERS.index(next(row for row in USERS if row[1] == email)) + 20}")


def test_real_database_rate_limit_and_sanitized_audit(engine) -> None:
    email = "missing-account@phase15.invalid"
    for attempt in range(TEST_SETTINGS.admin_login_max_attempts):
        with pytest.raises(admin_auth_service.AdminInvalidCredentials):
            admin_auth_service.login_admin(
                email=email,
                password=f"incorrect-{attempt}",
                ip_address="198.51.100.25",
                user_agent="phase-1.5-rate-test",
                request_id=f"attempt-{attempt}",
            )
    with pytest.raises(admin_auth_service.AdminLoginRateLimited):
        admin_auth_service.login_admin(
            email=email,
            password="final-incorrect-password",
            ip_address="198.51.100.25",
            user_agent="phase-1.5-rate-test",
            request_id="rate-limited",
        )

    with engine.connect() as connection:
        attempts = connection.execute(
            text("SELECT COUNT(*) FROM public.admin_login_attempts")
        ).scalar_one()
        audit_rows = connection.execute(
            text(
                "SELECT event_type, outcome, details, ip_hash, user_agent_hash "
                "FROM public.admin_auth_audit_events"
            )
        ).mappings().all()
    serialized = json.dumps([dict(row) for row in audit_rows], default=str)
    assert attempts == TEST_SETTINGS.admin_login_max_attempts
    assert len(audit_rows) == TEST_SETTINGS.admin_login_max_attempts + 1
    assert TEST_PASSWORD not in serialized
    assert "final-incorrect-password" not in serialized
    assert email not in serialized
    assert TEST_SETTINGS.jwt_secret not in serialized
    assert TEST_SETTINGS.admin_bff_shared_secret not in serialized
    assert all(len(row["ip_hash"]) == 64 for row in audit_rows)
    assert all(len(row["user_agent_hash"]) == 64 for row in audit_rows)


def test_fastapi_requires_real_bff_secret_and_ignores_browser_role() -> None:
    app = FastAPI()
    app.include_router(admin_auth_api.router)
    client = TestClient(app)

    denied = client.get(
        "/admin/auth/session?role=ADMIN",
        headers={"Authorization": "Bearer attacker-token"},
    )
    assert denied.status_code == 403

    issued = _login("approved-admin@phase15.invalid", ip="203.0.113.44")
    allowed = client.get(
        "/admin/auth/session?role=USER",
        headers={
            "Authorization": f"Bearer {issued.token}",
            "X-Admin-BFF-Key": TEST_SETTINGS.admin_bff_shared_secret,
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["user"]["role"] == "ADMIN"
