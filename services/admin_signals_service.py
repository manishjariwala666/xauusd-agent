"""ADMIN signal CRUD, lifecycle enforcement, and public-safe reads."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import text

from core.database import session_scope


class SignalNotFoundError(ValueError): pass
class SignalConflictError(ValueError): pass


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"PUBLISH", "SCHEDULE", "TRASH"},
    "SCHEDULED": {"PUBLISH", "UNPUBLISH", "CANCEL", "TRASH"},
    "PUBLISHED": {"ACTIVATE", "UNPUBLISH", "CANCEL", "EXPIRE", "TRASH"},
    "ACTIVE": {"TARGET_HIT", "STOPPED", "CANCEL", "CLOSE", "EXPIRE"},
    "TARGET_HIT": {"CLOSE", "TRASH"},
    "STOPPED": {"CLOSE", "TRASH"},
    "CANCELLED": {"TRASH"},
    "EXPIRED": {"TRASH"},
    "CLOSED": {"TRASH"},
    "TRASHED": {"RESTORE", "DELETE"},
}


def _audit(session: Any, actor_id: int, event: str, request_id: str, details: dict[str, Any]) -> None:
    session.execute(text("""INSERT INTO public.admin_auth_audit_events
        (user_id,event_type,outcome,request_id,details)
        VALUES (:user_id,:event,'SUCCESS',:request_id,CAST(:details AS JSONB))"""), {
        "user_id": int(actor_id), "event": event, "request_id": str(request_id or "unknown")[:128], "details": json.dumps(details),
    })


def _row(signal_id: int) -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(text("""SELECT ms.*, creator.email AS created_by_email
            FROM public.market_signals ms LEFT JOIN public.users creator ON creator.id=ms.created_by
            WHERE ms.id=:id"""), {"id": int(signal_id)}).mappings().first()
    if not row: raise SignalNotFoundError("Signal was not found.")
    return dict(row)


def get_admin_signal(signal_id: int) -> dict[str, Any]:
    return _row(signal_id)


def list_admin_signals(*, page: int, page_size: int, search: str = "", status: str = "all", direction: str = "all", symbol: str = "", timeframe: str = "all", date_filter: str = "all", sort: str = "updated_desc") -> dict[str, Any]:
    page, page_size = max(1, int(page)), max(1, min(50, int(page_size)))
    clauses: list[str] = []
    params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    if status != "all": clauses.append("ms.lifecycle_status=:status"); params["status"] = status.upper()
    if direction != "all": clauses.append("ms.signal_type=:direction"); params["direction"] = direction.upper()
    if timeframe != "all": clauses.append("ms.timeframe=:timeframe"); params["timeframe"] = timeframe.upper()
    if symbol.strip(): clauses.append("ms.symbol ILIKE :symbol"); params["symbol"] = f"%{symbol.strip()[:30]}%"
    if search.strip(): clauses.append("(ms.symbol ILIKE :search OR ms.analysis_summary ILIKE :search OR CAST(ms.public_id AS TEXT) ILIKE :search)"); params["search"] = f"%{search.strip()[:120]}%"
    days = {"7d": 7, "30d": 30, "90d": 90}.get(date_filter)
    if date_filter != "all" and days is None: raise ValueError("Unsupported date filter.")
    if days: clauses.append("ms.updated_at >= NOW() - make_interval(days => :days)"); params["days"] = days
    orders = {"updated_desc": "ms.updated_at DESC", "updated_asc": "ms.updated_at ASC", "published_desc": "ms.published_at DESC NULLS LAST"}
    if sort not in orders: raise ValueError("Unsupported signal sort.")
    where = " AND ".join(clauses) if clauses else "TRUE"
    with session_scope() as session:
        total = session.execute(text(f"SELECT COUNT(*) FROM public.market_signals ms WHERE {where}"), params).scalar_one()
        rows = session.execute(text(f"""SELECT ms.*, creator.email AS created_by_email
            FROM public.market_signals ms LEFT JOIN public.users creator ON creator.id=ms.created_by
            WHERE {where} ORDER BY {orders[sort]}, ms.id DESC LIMIT :limit OFFSET :offset"""), params).mappings().all()
        stats_rows = session.execute(text("SELECT lifecycle_status, COUNT(*) FROM public.market_signals GROUP BY lifecycle_status")).all()
    stats = {"total": sum(int(count) for _, count in stats_rows)}
    stats.update({str(state).lower(): int(count) for state, count in stats_rows})
    return {"items": [dict(row) for row in rows], "page": page, "page_size": page_size, "total": int(total), "pages": max(1, (int(total) + page_size - 1) // page_size), "stats": stats}


def create_admin_signal(*, actor_id: int, request_id: str, values: dict[str, Any]) -> dict[str, Any]:
    params = _params(values, actor_id)
    with session_scope() as session:
        signal_id = session.execute(text("""INSERT INTO public.market_signals (
            symbol,market,price,signal_type,entry_type,entry_price_min,entry_price_max,
            target_price,target_1,target_2,target_3,target_4,stop_loss,source,timeframe,
            risk_level,confidence_label,analysis_summary,technical_reason,astrology_reason,
            risk_note,publication_status,lifecycle_status,scheduled_at,expires_at,featured,
            created_by,updated_by,signal_time,created_at,updated_at
        ) VALUES (
            :symbol,:market,:entry_price,:direction,:entry_type,:entry_price_min,:entry_price_max,
            :target_1,:target_1,:target_2,:target_3,:target_4,:stop_loss,'ADMIN',:timeframe,
            :risk_level,:confidence_label,:analysis_summary,:technical_reason,:astrology_reason,
            :risk_note,:publication_status,:lifecycle_status,:scheduled_at,:expires_at,:featured,
            :actor_id,:actor_id,NOW(),NOW(),NOW()
        ) RETURNING id"""), params).scalar_one()
        _audit(session, actor_id, "SIGNAL_CREATED", request_id, {"signal_id": int(signal_id), "direction": params["direction"]})
    return _row(int(signal_id))


def update_admin_signal(*, signal_id: int, actor_id: int, request_id: str, values: dict[str, Any]) -> dict[str, Any]:
    params = {**_params(values, actor_id), "id": int(signal_id)}
    with session_scope() as session:
        existing = session.execute(text("SELECT lifecycle_status FROM public.market_signals WHERE id=:id FOR UPDATE"), params).scalar_one_or_none()
        if existing is None: raise SignalNotFoundError("Signal was not found.")
        if str(existing) not in {"DRAFT", "SCHEDULED"}: raise SignalConflictError("Only draft or scheduled signals can be edited.")
        session.execute(text("""UPDATE public.market_signals SET
            symbol=:symbol,market=:market,price=:entry_price,signal_type=:direction,entry_type=:entry_type,
            entry_price_min=:entry_price_min,entry_price_max=:entry_price_max,target_price=:target_1,
            target_1=:target_1,target_2=:target_2,target_3=:target_3,target_4=:target_4,stop_loss=:stop_loss,
            timeframe=:timeframe,risk_level=:risk_level,confidence_label=:confidence_label,
            analysis_summary=:analysis_summary,technical_reason=:technical_reason,astrology_reason=:astrology_reason,
            risk_note=:risk_note,scheduled_at=:scheduled_at,expires_at=:expires_at,featured=:featured,
            publication_status=:publication_status,lifecycle_status=:lifecycle_status,updated_by=:actor_id,updated_at=NOW()
            WHERE id=:id"""), params)
        _audit(session, actor_id, "SIGNAL_UPDATED", request_id, {"signal_id": int(signal_id)})
    return _row(signal_id)


def duplicate_admin_signal(*, signal_id: int, actor_id: int, request_id: str) -> dict[str, Any]:
    with session_scope() as session:
        new_id = session.execute(text("""INSERT INTO public.market_signals (
            symbol,market,price,signal_type,entry_type,entry_price_min,entry_price_max,target_price,
            target_1,target_2,target_3,target_4,stop_loss,source,timeframe,risk_level,confidence_label,
            analysis_summary,technical_reason,astrology_reason,risk_note,publication_status,lifecycle_status,
            featured,created_by,updated_by,signal_time,created_at,updated_at
        ) SELECT symbol,market,price,signal_type,entry_type,entry_price_min,entry_price_max,target_price,
            target_1,target_2,target_3,target_4,stop_loss,'ADMIN',timeframe,risk_level,confidence_label,
            analysis_summary,technical_reason,astrology_reason,risk_note,'DRAFT','DRAFT',FALSE,:actor,:actor,NOW(),NOW(),NOW()
          FROM public.market_signals WHERE id=:id RETURNING id"""), {"id": int(signal_id), "actor": int(actor_id)}).scalar_one_or_none()
        if new_id is None: raise SignalNotFoundError("Signal was not found.")
        _audit(session, actor_id, "SIGNAL_DUPLICATED", request_id, {"signal_id": int(signal_id), "duplicate_id": int(new_id)})
    return _row(int(new_id))


def transition_admin_signal(*, signal_id: int, action: str, actor_id: int, request_id: str, outcome: str | None = None, result_points: Decimal | None = None) -> dict[str, Any]:
    action = action.upper()
    with session_scope() as session:
        row = session.execute(text("SELECT * FROM public.market_signals WHERE id=:id FOR UPDATE"), {"id": int(signal_id)}).mappings().first()
        if not row: raise SignalNotFoundError("Signal was not found.")
        current = str(row["lifecycle_status"])
        if action not in ALLOWED_TRANSITIONS.get(current, set()): raise SignalConflictError(f"Cannot {action.lower().replace('_',' ')} a {current.lower().replace('_',' ')} signal.")
        if action in {"PUBLISH", "ACTIVATE"}: _validate_publishable(dict(row))
        updates = _transition_values(action, outcome=outcome, result_points=result_points)
        assignments = ", ".join(f"{key}=:{key}" for key in updates)
        session.execute(text(f"UPDATE public.market_signals SET {assignments}, updated_by=:actor, updated_at=NOW() WHERE id=:id"), {**updates, "actor": int(actor_id), "id": int(signal_id)})
        _audit(session, actor_id, f"SIGNAL_{action}", request_id, {"signal_id": int(signal_id), "from": current, "to": updates["lifecycle_status"]})
    return _row(signal_id)


def delete_admin_signal(*, signal_id: int, actor_id: int, request_id: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed: raise ValueError("Permanent deletion requires confirmation.")
    with session_scope() as session:
        state = session.execute(text("SELECT lifecycle_status FROM public.market_signals WHERE id=:id FOR UPDATE"), {"id": int(signal_id)}).scalar_one_or_none()
        if state is None: raise SignalNotFoundError("Signal was not found.")
        if state != "TRASHED": raise SignalConflictError("Only trashed signals can be permanently deleted.")
        _audit(session, actor_id, "SIGNAL_DELETED", request_id, {"signal_id": int(signal_id)})
        session.execute(text("DELETE FROM public.market_signals WHERE id=:id"), {"id": int(signal_id)})
    return {"deleted": True}


def list_public_signals(*, page: int, page_size: int, status: str = "all", symbol: str = "", direction: str = "all") -> dict[str, Any]:
    page, page_size = max(1, int(page)), max(1, min(24, int(page_size)))
    clauses = ["publication_status='PUBLISHED'", "deleted_at IS NULL"]
    params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    if status != "all": clauses.append("lifecycle_status=:status"); params["status"] = status.upper()
    if direction != "all": clauses.append("signal_type=:direction"); params["direction"] = direction.upper()
    if symbol.strip(): clauses.append("symbol ILIKE :symbol"); params["symbol"] = f"%{symbol.strip()[:30]}%"
    where = " AND ".join(clauses)
    fields = "public_id,symbol,market,signal_type AS direction,timeframe,entry_type,price AS entry_price,entry_price_min,entry_price_max,stop_loss,target_1,target_2,target_3,target_4,risk_level,lifecycle_status AS status,published_at,updated_at,expires_at,featured"
    with session_scope() as session:
        total = session.execute(text(f"SELECT COUNT(*) FROM public.market_signals WHERE {where}"), params).scalar_one()
        rows = session.execute(text(f"SELECT {fields} FROM public.market_signals WHERE {where} ORDER BY featured DESC,published_at DESC,id DESC LIMIT :limit OFFSET :offset"), params).mappings().all()
    return {"items": [dict(row) for row in rows], "page": page, "page_size": page_size, "total": int(total), "pages": max(1, (int(total)+page_size-1)//page_size)}


def get_public_signal(public_id: str) -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(text("""SELECT public_id,symbol,market,signal_type AS direction,timeframe,entry_type,
            price AS entry_price,entry_price_min,entry_price_max,stop_loss,target_1,target_2,target_3,target_4,
            risk_level,confidence_label,analysis_summary,technical_reason,astrology_reason,risk_note,
            lifecycle_status AS status,published_at,updated_at,expires_at,closed_at,outcome,featured
            FROM public.market_signals WHERE public_id=CAST(:public_id AS UUID)
              AND publication_status='PUBLISHED' AND deleted_at IS NULL"""), {"public_id": public_id}).mappings().first()
    if not row: raise SignalNotFoundError("Public signal was not found.")
    return dict(row)


def _params(values: dict[str, Any], actor_id: int) -> dict[str, Any]:
    publication = str(values.get("publication_status") or "DRAFT").upper()
    lifecycle = "SCHEDULED" if publication == "SCHEDULED" else "DRAFT"
    return {**values, "symbol": str(values["symbol"]).upper(), "market": str(values.get("market") or "FOREX").upper(), "direction": str(values["direction"]).upper(), "entry_type": str(values.get("entry_type") or "MARKET").upper(), "timeframe": str(values.get("timeframe") or "INTRADAY").upper(), "risk_level": str(values.get("risk_level") or "MEDIUM").upper(), "publication_status": publication, "lifecycle_status": lifecycle, "actor_id": int(actor_id)}


def _validate_publishable(row: dict[str, Any]) -> None:
    direction, entry = str(row.get("signal_type")), Decimal(str(row.get("price")))
    stop, target = row.get("stop_loss"), row.get("target_1")
    if stop is None or target is None: raise SignalConflictError("A stop loss and first target are required before publishing.")
    if not str(row.get("analysis_summary") or "").strip(): raise SignalConflictError("An analysis summary is required before publishing.")
    if direction == "BUY" and not (Decimal(str(stop)) < entry < Decimal(str(target))): raise SignalConflictError("BUY levels require stop loss below entry and target above entry.")
    if direction == "SELL" and not (Decimal(str(target)) < entry < Decimal(str(stop))): raise SignalConflictError("SELL levels require target below entry and stop loss above entry.")


def _transition_values(action: str, *, outcome: str | None, result_points: Decimal | None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    mapping: dict[str, dict[str, Any]] = {
        "PUBLISH": {"publication_status": "PUBLISHED", "lifecycle_status": "PUBLISHED", "published_at": now, "deleted_at": None},
        "SCHEDULE": {"publication_status": "SCHEDULED", "lifecycle_status": "SCHEDULED"},
        "UNPUBLISH": {"publication_status": "UNPUBLISHED", "lifecycle_status": "DRAFT", "published_at": None},
        "ACTIVATE": {"publication_status": "PUBLISHED", "lifecycle_status": "ACTIVE"},
        "TARGET_HIT": {"publication_status": "PUBLISHED", "lifecycle_status": "TARGET_HIT", "outcome": outcome or "TARGET_HIT", "result_points": result_points},
        "STOPPED": {"publication_status": "PUBLISHED", "lifecycle_status": "STOPPED", "outcome": outcome or "STOPPED", "result_points": result_points},
        "CANCEL": {"publication_status": "PUBLISHED", "lifecycle_status": "CANCELLED", "outcome": outcome or "CANCELLED", "closed_at": now},
        "EXPIRE": {"publication_status": "PUBLISHED", "lifecycle_status": "EXPIRED", "outcome": outcome or "EXPIRED", "closed_at": now},
        "CLOSE": {"publication_status": "PUBLISHED", "lifecycle_status": "CLOSED", "outcome": outcome or "CLOSED", "result_points": result_points, "closed_at": now},
        "TRASH": {"publication_status": "TRASHED", "lifecycle_status": "TRASHED", "deleted_at": now},
        "RESTORE": {"publication_status": "DRAFT", "lifecycle_status": "DRAFT", "deleted_at": None, "published_at": None},
    }
    return mapping[action]
