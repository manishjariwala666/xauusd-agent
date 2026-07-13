"""Minimal protected FastAPI surface for the separate admin BFF."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from services.admin_auth_service import (
    AdminAccessForbidden,
    AdminAuthUnavailable,
    AdminIdentity,
    AdminInvalidCredentials,
    AdminLoginRateLimited,
    AdminSessionInvalid,
    login_admin,
    logout_admin_session,
    validate_admin_session,
    verify_bff_secret,
)


LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-auth"])


class AdminLoginRequest(BaseModel):
    """Credentials accepted only from the trusted server-side BFF."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class AdminIdentityResponse(BaseModel):
    user_id: int
    email: str
    role: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: AdminIdentityResponse


class AdminSessionResponse(BaseModel):
    authenticated: bool = True
    user: AdminIdentityResponse


def _identity_response(identity: AdminIdentity) -> AdminIdentityResponse:
    return AdminIdentityResponse(
        user_id=identity.user_id,
        email=identity.email,
        role=identity.role,
    )


def _request_id(value: str | None) -> str:
    return str(value or uuid4())[:128]


def _client_ip(request: Request) -> str:
    forwarded = str(request.headers.get("x-forwarded-for") or "").split(",")[0]
    if forwarded.strip():
        return forwarded.strip()[:128]
    return str(request.client.host if request.client else "unknown")[:128]


def _bearer_token(authorization: str | None) -> str:
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Admin authentication is required.")
    return token.strip()


def _require_bff(provided: str | None) -> None:
    try:
        verify_bff_secret(provided)
    except AdminAuthUnavailable as exc:
        raise HTTPException(503, "Admin authentication is unavailable.") from exc
    except AdminAccessForbidden as exc:
        raise HTTPException(403, "Admin BFF authorization failed.") from exc


def _require_identity(token: str) -> AdminIdentity:
    try:
        return validate_admin_session(token)
    except AdminAccessForbidden as exc:
        raise HTTPException(403, "Administrator access is forbidden.") from exc
    except AdminSessionInvalid as exc:
        raise HTTPException(401, "Admin session is invalid or expired.") from exc


@router.post("/auth/login", response_model=AdminLoginResponse)
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> AdminLoginResponse:
    """Issue a short session only to the trusted BFF after database checks."""
    _require_bff(x_admin_bff_key)
    request_id = _request_id(x_request_id)
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    try:
        issued = login_admin(
            email=payload.email,
            password=payload.password,
            ip_address=_client_ip(request),
            user_agent=str(request.headers.get("user-agent") or "unknown")[:512],
            request_id=request_id,
        )
    except AdminLoginRateLimited as exc:
        raise HTTPException(
            429,
            "Too many login attempts. Please try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except AdminInvalidCredentials as exc:
        raise HTTPException(401, "Invalid email or password.") from exc
    except AdminAccessForbidden as exc:
        raise HTTPException(403, "Administrator access is forbidden.") from exc
    except Exception as exc:
        LOGGER.exception("Admin login failed safely; request_id=%s", request_id)
        raise HTTPException(503, "Admin authentication is unavailable.") from exc
    return AdminLoginResponse(
        access_token=issued.token,
        expires_at=issued.expires_at,
        user=_identity_response(issued.identity),
    )


@router.get("/auth/session", response_model=AdminSessionResponse)
def admin_session(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> AdminSessionResponse:
    """Revalidate role and account state from PostgreSQL on every request."""
    _require_bff(x_admin_bff_key)
    identity = _require_identity(_bearer_token(authorization))
    response.headers["Cache-Control"] = "no-store"
    return AdminSessionResponse(user=_identity_response(identity))


@router.post("/auth/logout", status_code=204)
def admin_logout(
    request: Request,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> Response:
    """Revoke the server-side session; the BFF also removes its cookie."""
    _require_bff(x_admin_bff_key)
    token = _bearer_token(authorization)
    try:
        logout_admin_session(
            token=token,
            ip_address=_client_ip(request),
            user_agent=str(request.headers.get("user-agent") or "unknown")[:512],
            request_id=_request_id(x_request_id),
        )
    except AdminSessionInvalid:
        pass
    except Exception as exc:
        LOGGER.exception("Admin logout failed safely")
        raise HTTPException(503, "Admin logout is temporarily unavailable.") from exc
    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/dashboard/summary")
def admin_dashboard_summary(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Return only Phase 1 shell data; CMS and analytics stay unloaded."""
    _require_bff(x_admin_bff_key)
    identity = _require_identity(_bearer_token(authorization))
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "user": _identity_response(identity).model_dump(),
        "cards": [
            {"label": "Content", "value": "Not loaded", "state": "placeholder"},
            {"label": "Signals", "value": "Not loaded", "state": "placeholder"},
            {"label": "Users", "value": "Not loaded", "state": "placeholder"},
            {"label": "System", "value": "Foundation ready", "state": "ready"},
        ],
    }
