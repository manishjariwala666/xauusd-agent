"""Public member authentication and payment-status API."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from config import get_settings
from core.auth import (
    AuthResult,
    register_user,
    request_password_reset,
    reset_password,
    resend_verification_email,
    verify_email,
)
from services.content_service import (
    PAYMENT_PENDING,
    PAYMENT_UNDER_REVIEW,
    get_site_setting,
    get_user_payment,
    submit_payment,
)
from services.member_auth_dependency import (
    require_authenticated_member,
    require_verified_paid_member,
)
from services.member_auth_service import (
    MemberAccessForbidden,
    MemberIdentity,
    MemberInvalidCredentials,
    login_member,
)


router = APIRouter(prefix="/api/v1/member", tags=["member"])


class SignupPayload(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    confirm_password: str = Field(min_length=12, max_length=256)
    whatsapp: str = Field(min_length=5, max_length=40)
    transaction_id: str = Field(default="", max_length=200)


class LoginPayload(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class EmailPayload(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class TokenPayload(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class ResetPayload(TokenPayload):
    password: str = Field(min_length=12, max_length=256)
    confirm_password: str = Field(min_length=12, max_length=256)


class PaymentPayload(BaseModel):
    transaction_id: str = Field(min_length=8, max_length=200)


def _result(result: AuthResult, *, failure_status: int = 400) -> dict[str, Any]:
    if not result.success:
        raise HTTPException(status_code=failure_status, detail=result.message)
    return {"message": result.message, "level": result.level}


def _profile(member: MemberIdentity) -> dict[str, Any]:
    return {
        "id": member.user_id,
        "email": member.email,
        "role": member.role,
        "email_verified": member.email_verified,
        "approval_status": member.approval_status,
        "payment_status": member.payment_status,
        "paid_access": member.email_verified and member.payment_status == "VERIFIED",
    }


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupPayload) -> dict[str, Any]:
    result = register_user(
        payload.email,
        payload.password,
        payload.confirm_password,
        payload.whatsapp,
        payload.transaction_id,
    )
    return _result(result)


@router.post("/auth/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    try:
        issued = login_member(email=payload.email, password=payload.password)
    except MemberInvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except MemberAccessForbidden as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return {
        "access_token": issued.token,
        "token_type": "bearer",
        "expires_at": issued.expires_at.isoformat(),
        "user": _profile(issued.identity),
    }


@router.get("/auth/me")
def me(member: Annotated[MemberIdentity, Depends(require_authenticated_member)]) -> dict[str, Any]:
    return {"user": _profile(member)}


@router.post("/auth/resend-verification")
def resend_verification(payload: EmailPayload) -> dict[str, Any]:
    return _result(resend_verification_email(payload.email))


@router.post("/auth/verify-email")
def verify_member_email(payload: TokenPayload) -> dict[str, Any]:
    return _result(verify_email(payload.token))


@router.post("/auth/forgot-password")
def forgot_password(payload: EmailPayload) -> dict[str, Any]:
    return _result(request_password_reset(payload.email))


@router.post("/auth/reset-password")
def reset_member_password(payload: ResetPayload) -> dict[str, Any]:
    return _result(reset_password(payload.token, payload.password, payload.confirm_password))


@router.get("/payment")
def payment_status(
    member: Annotated[MemberIdentity, Depends(require_authenticated_member)],
) -> dict[str, Any]:
    settings = get_settings()
    payment = get_user_payment(member.user_id)
    return {
        "payment": payment,
        "instructions": {
            "network": settings.usdt_network,
            "amount_usdt": settings.subscription_price_usdt,
        },
    }


@router.post("/payment/submit")
def submit_member_payment(
    payload: PaymentPayload,
    member: Annotated[MemberIdentity, Depends(require_authenticated_member)],
) -> dict[str, Any]:
    current = get_user_payment(member.user_id)
    if str(current.get("payment_status") or "") in {PAYMENT_PENDING, PAYMENT_UNDER_REVIEW}:
        raise HTTPException(409, "An existing payment submission is already being reviewed.")
    settings = get_settings()
    submit_payment(
        user_id=member.user_id,
        transaction_id=payload.transaction_id,
        amount_usdt=settings.subscription_price_usdt,
        network=settings.usdt_network,
    )
    return {"message": "Payment submitted for manual review.", "payment_status": PAYMENT_PENDING}


@router.get("/access")
def member_access(
    member: Annotated[MemberIdentity, Depends(require_verified_paid_member)],
) -> dict[str, Any]:
    settings = get_settings()
    telegram_url = get_site_setting("telegram_invite_url") or settings.telegram_invite_url
    whatsapp_url = get_site_setting("whatsapp_invite_url") or settings.support_whatsapp_url
    return {
        "telegram_invite_url": telegram_url or None,
        "whatsapp_invite_url": whatsapp_url or None,
    }
