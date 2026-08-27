"""Member-safe authentication helpers compatible with the existing auth contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from sqlalchemy import text

from config import get_settings
from core.auth import ROLE_USER, STATUS_BLOCKED
from core.database import session_scope


class MemberAuthError(RuntimeError):
    """Base class for member authentication failures."""


class MemberInvalidCredentials(MemberAuthError):
    pass


class MemberAccessForbidden(MemberAuthError):
    pass


class MemberSessionInvalid(MemberAuthError):
    pass


@dataclass(frozen=True)
class MemberIdentity:
    user_id: int
    email: str
    role: str
    email_verified: bool
    approval_status: str
    payment_status: str


@dataclass(frozen=True)
class IssuedMemberSession:
    token: str
    expires_at: datetime
    identity: MemberIdentity


def _identity_from_row(row: Any) -> MemberIdentity:
    payment_status = str(row["payment_status"] or "NOT_STARTED").strip().upper()
    subscription_status = str(
        row.get("subscription_payment_status") or ""
    ).strip().upper()
    if payment_status != "VERIFIED" and subscription_status == "VERIFIED":
        payment_status = "VERIFIED"
    return MemberIdentity(
        user_id=int(row["id"]),
        email=str(row["email"]),
        role=str(row["role"]),
        email_verified=bool(row["email_verified"]),
        approval_status=str(row["approval_status"] or "PENDING"),
        payment_status=payment_status,
    )


def get_member_identity(user_id: int) -> MemberIdentity:
    """Load current member truth from public.users, never from stale token claims."""
    with session_scope() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT u.id, u.email, u.role, u.email_verified,
                           u.approval_status, u.payment_status,
                           s.payment_status AS subscription_payment_status
                    FROM public.users u
                    LEFT JOIN LATERAL (
                        SELECT payment_status
                        FROM public.subscriptions
                        WHERE user_id = u.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) s ON TRUE
                    WHERE u.id = :user_id
                    LIMIT 1
                    """
                ),
                {"user_id": int(user_id)},
            )
            .mappings()
            .first()
        )
    if not row:
        raise MemberSessionInvalid("Member account was not found.")
    identity = _identity_from_row(row)
    if identity.role != ROLE_USER:
        raise MemberAccessForbidden("Member access required.")
    if identity.approval_status == STATUS_BLOCKED:
        raise MemberAccessForbidden("This account has been blocked.")
    return identity


def login_member(*, email: str, password: str) -> IssuedMemberSession:
    """Authenticate a ROLE_USER with the same bcrypt/JWT contract as core.auth."""
    normalized_email = str(email or "").strip().lower()
    normalized_password = str(password or "")
    if not normalized_email or not normalized_password:
        raise MemberInvalidCredentials("Invalid email or password.")

    with session_scope() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT u.id, u.email, u.password_hash, u.role,
                           u.email_verified, u.approval_status,
                           u.payment_status,
                           s.payment_status AS subscription_payment_status
                    FROM public.users u
                    LEFT JOIN LATERAL (
                        SELECT payment_status
                        FROM public.subscriptions
                        WHERE user_id = u.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) s ON TRUE
                    WHERE LOWER(u.email) = :email
                    LIMIT 1
                    """
                ),
                {"email": normalized_email},
            )
            .mappings()
            .first()
        )
        if (
            not row
            or not row["password_hash"]
            or not bcrypt.checkpw(
                normalized_password.encode("utf-8"),
                str(row["password_hash"]).encode("utf-8"),
            )
        ):
            raise MemberInvalidCredentials("Invalid email or password.")

        identity = _identity_from_row(row)
        if identity.role != ROLE_USER:
            raise MemberAccessForbidden("Member access required.")
        if identity.approval_status == STATUS_BLOCKED:
            raise MemberAccessForbidden("This account has been blocked.")
        if not identity.email_verified:
            raise MemberAccessForbidden("Please verify your email before signing in.")

        session.execute(
            text("UPDATE public.users SET last_login_at = NOW() WHERE id = :user_id"),
            {"user_id": identity.user_id},
        )

    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {
        "sub": str(identity.user_id),
        "email": identity.email,
        "role": identity.role,
        "approval_status": identity.approval_status,
        "payment_status": identity.payment_status,
        "email_verified": identity.email_verified,
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return IssuedMemberSession(token=token, expires_at=expires_at, identity=identity)


def verify_member_token(token: str) -> MemberIdentity:
    """Validate the existing application JWT contract then refresh DB access state."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            str(token or ""),
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise MemberSessionInvalid("Invalid or expired member session.") from exc
    return get_member_identity(user_id)
