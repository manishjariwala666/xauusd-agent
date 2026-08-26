"""Focused contracts for public/member Gold Signal access separation."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.member_auth_dependency import (
    require_authenticated_member,
    require_verified_paid_member,
)
from services.member_auth_service import MemberIdentity
from services.member_signals_api import router as member_signals_router


ROOT = Path(__file__).resolve().parents[1]


def _identity(*, email_verified: bool, payment_status: str) -> MemberIdentity:
    return MemberIdentity(
        user_id=123,
        email="member@example.com",
        role="USER",
        email_verified=email_verified,
        approval_status="PENDING",
        payment_status=payment_status,
    )


def _member_app(identity: MemberIdentity | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(member_signals_router)
    if identity is not None:
        app.dependency_overrides[require_authenticated_member] = lambda: identity
    return TestClient(app)


def test_anonymous_cannot_access_member_signals() -> None:
    response = _member_app().get("/api/v1/member/signals")
    assert response.status_code == 401


def test_unverified_member_cannot_access_member_signals() -> None:
    response = _member_app(_identity(email_verified=False, payment_status="VERIFIED")).get(
        "/api/v1/member/signals"
    )
    assert response.status_code == 403
    assert response.headers["x-auth-reason"] == "EMAIL_NOT_VERIFIED"


@pytest.mark.parametrize("payment_status", ["NOT_STARTED", "PENDING", "UNDER_REVIEW", "REJECTED"])
def test_unpaid_member_cannot_access_member_signals(payment_status: str) -> None:
    response = _member_app(_identity(email_verified=True, payment_status=payment_status)).get(
        "/api/v1/member/signals"
    )
    assert response.status_code == 403
    assert response.headers["x-auth-reason"] == "PAYMENT_NOT_VERIFIED"


def test_paid_gate_accepts_only_verified_email_and_payment() -> None:
    member = _identity(email_verified=True, payment_status="verified")
    assert require_verified_paid_member(member) is member


def test_backend_registers_member_routes_through_mounted_router() -> None:
    from backend import app

    paths = set(app.openapi()["paths"])
    expected = {
        "/api/v1/member/auth/signup",
        "/api/v1/member/auth/login",
        "/api/v1/member/auth/me",
        "/api/v1/member/auth/verify-email",
        "/api/v1/member/auth/forgot-password",
        "/api/v1/member/auth/reset-password",
        "/api/v1/member/payment",
        "/api/v1/member/payment/submit",
        "/api/v1/member/access",
        "/api/v1/member/signals",
        "/api/v1/member/signals/{public_id}",
    }
    assert expected <= paths


def test_member_signal_query_uses_only_canonical_published_source() -> None:
    source = (ROOT / "services/member_signals_api.py").read_text()
    assert "FROM public.market_signals" in source
    assert "publication_status = 'PUBLISHED'" in source
    assert "deleted_at IS NULL" in source
    assert "target_1" in source and "target_4" in source
    assert "target_5" not in source
    assert "target_6" not in source
    assert "FROM public.signals" not in source


def test_public_signal_service_never_selects_actionable_fields() -> None:
    source = (ROOT / "services/admin_signals_service.py").read_text()
    section = source.split("def list_public_signals", 1)[1].split("def get_public_signal", 1)[0]
    fields_line = next(line for line in section.splitlines() if "fields =" in line)
    for protected in (
        "signal_type",
        "price",
        "entry_price_min",
        "entry_price_max",
        "stop_loss",
        "target_1",
        "target_2",
        "target_3",
        "target_4",
        "analysis_summary",
    ):
        assert protected not in fields_line
    assert "member_access_required" in section


def test_payment_api_reuses_existing_subscription_service() -> None:
    source = (ROOT / "services/member_auth_api.py").read_text()
    assert "get_user_payment" in source
    assert "submit_payment" in source
    assert "public.payments" not in source
    assert "require_authenticated_member" in source
    payment_section = source.split('router.post("/payment/submit")', 1)[1]
    assert "require_verified_paid_member" not in payment_section.split('@router.get("/access")', 1)[0]


def test_public_web_member_bff_keeps_token_http_only() -> None:
    source = (ROOT / "public-web/app/api/member/[...path]/route.ts").read_text()
    assert 'httpOnly: true' in source
    assert 'sameSite: "lax"' in source
    assert "ADMIN_BFF_SHARED_SECRET" not in source
    assert "access_token" in source
    assert "delete responsePayload.access_token" in source


def test_public_access_page_no_longer_routes_members_to_admin() -> None:
    source = (ROOT / "public-web/components/access-page.tsx").read_text()
    assert "MemberAccessForm" in source
    assert "Open secure admin login" not in source
    assert "configuredLinks().admin" not in source
