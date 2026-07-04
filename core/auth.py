"""Secure authentication, account verification, and role authorization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import re
import secrets
from typing import Any

import bcrypt
import jwt
from sqlalchemy import text
import streamlit as st

from config import get_settings
from core.database import session_scope
from services.email_service import (
    EmailDeliveryError,
    send_password_reset_email,
    send_verification_email,
)


LOGGER = logging.getLogger(__name__)

ROLE_ADMIN = "ADMIN"
ROLE_USER = "USER"
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_BLOCKED = "BLOCKED"

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SESSION_DEFAULTS = {
    "logged_in": False,
    "role": None,
    "user_email": None,
    "user_id": None,
    "approval_status": None,
    "payment_status": "NOT_STARTED",
    "email_verified": False,
    "auth_token": None,
}


@dataclass(frozen=True)
class AuthResult:
    """Safe result returned to the user interface."""

    success: bool
    message: str
    level: str = "error"


def initialize_session() -> None:
    """Initialize auth state and invalidate expired or malformed sessions."""
    for key, value in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    token = st.session_state.get("auth_token")
    if token and not _restore_session_from_token(str(token)):
        logout_user()


def is_authenticated() -> bool:
    """Return whether a valid application session is active."""
    return bool(
        st.session_state.get("logged_in")
        and st.session_state.get("auth_token")
    )


def get_current_role() -> str | None:
    return st.session_state.get("role")


def get_current_user_email() -> str | None:
    return st.session_state.get("user_email")


def get_current_user_id() -> int | None:
    value = st.session_state.get("user_id")
    return int(value) if value is not None else None


def is_approved_user() -> bool:
    """Backward-compatible premium access check."""
    return is_payment_verified()


def is_payment_verified() -> bool:
    """Return whether paid links and premium content may be rendered."""
    return bool(
        is_authenticated()
        and st.session_state.get("email_verified")
        and st.session_state.get("payment_status") == "VERIFIED"
    )


def get_payment_status() -> str:
    """Return the current session payment status."""
    return str(st.session_state.get("payment_status") or "NOT_STARTED")


def logout_user() -> None:
    """Clear authentication state without changing unrelated UI state."""
    for key, value in _SESSION_DEFAULTS.items():
        st.session_state[key] = value


def authenticate_credentials(email: str, password: str) -> AuthResult:
    """Authenticate a verified and approved user using bcrypt."""
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return AuthResult(False, "Email and password are required.")

    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT id, email, password_hash, role,
                               email_verified, approval_status,
                               payment_status
                        FROM public.users
                        WHERE LOWER(email) = :email
                        LIMIT 1
                        """
                    ),
                    {"email": normalized_email},
                )
                .mappings()
                .first()
            )

            if not row or not row["password_hash"]:
                return AuthResult(False, "Invalid email or password.")
            if not bcrypt.checkpw(
                password.encode("utf-8"),
                str(row["password_hash"]).encode("utf-8"),
            ):
                return AuthResult(False, "Invalid email or password.")
            if not row["email_verified"]:
                return AuthResult(
                    False,
                    "Please verify your email before signing in.",
                    level="warning",
                )
            if row["approval_status"] == STATUS_BLOCKED:
                return AuthResult(False, "This account has been blocked.")
            if (
                row["role"] == ROLE_ADMIN
                and row["approval_status"] != STATUS_APPROVED
            ):
                return AuthResult(
                    False,
                    "Administrator access is not approved.",
                )

            session.execute(
                text(
                    "UPDATE public.users SET last_login_at = NOW() "
                    "WHERE id = :user_id"
                ),
                {"user_id": row["id"]},
            )
            _set_authenticated_session(dict(row))
            return AuthResult(True, "Login successful.", level="success")
    except Exception:
        LOGGER.exception("User authentication failed.")
        return AuthResult(
            False,
            "Login is temporarily unavailable. Please try again.",
        )


def register_user(
    email: str,
    password: str,
    confirm_password: str,
    whatsapp: str,
    transaction_id: str,
) -> AuthResult:
    """Create a pending account and send a single-use verification email."""
    normalized_email = email.strip().lower()
    normalized_whatsapp = whatsapp.strip()
    normalized_txid = transaction_id.strip()

    validation_error = _validate_registration(
        normalized_email,
        password,
        confirm_password,
        normalized_whatsapp,
        normalized_txid,
    )
    if validation_error:
        return AuthResult(False, validation_error, level="warning")

    verification_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(verification_token)
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    try:
        with session_scope() as session:
            exists = session.execute(
                text(
                    "SELECT 1 FROM public.users "
                    "WHERE LOWER(email) = :email LIMIT 1"
                ),
                {"email": normalized_email},
            ).first()
            if exists:
                return AuthResult(False, "An account already exists for this email.")

            session.execute(
                text(
                    """
                    INSERT INTO public.users (
                        email, password_hash, whatsapp, txid, status,
                        role, email_verified, approval_status, payment_status,
                        verification_token_hash, verification_expires_at
                    )
                    VALUES (
                        :email, :password_hash, :whatsapp, :txid, 'Pending',
                        :role, FALSE, :approval_status, 'NOT_STARTED',
                        :token_hash, :expires_at
                    )
                    """
                ),
                {
                    "email": normalized_email,
                    "password_hash": password_hash,
                    "whatsapp": normalized_whatsapp,
                    "txid": normalized_txid or None,
                    "role": ROLE_USER,
                    "approval_status": STATUS_PENDING,
                    "token_hash": token_hash,
                    "expires_at": datetime.now(timezone.utc)
                    + timedelta(hours=24),
                },
            )
    except Exception:
        LOGGER.exception("Account registration failed.")
        return AuthResult(False, "Account registration failed. Please try again.")

    try:
        send_verification_email(normalized_email, verification_token)
    except EmailDeliveryError:
        LOGGER.exception("Verification email was not delivered.")
        return AuthResult(
            False,
            "Account created, but verification email could not be sent. "
            "Please contact support.",
            level="warning",
        )

    return AuthResult(
        True,
        "Account created. Please verify your email, then wait for USDT approval.",
        level="success",
    )


def verify_email(token: str) -> AuthResult:
    """Verify an email using a hashed, expiring, single-use token."""
    if not token:
        return AuthResult(False, "Verification token is missing.")
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT id FROM public.users
                        WHERE verification_token_hash = :token_hash
                          AND verification_expires_at > NOW()
                        LIMIT 1
                        """
                    ),
                    {"token_hash": _hash_token(token)},
                )
                .mappings()
                .first()
            )
            if not row:
                return AuthResult(False, "Verification link is invalid or expired.")
            session.execute(
                text(
                    """
                    UPDATE public.users
                    SET email_verified = TRUE,
                        verification_token_hash = NULL,
                        verification_expires_at = NULL
                    WHERE id = :user_id
                    """
                ),
                {"user_id": row["id"]},
            )
    except Exception:
        LOGGER.exception("Email verification failed.")
        return AuthResult(False, "Email verification is temporarily unavailable.")
    return AuthResult(True, "Email verified successfully. You may now sign in.", "success")


def request_password_reset(email: str) -> AuthResult:
    """Issue a reset token without revealing whether an account exists."""
    normalized_email = email.strip().lower()
    generic_result = AuthResult(
        True,
        "If this email is registered, a reset link has been sent.",
        "success",
    )
    if not _EMAIL_PATTERN.fullmatch(normalized_email):
        return generic_result

    reset_token = secrets.token_urlsafe(32)
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        "SELECT id, email FROM public.users "
                        "WHERE LOWER(email) = :email LIMIT 1"
                    ),
                    {"email": normalized_email},
                )
                .mappings()
                .first()
            )
            if not row:
                return generic_result
            session.execute(
                text(
                    """
                    UPDATE public.users
                    SET reset_token_hash = :token_hash,
                        reset_expires_at = :expires_at
                    WHERE id = :user_id
                    """
                ),
                {
                    "token_hash": _hash_token(reset_token),
                    "expires_at": datetime.now(timezone.utc)
                    + timedelta(minutes=30),
                    "user_id": row["id"],
                },
            )
        send_password_reset_email(str(row["email"]), reset_token)
    except Exception:
        LOGGER.exception("Password reset request failed.")
    return generic_result


def reset_password(
    token: str,
    password: str,
    confirm_password: str,
) -> AuthResult:
    """Replace a password using an expiring single-use reset token."""
    password_error = _validate_password(password, confirm_password)
    if password_error:
        return AuthResult(False, password_error, "warning")
    if not token:
        return AuthResult(False, "Reset token is missing.")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")
    try:
        with session_scope() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT id FROM public.users
                        WHERE reset_token_hash = :token_hash
                          AND reset_expires_at > NOW()
                        LIMIT 1
                        """
                    ),
                    {"token_hash": _hash_token(token)},
                )
                .mappings()
                .first()
            )
            if not row:
                return AuthResult(False, "Reset link is invalid or expired.")
            session.execute(
                text(
                    """
                    UPDATE public.users
                    SET password_hash = :password_hash,
                        reset_token_hash = NULL,
                        reset_expires_at = NULL
                    WHERE id = :user_id
                    """
                ),
                {"password_hash": password_hash, "user_id": row["id"]},
            )
    except Exception:
        LOGGER.exception("Password reset failed.")
        return AuthResult(False, "Password reset is temporarily unavailable.")
    return AuthResult(True, "Password updated. Please sign in again.", "success")


def list_users() -> list[dict[str, Any]]:
    """Return user records required by the protected admin dashboard."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, email, whatsapp, txid, role, email_verified,
                           approval_status, created_at
                    FROM public.users
                    ORDER BY created_at DESC
                    """
                )
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]


def set_user_approval(user_id: int, approval_status: str) -> None:
    """Update premium approval while preventing arbitrary status values."""
    if approval_status not in {
        STATUS_PENDING,
        STATUS_APPROVED,
        STATUS_BLOCKED,
    }:
        raise ValueError("Unsupported approval status.")
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.users
                SET approval_status = :approval_status,
                    status = CASE
                        WHEN :approval_status = 'APPROVED' THEN 'Approved'
                        WHEN :approval_status = 'BLOCKED' THEN 'Blocked'
                        ELSE 'Pending'
                    END,
                    approved_at = CASE
                        WHEN :approval_status = 'APPROVED' THEN NOW()
                        ELSE NULL
                    END
                WHERE id = :user_id AND role = 'USER'
                """
            ),
            {"approval_status": approval_status, "user_id": user_id},
        )


def _validate_registration(
    email: str,
    password: str,
    confirm_password: str,
    whatsapp: str,
    transaction_id: str,
) -> str | None:
    if not all((email, password, confirm_password, whatsapp)):
        return "All fields are required."
    if not _EMAIL_PATTERN.fullmatch(email):
        return "Enter a valid email address."
    return _validate_password(password, confirm_password)


def _validate_password(password: str, confirm_password: str) -> str | None:
    if password != confirm_password:
        return "Passwords do not match."
    if len(password) < 12:
        return "Password must contain at least 12 characters."
    if not (
        re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"[^A-Za-z0-9]", password)
    ):
        return "Password must include uppercase, lowercase, number, and symbol."
    return None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_authenticated_session(user: dict[str, Any]) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "email": str(user["email"]),
        "role": str(user["role"]),
        "approval_status": str(user["approval_status"]),
        "payment_status": str(user.get("payment_status") or "NOT_STARTED"),
        "email_verified": bool(user["email_verified"]),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
        "iss": settings.jwt_issuer,
    }
    st.session_state.auth_token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )
    _apply_claims(payload)


def _restore_session_from_token(token: str) -> bool:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
    except jwt.PyJWTError:
        LOGGER.info("Expired or invalid authentication token rejected.")
        return False
    _apply_claims(claims)
    return True


def _apply_claims(claims: dict[str, Any]) -> None:
    st.session_state.logged_in = True
    st.session_state.user_id = int(claims["sub"])
    st.session_state.user_email = str(claims["email"])
    st.session_state.role = str(claims["role"])
    st.session_state.approval_status = str(claims["approval_status"])
    st.session_state.payment_status = str(
        claims.get("payment_status") or "NOT_STARTED"
    )
    st.session_state.email_verified = bool(claims["email_verified"])
