"""Protected Phase 4B administration and privacy-minimized public endpoints."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
import logging
from typing import Annotated, Any, Callable, Literal
from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field
from services.admin_auth_api import _bearer_token, _request_id, _require_bff, _require_identity
from services.admin_publications_service import *

LOGGER=logging.getLogger(__name__)
admin=APIRouter(prefix="/admin",tags=["admin-publications"])
public=APIRouter(prefix="/public",tags=["public-publications"])

class AnnouncementPayload(BaseModel):
    title:str=Field(min_length=3,max_length=240); slug:str=""; summary:str=Field(default="",max_length=500); body:str=Field(default="",max_length=100000)
    announcement_type:Literal["PLATFORM_UPDATE","MARKET_NOTICE","SIGNAL_UPDATE","SERVICE_NOTICE","EDUCATION","EVENT","GENERAL"]="GENERAL"
    priority:Literal["NORMAL","IMPORTANT","URGENT"]="NORMAL"; audience:Literal["PUBLIC","MEMBERS","ALL"]="PUBLIC"
    featured:bool=False; pinned:bool=False; cta_label:str|None=Field(None,max_length=80); cta_url:str|None=Field(None,max_length=2048); media_id:int|None=Field(None,ge=1); scheduled_at:datetime|None=None; expires_at:datetime|None=None

class ResultPayload(BaseModel):
    related_signal_id:int|None=Field(None,ge=1); symbol:str=Field(min_length=2,max_length=30); direction:Literal["BUY","SELL"]; timeframe:str|None=Field(None,max_length=30)
    entry_price:Decimal=Field(gt=0,max_digits=18,decimal_places=6); exit_price:Decimal=Field(gt=0,max_digits=18,decimal_places=6); stop_loss:Decimal|None=Field(None,gt=0,max_digits=18,decimal_places=6); targets:list[Decimal]=Field(default_factory=list,max_length=4)
    lifecycle_outcome:str=Field(min_length=2,max_length=60); result_unit:Literal["POINTS","PIPS"]="POINTS"; opened_at:datetime; closed_at:datetime
    evidence_type:str|None=Field(None,max_length=80); evidence_media_id:int|None=Field(None,ge=1); evidence_notes:str|None=Field(None,max_length=4000); redaction_confirmed:bool=False
    compliance_status:Literal["PENDING","PASSED","FAILED"]="PENDING"; compliance_notes:str|None=Field(None,max_length=4000); public_summary:str=Field(default="",max_length=2000); featured:bool=False

class ActionPayload(BaseModel): action:str=Field(min_length=2,max_length=30); reason:str|None=Field(None,max_length=2000)

def ident(auth:str|None,key:str|None): _require_bff(key); return _require_identity(_bearer_token(auth))
def safe(fn:Callable[[],Any]):
    try:return fn()
    except PublicationNotFound as e: raise HTTPException(404,str(e)) from e
    except PublicationConflict as e: raise HTTPException(409,str(e)) from e
    except ValueError as e: raise HTTPException(400,str(e)) from e
    except HTTPException: raise
    except Exception as e: LOGGER.exception("Publication operation failed safely");raise HTTPException(503,"Publication service is temporarily unavailable.") from e

@admin.get("/announcements")
def announcements_list(response:Response,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=50),search:str=Query("",max_length=120),status:str="all",kind:str="all",priority:str="all",audience:str="all",authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None):
    ident(authorization,x_admin_bff_key);response.headers["Cache-Control"]="private, no-store";return safe(lambda:list_announcements(page=page,page_size=page_size,search=search,status=status,kind=kind,priority=priority,audience=audience))
@admin.post("/announcements",status_code=201)
def announcements_create(payload:AnnouncementPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:save_announcement(actor_id=i.user_id,request_id=_request_id(x_request_id),**payload.model_dump()))
@admin.get("/announcements/{item_id}")
def announcements_detail(item_id:int,response:Response,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None):
    ident(authorization,x_admin_bff_key);response.headers["Cache-Control"]="private, no-store";return safe(lambda:get_announcement(item_id))
@admin.patch("/announcements/{item_id}")
def announcements_update(item_id:int,payload:AnnouncementPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:save_announcement(item_id=item_id,actor_id=i.user_id,request_id=_request_id(x_request_id),**payload.model_dump()))
@admin.post("/announcements/{item_id}/transition")
def announcements_transition(item_id:int,payload:ActionPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:transition_announcement(item_id=item_id,action=payload.action,actor_id=i.user_id,request_id=_request_id(x_request_id)))
@admin.post("/announcements/{item_id}/duplicate")
def announcements_duplicate(item_id:int,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:duplicate_announcement(item_id=item_id,actor_id=i.user_id,request_id=_request_id(x_request_id)))
@admin.delete("/announcements/{item_id}")
def announcements_delete(item_id:int,confirmed:bool=False,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:delete_announcement(item_id=item_id,actor_id=i.user_id,request_id=_request_id(x_request_id),confirmed=confirmed))

@admin.get("/results")
def results_list(response:Response,page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=50),search:str=Query("",max_length=120),verification:str="all",publication:str="all",symbol:str="",outcome:str="all",authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None):
    ident(authorization,x_admin_bff_key);response.headers["Cache-Control"]="private, no-store";return safe(lambda:list_results(page=page,page_size=page_size,search=search,verification=verification,publication=publication,symbol=symbol,outcome=outcome))
@admin.post("/results",status_code=201)
def results_create(payload:ResultPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:save_result(actor_id=i.user_id,request_id=_request_id(x_request_id),**payload.model_dump()))
@admin.get("/results/{item_id}")
def results_detail(item_id:int,response:Response,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None):
    ident(authorization,x_admin_bff_key);response.headers["Cache-Control"]="private, no-store";return safe(lambda:get_result(item_id))
@admin.patch("/results/{item_id}")
def results_update(item_id:int,payload:ResultPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:save_result(item_id=item_id,actor_id=i.user_id,request_id=_request_id(x_request_id),**payload.model_dump()))
@admin.post("/results/{item_id}/transition")
def results_transition(item_id:int,payload:ActionPayload,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:transition_result(item_id=item_id,action=payload.action,reason=payload.reason,actor_id=i.user_id,request_id=_request_id(x_request_id)))
@admin.delete("/results/{item_id}")
def results_delete(item_id:int,confirmed:bool=False,authorization:Annotated[str|None,Header()]=None,x_admin_bff_key:Annotated[str|None,Header()]=None,x_request_id:Annotated[str|None,Header()]=None):
    i=ident(authorization,x_admin_bff_key);return safe(lambda:delete_result(item_id=item_id,actor_id=i.user_id,request_id=_request_id(x_request_id),confirmed=confirmed))

@public.get("/announcements/v2")
def public_announcements(response:Response,page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=24),kind:str="all",priority:str="all"):
    response.headers["Cache-Control"]="public, max-age=30, s-maxage=120, stale-while-revalidate=300";return safe(lambda:list_public_announcements(page=page,page_size=page_size,kind=kind,priority=priority))
@public.get("/announcements/v2/{slug}")
def public_announcement(slug:str,response:Response): response.headers["Cache-Control"]="public, max-age=30, s-maxage=120";return {"item":safe(lambda:get_public_announcement(slug))}
@public.get("/results")
def public_results(response:Response,page:int=Query(1,ge=1),page_size:int=Query(12,ge=1,le=24),symbol:str="",outcome:str="all"):
    response.headers["Cache-Control"]="public, max-age=30, s-maxage=120, stale-while-revalidate=300";return safe(lambda:list_public_results(page=page,page_size=page_size,symbol=symbol,outcome=outcome))
@public.get("/results/{public_id}")
def public_result(public_id:str,response:Response): response.headers["Cache-Control"]="public, max-age=30, s-maxage=120";return {"item":safe(lambda:get_public_result(public_id))}
