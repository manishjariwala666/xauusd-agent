"""Public enquiry intake and protected Phase 5A lead-management endpoints."""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Annotated, Any, Callable, Literal
import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, field_validator

from services.admin_auth_api import _bearer_token, _request_id, _require_bff, _require_identity
from services.admin_leads_service import EMAIL, LeadConflict, LeadNotFound, create_public_lead, delete_lead, get_lead, list_leads, update_lead

LOGGER = logging.getLogger(__name__)
admin = APIRouter(prefix="/admin/leads", tags=["admin-leads"])
public = APIRouter(prefix="/public/automation-enquiries", tags=["public-leads"])
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempt_lock = Lock()


class PublicLeadPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120); business_email: str = Field(min_length=5, max_length=254)
    company: str | None = Field(None, max_length=160); country: str = Field(min_length=2, max_length=100); website_url: str | None = Field(None, max_length=2048); phone: str | None = Field(None, max_length=40)
    business_type: str = Field(min_length=2, max_length=100); requested_services: list[str] = Field(min_length=1, max_length=12); current_tools: str | None = Field(None, max_length=1000)
    project_description: str = Field(min_length=20, max_length=5000); primary_problem: str = Field(min_length=10, max_length=2000); expected_outcome: str = Field(min_length=10, max_length=2000)
    budget_range: str = Field(min_length=2, max_length=80); preferred_timeline: str = Field(min_length=2, max_length=80); preferred_contact_method: Literal["EMAIL", "PHONE", "WHATSAPP"]
    consent: bool; website_confirm: str = Field(default="", max_length=200)

    @field_validator("business_email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if not EMAIL.fullmatch(value.strip()):
            raise ValueError("Enter a valid business email address.")
        return value.strip().lower()


class LeadUpdatePayload(BaseModel):
    status: str | None = Field(None, max_length=20); internal_notes: str | None = Field(None, max_length=10000); assigned_to: int | None = Field(None, ge=1)


def _identity(authorization: str | None, key: str | None): _require_bff(key); return _require_identity(_bearer_token(authorization))
def _safe(operation: Callable[[], Any]):
    try: return operation()
    except LeadNotFound as error: raise HTTPException(404, str(error)) from error
    except LeadConflict as error: raise HTTPException(409, str(error)) from error
    except ValueError as error: raise HTTPException(400, str(error)) from error
    except HTTPException: raise
    except Exception as error: LOGGER.exception("Lead operation failed safely"); raise HTTPException(503, "Lead service is temporarily unavailable.") from error


def _rate_limit(request: Request) -> None:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    key = forwarded or (request.client.host if request.client else "unknown")
    now = monotonic()
    with _attempt_lock:
        bucket = _attempts[key]
        while bucket and bucket[0] < now - 900: bucket.popleft()
        if len(bucket) >= 5: raise HTTPException(429, "Too many enquiries. Please try again later.")
        bucket.append(now)


@public.post("", status_code=201)
def submit(payload: PublicLeadPayload, request: Request):
    _rate_limit(request)
    return _safe(lambda: create_public_lead(**payload.model_dump()))


@admin.get("")
def leads(response: Response, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50), search: str = Query("", max_length=120), status: str = "all", authorization: Annotated[str | None, Header()] = None, x_admin_bff_key: Annotated[str | None, Header()] = None):
    _identity(authorization, x_admin_bff_key); response.headers["Cache-Control"] = "private, no-store"; return _safe(lambda: list_leads(page=page, page_size=page_size, search=search, status=status))


@admin.get("/{lead_id}")
def detail(lead_id: int, response: Response, authorization: Annotated[str | None, Header()] = None, x_admin_bff_key: Annotated[str | None, Header()] = None):
    _identity(authorization, x_admin_bff_key); response.headers["Cache-Control"] = "private, no-store"; return _safe(lambda: get_lead(lead_id))


@admin.patch("/{lead_id}")
def update(lead_id: int, payload: LeadUpdatePayload, authorization: Annotated[str | None, Header()] = None, x_admin_bff_key: Annotated[str | None, Header()] = None, x_request_id: Annotated[str | None, Header()] = None):
    identity = _identity(authorization, x_admin_bff_key); return _safe(lambda: update_lead(lead_id=lead_id, actor_id=identity.user_id, request_id=_request_id(x_request_id), **payload.model_dump()))


@admin.delete("/{lead_id}")
def delete(lead_id: int, confirmed: bool = False, authorization: Annotated[str | None, Header()] = None, x_admin_bff_key: Annotated[str | None, Header()] = None, x_request_id: Annotated[str | None, Header()] = None):
    identity = _identity(authorization, x_admin_bff_key); return _safe(lambda: delete_lead(lead_id=lead_id, actor_id=identity.user_id, request_id=_request_id(x_request_id), confirmed=confirmed))
