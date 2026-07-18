"""Persistence and validation for Phase 5A automation-service enquiries."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text

from core.database import session_scope

LEAD_STATES = {"NEW", "REVIEWING", "QUALIFIED", "CONTACTED", "PROPOSAL", "WON", "LOST", "SPAM", "ARCHIVED", "TRASHED"}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class LeadNotFound(ValueError):
    pass


class LeadConflict(ValueError):
    pass


def _clean(value: Any, limit: int, *, required: bool = False) -> str | None:
    cleaned = CONTROL.sub("", str(value or "")).strip()
    if "<" in cleaned or ">" in cleaned:
        raise ValueError("HTML is not accepted.")
    if required and not cleaned:
        raise ValueError("Complete all required fields.")
    if len(cleaned) > limit:
        raise ValueError("One or more fields exceed the allowed length.")
    return cleaned or None


def _url(value: Any) -> str | None:
    cleaned = _clean(value, 2048)
    if not cleaned:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Website URL must be a valid HTTPS address.")
    return cleaned


def _audit(session: Any, actor: int, event: str, request_id: str, details: dict[str, Any]) -> None:
    session.execute(text("INSERT INTO public.admin_auth_audit_events(user_id,event_type,outcome,request_id,details) VALUES (:u,:e,'SUCCESS',:r,CAST(:d AS JSONB))"), {"u": actor, "e": event, "r": request_id, "d": json.dumps(details)})


def create_public_lead(**values: Any) -> dict[str, str]:
    if values.get("website_confirm"):
        # Honeypot submissions receive a neutral response and are not persisted.
        return {"reference": "received", "status": "received"}
    email = (_clean(values.get("business_email"), 254, required=True) or "").lower()
    if not EMAIL.fullmatch(email):
        raise ValueError("Enter a valid business email address.")
    services = values.get("requested_services") or []
    if not isinstance(services, list) or not 1 <= len(services) <= 12:
        raise ValueError("Choose at least one service.")
    services = list(dict.fromkeys((_clean(item, 80, required=True) or "") for item in services))
    contact = str(values.get("preferred_contact_method") or "").upper()
    if contact not in {"EMAIL", "PHONE", "WHATSAPP"}:
        raise ValueError("Choose a valid contact method.")
    consent = values.get("consent") is True
    if not consent:
        raise ValueError("Consent is required before submitting.")
    params = {
        "name": _clean(values.get("name"), 120, required=True), "email": email,
        "company": _clean(values.get("company"), 160), "country": _clean(values.get("country"), 100, required=True),
        "url": _url(values.get("website_url")), "phone": _clean(values.get("phone"), 40),
        "business": _clean(values.get("business_type"), 100, required=True), "services": json.dumps(services),
        "tools": _clean(values.get("current_tools"), 1000), "description": _clean(values.get("project_description"), 5000, required=True),
        "problem": _clean(values.get("primary_problem"), 2000, required=True), "outcome": _clean(values.get("expected_outcome"), 2000, required=True),
        "budget": _clean(values.get("budget_range"), 80, required=True), "timeline": _clean(values.get("preferred_timeline"), 80, required=True),
        "contact": contact, "consent_at": datetime.now(timezone.utc),
    }
    if len(params["description"] or "") < 20 or len(params["problem"] or "") < 10 or len(params["outcome"] or "") < 10:
        raise ValueError("Please provide enough project detail for a useful review.")
    with session_scope() as session:
        reference = session.execute(text("""INSERT INTO public.automation_service_leads(name,business_email,company,country,website_url,phone,business_type,requested_services,current_tools,project_description,primary_problem,expected_outcome,budget_range,preferred_timeline,preferred_contact_method,consent_recorded_at) VALUES (:name,:email,:company,:country,:url,:phone,:business,CAST(:services AS JSONB),:tools,:description,:problem,:outcome,:budget,:timeline,:contact,:consent_at) RETURNING public_reference"""), params).scalar_one()
    return {"reference": str(reference), "status": "received"}


def list_leads(*, page: int, page_size: int, search: str = "", status: str = "all") -> dict[str, Any]:
    page, page_size = max(1, page), max(1, min(50, page_size)); clauses = ["1=1"]; params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    if status.lower() != "all":
        state = status.upper()
        if state not in LEAD_STATES: raise ValueError("Invalid lead status.")
        clauses.append("status=:status"); params["status"] = state
    if search.strip(): clauses.append("(name ILIKE :query OR business_email ILIKE :query OR company ILIKE :query OR CAST(public_reference AS TEXT) ILIKE :query)"); params["query"] = f"%{search.strip()[:120]}%"
    where = " AND ".join(clauses)
    fields = "id,public_reference,name,business_email,company,country,business_type,requested_services,budget_range,status,created_at,updated_at,deleted_at"
    with session_scope() as session:
        total = int(session.execute(text(f"SELECT COUNT(*) FROM public.automation_service_leads WHERE {where}"), params).scalar_one())
        rows = session.execute(text(f"SELECT {fields} FROM public.automation_service_leads WHERE {where} ORDER BY updated_at DESC,id DESC LIMIT :limit OFFSET :offset"), params).mappings().all()
        counts = dict(session.execute(text("SELECT status,COUNT(*) FROM public.automation_service_leads GROUP BY status")).all())
    return {"items": [dict(row) for row in rows], "page": page, "page_size": page_size, "total": total, "pages": max(1, (total + page_size - 1) // page_size), "stats": {key.lower(): int(counts.get(key, 0)) for key in LEAD_STATES}}


def get_lead(lead_id: int) -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(text("SELECT * FROM public.automation_service_leads WHERE id=:id"), {"id": lead_id}).mappings().first()
        history = session.execute(text("SELECT event_type,created_at,details FROM public.admin_auth_audit_events WHERE details->>'lead_id'=:id ORDER BY created_at DESC LIMIT 50"), {"id": str(lead_id)}).mappings().all() if row else []
    if not row: raise LeadNotFound("Lead was not found.")
    return {**dict(row), "status_history": [dict(event) for event in history]}


def update_lead(*, lead_id: int, actor_id: int, request_id: str, status: str | None = None, internal_notes: str | None = None, assigned_to: int | None = None) -> dict[str, Any]:
    with session_scope() as session:
        current = session.execute(text("SELECT status FROM public.automation_service_leads WHERE id=:id FOR UPDATE"), {"id": lead_id}).scalar_one_or_none()
        if current is None: raise LeadNotFound("Lead was not found.")
        next_status = (status or current).upper()
        if next_status not in LEAD_STATES: raise ValueError("Invalid lead status.")
        if current == "TRASHED" and next_status not in {"TRASHED", "NEW"}: raise LeadConflict("Restore a trashed lead before updating its status.")
        notes = _clean(internal_notes, 10000) if internal_notes is not None else None
        session.execute(text("""UPDATE public.automation_service_leads SET status=:status,internal_notes=CASE WHEN :has_notes THEN :notes ELSE internal_notes END,assigned_to=:assigned,deleted_at=CASE WHEN :status='TRASHED' THEN COALESCE(deleted_at,NOW()) ELSE NULL END,updated_at=NOW() WHERE id=:id"""), {"status": next_status, "has_notes": internal_notes is not None, "notes": notes, "assigned": assigned_to, "id": lead_id})
        _audit(session, actor_id, "LEAD_UPDATED", request_id, {"lead_id": lead_id, "from": current, "to": next_status})
    return get_lead(lead_id)


def delete_lead(*, lead_id: int, actor_id: int, request_id: str, confirmed: bool) -> dict[str, bool]:
    if not confirmed: raise ValueError("Permanent deletion requires confirmation.")
    with session_scope() as session:
        state = session.execute(text("SELECT status FROM public.automation_service_leads WHERE id=:id FOR UPDATE"), {"id": lead_id}).scalar_one_or_none()
        if state is None: raise LeadNotFound("Lead was not found.")
        if state != "TRASHED": raise LeadConflict("Only trashed leads can be permanently deleted.")
        _audit(session, actor_id, "LEAD_DELETED", request_id, {"lead_id": lead_id})
        session.execute(text("DELETE FROM public.automation_service_leads WHERE id=:id"), {"id": lead_id})
    return {"deleted": True}
