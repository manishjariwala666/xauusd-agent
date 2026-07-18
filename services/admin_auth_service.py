"""Server-only authentication for the separate Next.js admin application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from typing import Any

import bcrypt
import jwt
from sqlalchemy import text

from config import get_settings
from core.database import session_scope


ROLE_ADMIN = "ADMIN"
STATUS_APPROVED = "APPROVED"
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DUMMY_PASSWORD_HASH = (
    b"$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxmZ5Nn0p9vQm2Q7b9YFf6M8K7e"
)


class AdminAuthError(RuntimeError):
    """Base class for safe admin authentication failures."""


class AdminAuthUnavailable(AdminAuthError):
    """Required server-side authentication configuration is unavailable."""


class AdminInvalidCredentials(AdminAuthError):
    """Credentials are invalid without revealing which value failed."""


class AdminAccessForbidden(AdminAuthError):
    """Credentials are valid but the account is not an approved admin."""


class AdminSessionInvalid(AdminAuthError):
    """The admin access session is missing, invalid, revoked, or expired."""


class AdminLoginRateLimited(AdminAuthError):
    """Too many failed login attempts were recorded in the active window."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many login attempts.")
        self.retry_after_seconds = max(1, int(retry_after_seconds))


@dataclass(frozen=True)
class AdminIdentity:
    """Database-verified admin identity safe to return to the BFF."""

    user_id: int
    email: str
    role: str


@dataclass(frozen=True)
class IssuedAdminSession:
    """Short-lived token returned only to the trusted Next.js BFF."""

    token: str
    expires_at: datetime
    identity: AdminIdentity


def verify_bff_secret(provided_secret: str | None) -> None:
    """Require a server-only shared secret before issuing or reading sessions."""
    expected = str(get_settings().admin_bff_shared_secret or "").strip()
    provided = str(provided_secret or "").strip()
    if not expected or len(expected) < 32:
        raise AdminAuthUnavailable("Admin BFF authentication is not configured.")
    if not provided or not hmac.compare_digest(provided, expected):
        raise AdminAccessForbidden("Admin BFF authorization failed.")


def login_admin(
    *,
    email: str,
    password: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> IssuedAdminSession:
    """Authenticate one approved administrator and persist a revocable session."""
    settings = get_settings()
    normalized_email = str(email or "").strip().lower()
    normalized_password = str(password or "")
    email_hash = _identifier_hash(normalized_email, settings.jwt_secret)
    ip_hash = _identifier_hash(ip_address, settings.jwt_secret)
    agent_hash = _identifier_hash(user_agent, settings.jwt_secret)

    with session_scope() as session:
        failures = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM public.admin_login_attempts
                WHERE succeeded = FALSE
                  AND attempted_at >= NOW() - make_interval(secs => :window_seconds)
                  AND (email_hash = :email_hash OR ip_hash = :ip_hash)
                """
            ),
            {
                "window_seconds": settings.admin_login_window_seconds,
                "email_hash": email_hash,
                "ip_hash": ip_hash,
            },
        ).scalar_one()
        if int(failures or 0) >= settings.admin_login_max_attempts:
            _record_audit(
                session,
                event_type="LOGIN_RATE_LIMITED",
                outcome="DENIED",
                request_id=request_id,
                ip_hash=ip_hash,
                user_agent_hash=agent_hash,
                details={"reason": "rate_limited"},
            )
            session.commit()
            raise AdminLoginRateLimited(settings.admin_login_window_seconds)

        user = session.execute(
            text(
                """
                SELECT id, email, password_hash, role,
                       email_verified, approval_status
                FROM public.users
                WHERE LOWER(email) = :email
                LIMIT 1
                """
            ),
            {"email": normalized_email},
        ).mappings().first()

        supplied_hash = (
            str(user["password_hash"]).encode("utf-8")
            if user and user.get("password_hash")
            else _DUMMY_PASSWORD_HASH
        )
        password_valid = _password_matches(normalized_password, supplied_hash)
        credentials_valid = bool(
            user
            and _EMAIL_PATTERN.fullmatch(normalized_email)
            and password_valid
        )
        if not credentials_valid:
            _record_attempt(session, email_hash, ip_hash, succeeded=False)
            _record_audit(
                session,
                event_type="LOGIN",
                outcome="DENIED",
                request_id=request_id,
                ip_hash=ip_hash,
                user_agent_hash=agent_hash,
                details={"reason": "invalid_credentials"},
            )
            session.commit()
            raise AdminInvalidCredentials("Invalid email or password.")

        user_id = int(user["id"])
        eligible = bool(
            str(user["role"] or "").upper() == ROLE_ADMIN
            and bool(user["email_verified"])
            and str(user["approval_status"] or "").upper() == STATUS_APPROVED
        )
        if not eligible:
            _record_attempt(session, email_hash, ip_hash, succeeded=False)
            _record_audit(
                session,
                user_id=user_id,
                event_type="LOGIN",
                outcome="DENIED",
                request_id=request_id,
                ip_hash=ip_hash,
                user_agent_hash=agent_hash,
                details={"reason": "admin_access_denied"},
            )
            session.commit()
            raise AdminAccessForbidden("Administrator access is not approved.")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.admin_session_ttl_minutes)
        token_id = secrets.token_urlsafe(32)
        token = jwt.encode(
            {
                "sub": str(user_id),
                "jti": token_id,
                "typ": "admin_session",
                "iat": now,
                "exp": expires_at,
                "iss": settings.jwt_issuer,
                "aud": "admin-web",
            },
            settings.jwt_secret,
            algorithm="HS256",
        )
        token_id_hash = _identifier_hash(token_id, settings.jwt_secret)
        session.execute(
            text(
                """
                INSERT INTO public.admin_sessions (
                    token_id_hash, user_id, expires_at,
                    ip_hash, user_agent_hash
                )
                VALUES (
                    :token_id_hash, :user_id, :expires_at,
                    :ip_hash, :user_agent_hash
                )
                """
            ),
            {
                "token_id_hash": token_id_hash,
                "user_id": user_id,
                "expires_at": expires_at,
                "ip_hash": ip_hash,
                "user_agent_hash": agent_hash,
            },
        )
        session.execute(
            text("UPDATE public.users SET last_login_at = NOW() WHERE id = :user_id"),
            {"user_id": user_id},
        )
        _record_attempt(session, email_hash, ip_hash, succeeded=True)
        _record_audit(
            session,
            user_id=user_id,
            event_type="LOGIN",
            outcome="SUCCESS",
            request_id=request_id,
            ip_hash=ip_hash,
            user_agent_hash=agent_hash,
            details={"session_ttl_minutes": settings.admin_session_ttl_minutes},
        )

    return IssuedAdminSession(
        token=token,
        expires_at=expires_at,
        identity=AdminIdentity(
            user_id=user_id,
            email=str(user["email"]),
            role=ROLE_ADMIN,
        ),
    )


def validate_admin_session(token: str) -> AdminIdentity:
    """Validate signature, persisted session state, and current database role."""
    settings = get_settings()
    claims = _decode_admin_token(token, verify_expiration=True)
    token_id_hash = _identifier_hash(str(claims["jti"]), settings.jwt_secret)
    with session_scope() as session:
        row = session.execute(
            text(
                """
                SELECT s.user_id, s.expires_at, s.revoked_at,
                       u.email, u.role, u.email_verified, u.approval_status
                FROM public.admin_sessions s
                JOIN public.users u ON u.id = s.user_id
                WHERE s.token_id_hash = :token_id_hash
                LIMIT 1
                """
            ),
            {"token_id_hash": token_id_hash},
        ).mappings().first()
        if not row or row["revoked_at"] is not None:
            raise AdminSessionInvalid("Admin session is invalid.")
        expires_at = row["expires_at"]
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            raise AdminSessionInvalid("Admin session has expired.")
        if (
            str(row["role"] or "").upper() != ROLE_ADMIN
            or not bool(row["email_verified"])
            or str(row["approval_status"] or "").upper() != STATUS_APPROVED
        ):
            session.execute(
                text(
                    """
                    UPDATE public.admin_sessions
                    SET revoked_at = COALESCE(revoked_at, NOW())
                    WHERE token_id_hash = :token_id_hash
                    """
                ),
                {"token_id_hash": token_id_hash},
            )
            session.commit()
            raise AdminAccessForbidden("Administrator access is no longer approved.")
        session.execute(
            text(
                """
                UPDATE public.admin_sessions
                SET last_seen_at = NOW()
                WHERE token_id_hash = :token_id_hash
                """
            ),
            {"token_id_hash": token_id_hash},
        )
    return AdminIdentity(
        user_id=int(row["user_id"]),
        email=str(row["email"]),
        role=ROLE_ADMIN,
    )


def logout_admin_session(
    *,
    token: str,
    ip_address: str,
    user_agent: str,
    request_id: str,
) -> None:
    """Revoke a persisted session while allowing already-expired logout calls."""
    settings = get_settings()
    claims = _decode_admin_token(token, verify_expiration=False)
    token_id_hash = _identifier_hash(str(claims["jti"]), settings.jwt_secret)
    with session_scope() as session:
        user_id = session.execute(
            text(
                """
                UPDATE public.admin_sessions
                SET revoked_at = COALESCE(revoked_at, NOW())
                WHERE token_id_hash = :token_id_hash
                RETURNING user_id
                """
            ),
            {"token_id_hash": token_id_hash},
        ).scalar_one_or_none()
        _record_audit(
            session,
            user_id=int(user_id) if user_id is not None else None,
            event_type="LOGOUT",
            outcome="SUCCESS",
            request_id=request_id,
            ip_hash=_identifier_hash(ip_address, settings.jwt_secret),
            user_agent_hash=_identifier_hash(user_agent, settings.jwt_secret),
            details={},
        )


def _decode_admin_token(token: str, *, verify_expiration: bool) -> dict[str, Any]:
    settings = get_settings()
    if not token:
        raise AdminSessionInvalid("Admin session is missing.")
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience="admin-web",
            options={
                "require": ["sub", "jti", "typ", "iat", "exp", "iss", "aud"],
                "verify_exp": verify_expiration,
            },
        )
    except jwt.PyJWTError as exc:
        raise AdminSessionInvalid("Admin session is invalid or expired.") from exc
    if claims.get("typ") != "admin_session":
        raise AdminSessionInvalid("Admin session type is invalid.")
    return dict(claims)


def _password_matches(password: str, password_hash: bytes) -> bool:
    try:
        encoded = password.encode("utf-8")
        if not password or len(encoded) > 72:
            return False
        return bcrypt.checkpw(encoded, password_hash)
    except (TypeError, ValueError):
        return False


def _identifier_hash(value: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        str(value or "unknown").strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _record_attempt(
    session: Any,
    email_hash: str,
    ip_hash: str,
    *,
    succeeded: bool,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO public.admin_login_attempts (
                email_hash, ip_hash, succeeded
            )
            VALUES (:email_hash, :ip_hash, :succeeded)
            """
        ),
        {
            "email_hash": email_hash,
            "ip_hash": ip_hash,
            "succeeded": succeeded,
        },
    )


def _record_audit(
    session: Any,
    *,
    event_type: str,
    outcome: str,
    request_id: str,
    ip_hash: str,
    user_agent_hash: str,
    details: dict[str, Any],
    user_id: int | None = None,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO public.admin_auth_audit_events (
                user_id, event_type, outcome, request_id,
                ip_hash, user_agent_hash, details
            )
            VALUES (
                :user_id, :event_type, :outcome, :request_id,
                :ip_hash, :user_agent_hash, CAST(:details AS JSONB)
            )
            """
        ),
        {
            "user_id": user_id,
            "event_type": event_type,
            "outcome": outcome,
            "request_id": str(request_id or "unknown")[:128],
            "ip_hash": ip_hash,
            "user_agent_hash": user_agent_hash,
            "details": __import__("json").dumps(details),
        },
    )
