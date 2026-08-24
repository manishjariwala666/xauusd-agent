"""FastAPI dependencies for authenticated and paid VenusRealm members."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.member_auth_service import (
    MemberAccessForbidden,
    MemberIdentity,
    MemberSessionInvalid,
    verify_member_token,
)


security = HTTPBearer(auto_error=False)


def require_authenticated_member(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> MemberIdentity:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_member_token(credentials.credentials)
    except MemberSessionInvalid as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except MemberAccessForbidden as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def require_verified_paid_member(
    member: MemberIdentity = Depends(require_authenticated_member),
) -> MemberIdentity:
    if not member.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required.",
            headers={"X-Auth-Reason": "EMAIL_NOT_VERIFIED"},
        )
    if member.payment_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified paid membership required.",
            headers={"X-Auth-Reason": "PAYMENT_NOT_VERIFIED"},
        )
    return member
