"""Protected Phase 4A Signals Admin endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field, model_validator

from services.admin_auth_api import _bearer_token, _request_id, _require_bff, _require_identity
from services.admin_auth_service import AdminIdentity
from services.admin_signals_service import (
    SignalConflictError, SignalNotFoundError, create_admin_signal, delete_admin_signal,
    duplicate_admin_signal, get_admin_signal, get_public_signal, list_admin_signals, list_public_signals,
    transition_admin_signal, update_admin_signal,
)


LOGGER = logging.getLogger(__name__)
router = APIRouter(tags=["signals"])


class SignalPayload(BaseModel):
    symbol: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9/._-]+$")
    market: str = Field(default="FOREX", min_length=2, max_length=30)
    direction: Literal["BUY", "SELL"]
    timeframe: str = Field(default="INTRADAY", min_length=1, max_length=30)
    entry_type: Literal["MARKET", "LIMIT", "STOP", "RANGE"] = "MARKET"
    entry_price: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    entry_price_min: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    entry_price_max: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    stop_loss: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    target_1: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    target_2: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    target_3: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    target_4: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    confidence_label: str = Field(default="", max_length=60)
    analysis_summary: str = Field(default="", max_length=4_000)
    technical_reason: str = Field(default="", max_length=10_000)
    astrology_reason: str = Field(default="", max_length=10_000)
    risk_note: str = Field(default="", max_length=4_000)
    publication_status: Literal["DRAFT", "SCHEDULED"] = "DRAFT"
    scheduled_at: datetime | None = None
    expires_at: datetime | None = None
    featured: bool = False

    @model_validator(mode="after")
    def validate_levels(self) -> "SignalPayload":
        if self.entry_type == "RANGE":
            if self.entry_price_min is None or self.entry_price_max is None or self.entry_price_min > self.entry_price_max:
                raise ValueError("A valid minimum and maximum are required for range entries.")
        targets = [value for value in (self.target_1, self.target_2, self.target_3, self.target_4) if value is not None]
        if self.direction == "BUY":
            if self.stop_loss is not None and self.stop_loss >= self.entry_price: raise ValueError("BUY stop loss must be below entry.")
            if any(target <= self.entry_price for target in targets): raise ValueError("BUY targets must be above entry.")
            if targets != sorted(targets): raise ValueError("BUY targets must increase in order.")
        else:
            if self.stop_loss is not None and self.stop_loss <= self.entry_price: raise ValueError("SELL stop loss must be above entry.")
            if any(target >= self.entry_price for target in targets): raise ValueError("SELL targets must be below entry.")
            if targets != sorted(targets, reverse=True): raise ValueError("SELL targets must decrease in order.")
        if self.publication_status == "SCHEDULED" and self.scheduled_at is None: raise ValueError("Scheduled signals require a scheduled time.")
        if self.expires_at and self.scheduled_at and self.expires_at <= self.scheduled_at:
            raise ValueError("Expiration must be after the scheduled publication time.")
        return self


class TransitionPayload(BaseModel):
    action: Literal["PUBLISH", "SCHEDULE", "UNPUBLISH", "ACTIVATE", "TARGET_HIT", "STOPPED", "CANCEL", "EXPIRE", "CLOSE"]
    outcome: str | None = Field(default=None, max_length=120)
    result_points: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)


def _identity(authorization: str | None, secret: str | None) -> AdminIdentity:
    _require_bff(secret); return _require_identity(_bearer_token(authorization))


def _safe(callback: Any) -> Any:
    try: return callback()
    except SignalNotFoundError as exc: raise HTTPException(404, str(exc)) from exc
    except SignalConflictError as exc: raise HTTPException(409, str(exc)) from exc
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    except HTTPException: raise
    except Exception as exc: LOGGER.exception("Signals operation failed safely"); raise HTTPException(503, "Signals service is temporarily unavailable.") from exc


@router.get("/admin/signals")
def admin_signal_list(response: Response, page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=50), search: str=Query("",max_length=120), status: str="all", direction: str="all", symbol: str="", timeframe: str="all", date_filter: str="all", sort: str="updated_desc", authorization: Annotated[str|None,Header()]=None, x_admin_bff_key: Annotated[str|None,Header()]=None) -> dict[str,Any]:
    _identity(authorization,x_admin_bff_key); response.headers["Cache-Control"]="private, no-store"; return _safe(lambda:list_admin_signals(page=page,page_size=page_size,search=search,status=status,direction=direction,symbol=symbol,timeframe=timeframe,date_filter=date_filter,sort=sort))

@router.post("/admin/signals", status_code=201)
def admin_signal_create(payload: SignalPayload, authorization: Annotated[str|None,Header()]=None, x_admin_bff_key: Annotated[str|None,Header()]=None, x_request_id: Annotated[str|None,Header()]=None) -> dict[str,Any]:
    identity=_identity(authorization,x_admin_bff_key); return _safe(lambda:create_admin_signal(actor_id=identity.user_id,request_id=_request_id(x_request_id),values=payload.model_dump()))

@router.get("/admin/signals/{signal_id}")
def admin_signal_detail(signal_id:int,response:Response,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None)->dict[str,Any]:
    _identity(authorization,x_admin_bff_key); response.headers["Cache-Control"]="private, no-store"; return _safe(lambda:get_admin_signal(signal_id))

@router.patch("/admin/signals/{signal_id}")
def admin_signal_update(signal_id:int,payload:SignalPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None)->dict[str,Any]:
    identity=_identity(authorization,x_admin_bff_key); return _safe(lambda:update_admin_signal(signal_id=signal_id,actor_id=identity.user_id,request_id=_request_id(x_request_id),values=payload.model_dump()))

@router.post("/admin/signals/{signal_id}/duplicate")
def admin_signal_duplicate(signal_id:int,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None)->dict[str,Any]:
    identity=_identity(authorization,x_admin_bff_key); return _safe(lambda:duplicate_admin_signal(signal_id=signal_id,actor_id=identity.user_id,request_id=_request_id(x_request_id)))

@router.post("/admin/signals/{signal_id}/transition")
def admin_signal_transition(signal_id:int,payload:TransitionPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None)->dict[str,Any]:
    identity=_identity(authorization,x_admin_bff_key); return _safe(lambda:transition_admin_signal(signal_id=signal_id,action=payload.action,actor_id=identity.user_id,request_id=_request_id(x_request_id),outcome=payload.outcome,result_points=payload.result_points))

@router.post("/admin/signals/{signal_id}/{action}")
def admin_signal_simple_transition(signal_id:int,action:str,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None)->dict[str,Any]:
    mapped={"publish":"PUBLISH","unpublish":"UNPUBLISH","trash":"TRASH","restore":"RESTORE"}.get(action);
    if not mapped: raise HTTPException(404,"Signal action was not found.")
    identity=_identity(authorization,x_admin_bff_key); return _safe(lambda:transition_admin_signal(signal_id=signal_id,action=mapped,actor_id=identity.user_id,request_id=_request_id(x_request_id)))

@router.delete("/admin/signals/{signal_id}")
def admin_signal_delete(signal_id:int,confirmed:bool=Query(False),authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None)->dict[str,Any]:
    identity=_identity(authorization,x_admin_bff_key); return _safe(lambda:delete_admin_signal(signal_id=signal_id,actor_id=identity.user_id,request_id=_request_id(x_request_id),confirmed=confirmed))

@router.get("/public/signals/v2")
def public_signal_list(response:Response,page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=24),status:str="all",symbol:str="",direction:str="all")->dict[str,Any]:
    response.headers["Cache-Control"]="public, max-age=15, s-maxage=30, stale-while-revalidate=120"; return _safe(lambda:list_public_signals(page=page,page_size=page_size,status=status,symbol=symbol,direction=direction))

@router.get("/public/signals/v2/{public_id}")
def public_signal_detail(public_id:str,response:Response)->dict[str,Any]:
    response.headers["Cache-Control"]="public, max-age=15, s-maxage=30, stale-while-revalidate=120"; return {"item":_safe(lambda:get_public_signal(public_id))}
