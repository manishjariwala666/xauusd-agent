"""Compliance-first announcement and verified-result persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json, re
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from core.database import session_scope

ANNOUNCEMENT_STATES = {"DRAFT", "SCHEDULED", "PUBLISHED", "EXPIRED", "ARCHIVED", "TRASHED"}
ANNOUNCEMENT_TRANSITIONS = {
    "DRAFT": {"SCHEDULE", "PUBLISH", "TRASH"}, "SCHEDULED": {"PUBLISH", "UNPUBLISH", "EXPIRE", "TRASH"},
    "PUBLISHED": {"UNPUBLISH", "EXPIRE", "ARCHIVE", "TRASH"}, "EXPIRED": {"ARCHIVE", "TRASH"},
    "ARCHIVED": {"TRASH"}, "TRASHED": {"RESTORE"},
}
RESULT_TRANSITIONS = {
    "DRAFT": {"REQUEST_EVIDENCE", "SUBMIT", "TRASH"}, "PENDING_EVIDENCE": {"SUBMIT", "TRASH"},
    "PENDING_REVIEW": {"VERIFY", "REJECT", "TRASH"}, "VERIFIED": {"PUBLISH", "ARCHIVE", "TRASH"},
    "REJECTED": {"RESTORE", "TRASH"}, "ARCHIVED": {"TRASH"}, "TRASHED": {"RESTORE"},
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

class PublicationNotFound(ValueError): pass
class PublicationConflict(ValueError): pass

def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not value or len(value) > 160 or not SLUG.fullmatch(value): raise ValueError("Enter a valid slug.")
    return value

def _audit(session: Any, actor: int, event: str, request_id: str, details: dict[str, Any]) -> None:
    session.execute(text("INSERT INTO public.admin_auth_audit_events(user_id,event_type,outcome,request_id,details) VALUES (:u,:e,'SUCCESS',:r,CAST(:d AS JSONB))"), {"u":actor,"e":event,"r":request_id,"d":json.dumps(details)})

def _safe_cta(value: str | None) -> str | None:
    if not value: return None
    parsed=urlparse(value)
    if parsed.scheme not in {"https"} or not parsed.netloc: raise ValueError("CTA URL must be a valid HTTPS URL.")
    return value

def list_announcements(*, page:int,page_size:int,search:str="",status:str="all",kind:str="all",priority:str="all",audience:str="all") -> dict[str,Any]:
    page=max(1,page); page_size=max(1,min(50,page_size)); clauses=["content_type='ANNOUNCEMENT'"]; p={"l":page_size,"o":(page-1)*page_size}
    for field,value in (("status",status),("announcement_type",kind),("announcement_priority",priority),("announcement_audience",audience)):
        if value.lower()!="all": clauses.append(f"UPPER({field})=:{field}"); p[field]=value.upper()
    if search.strip(): clauses.append("(title ILIKE :q OR slug ILIKE :q OR excerpt ILIKE :q)"); p["q"]=f"%{search.strip()[:120]}%"
    where=" AND ".join(clauses)
    fields="id,slug,title,excerpt AS summary,body,announcement_type,announcement_priority AS priority,announcement_audience AS audience,status,featured,pinned,cta_label,cta_url,media_id,scheduled_at,published_at,expires_at,created_at,updated_at,deleted_at"
    with session_scope() as s:
        total=s.execute(text(f"SELECT COUNT(*) FROM content_items WHERE {where}"),p).scalar_one()
        items=s.execute(text(f"SELECT {fields} FROM content_items WHERE {where} ORDER BY pinned DESC,updated_at DESC,id DESC LIMIT :l OFFSET :o"),p).mappings().all()
        stats=dict(s.execute(text("SELECT status,COUNT(*) n FROM content_items WHERE content_type='ANNOUNCEMENT' GROUP BY status")).all())
    return {"items":[dict(x) for x in items],"page":page,"page_size":page_size,"total":int(total),"pages":max(1,(int(total)+page_size-1)//page_size),"stats":{"total":sum(stats.values()),**{k.lower():int(v) for k,v in stats.items()}}}

def get_announcement(item_id:int) -> dict[str,Any]:
    data=list_announcements(page=1,page_size=1,search="")
    with session_scope() as s: row=s.execute(text("SELECT id,slug,title,excerpt AS summary,body,announcement_type,announcement_priority AS priority,announcement_audience AS audience,status,featured,pinned,cta_label,cta_url,media_id,scheduled_at,published_at,expires_at,created_at,updated_at,deleted_at FROM content_items WHERE id=:id AND content_type='ANNOUNCEMENT'"),{"id":item_id}).mappings().first()
    if not row: raise PublicationNotFound("Announcement was not found.")
    return dict(row)

def save_announcement(*,actor_id:int,request_id:str,item_id:int|None=None,**v:Any)->dict[str,Any]:
    title=str(v["title"]).strip(); summary=str(v.get("summary") or "").strip(); body=str(v.get("body") or "").strip()
    if not 3<=len(title)<=240: raise ValueError("Title must be between 3 and 240 characters.")
    if len(summary)>500: raise ValueError("Summary cannot exceed 500 characters.")
    if "<script" in body.lower(): raise ValueError("Executable HTML is not allowed.")
    scheduled=v.get("scheduled_at"); expires=v.get("expires_at")
    if scheduled and expires and expires<=scheduled: raise ValueError("Expiry must be after schedule time.")
    params={"slug":_slug(v.get("slug") or title),"title":title,"summary":summary,"body":body,"type":str(v.get("announcement_type") or "GENERAL").upper(),"priority":str(v.get("priority") or "NORMAL").upper(),"audience":str(v.get("audience") or "PUBLIC").upper(),"featured":bool(v.get("featured")),"pinned":bool(v.get("pinned")),"cta_label":str(v.get("cta_label") or "").strip()[:80] or None,"cta_url":_safe_cta(v.get("cta_url")),"media_id":v.get("media_id"),"scheduled":scheduled,"expires":expires,"actor":actor_id}
    with session_scope() as s:
        if item_id is None:
            item_id=s.execute(text("""INSERT INTO content_items(content_type,slug,status,title,excerpt,body,is_public,is_published,announcement_type,announcement_priority,announcement_audience,featured,pinned,cta_label,cta_url,media_id,scheduled_at,expires_at,created_by,updated_by) VALUES ('ANNOUNCEMENT',:slug,'DRAFT',:title,:summary,:body,TRUE,FALSE,:type,:priority,:audience,:featured,:pinned,:cta_label,:cta_url,:media_id,:scheduled,:expires,:actor,:actor) RETURNING id"""),params).scalar_one()
        else:
            state=s.execute(text("SELECT status FROM content_items WHERE id=:id AND content_type='ANNOUNCEMENT' FOR UPDATE"),{"id":item_id}).scalar_one_or_none()
            if state not in {"DRAFT","SCHEDULED"}: raise PublicationConflict("Only draft or scheduled announcements can be edited.")
            params["id"]=item_id; s.execute(text("""UPDATE content_items SET slug=:slug,title=:title,excerpt=:summary,body=:body,announcement_type=:type,announcement_priority=:priority,announcement_audience=:audience,featured=:featured,pinned=:pinned,cta_label=:cta_label,cta_url=:cta_url,media_id=:media_id,scheduled_at=:scheduled,expires_at=:expires,updated_by=:actor,updated_at=NOW() WHERE id=:id"""),params)
        _audit(s,actor_id,"ANNOUNCEMENT_SAVED",request_id,{"announcement_id":item_id})
    return get_announcement(int(item_id))

def transition_announcement(*,item_id:int,action:str,actor_id:int,request_id:str)->dict[str,Any]:
    action=action.upper(); now=datetime.now(timezone.utc)
    with session_scope() as s:
        row=s.execute(text("SELECT status,title,excerpt,body,scheduled_at,expires_at FROM content_items WHERE id=:id AND content_type='ANNOUNCEMENT' FOR UPDATE"),{"id":item_id}).mappings().first()
        if not row: raise PublicationNotFound("Announcement was not found.")
        state=str(row["status"]).upper()
        if action not in ANNOUNCEMENT_TRANSITIONS.get(state,set()): raise PublicationConflict(f"Cannot {action.lower()} a {state.lower()} announcement.")
        if action=="PUBLISH" and (not row["title"] or not row["excerpt"] or not row["body"]): raise PublicationConflict("Title, summary and body are required before publishing.")
        if action=="SCHEDULE" and not row["scheduled_at"]: raise PublicationConflict("A schedule time is required.")
        values={"SCHEDULE":("SCHEDULED",False,None,None),"PUBLISH":("PUBLISHED",True,now,None),"UNPUBLISH":("DRAFT",False,None,None),"EXPIRE":("EXPIRED",False,None,None),"ARCHIVE":("ARCHIVED",False,None,None),"TRASH":("TRASHED",False,None,now),"RESTORE":("DRAFT",False,None,None)}[action]
        s.execute(text("UPDATE content_items SET status=:st,is_published=:pub,published_at=COALESCE(:at,published_at),deleted_at=:deleted,updated_by=:actor,updated_at=NOW() WHERE id=:id"),{"st":values[0],"pub":values[1],"at":values[2],"deleted":values[3],"actor":actor_id,"id":item_id})
        _audit(s,actor_id,f"ANNOUNCEMENT_{action}",request_id,{"announcement_id":item_id,"from":state,"to":values[0]})
    return get_announcement(item_id)

def duplicate_announcement(*,item_id:int,actor_id:int,request_id:str)->dict[str,Any]:
    with session_scope() as s:
        new=s.execute(text("""INSERT INTO content_items(content_type,slug,status,title,excerpt,body,is_public,is_published,announcement_type,announcement_priority,announcement_audience,featured,pinned,cta_label,cta_url,media_id,created_by,updated_by) SELECT 'ANNOUNCEMENT',slug||'-copy-'||id,'DRAFT',title||' (Copy)',excerpt,body,TRUE,FALSE,announcement_type,announcement_priority,announcement_audience,FALSE,FALSE,cta_label,cta_url,media_id,:actor,:actor FROM content_items WHERE id=:id AND content_type='ANNOUNCEMENT' RETURNING id"""),{"id":item_id,"actor":actor_id}).scalar_one_or_none()
        if not new: raise PublicationNotFound("Announcement was not found.")
        _audit(s,actor_id,"ANNOUNCEMENT_DUPLICATED",request_id,{"announcement_id":item_id,"duplicate_id":new})
    return get_announcement(int(new))

def delete_announcement(*,item_id:int,actor_id:int,request_id:str,confirmed:bool)->dict[str,Any]:
    if not confirmed: raise ValueError("Permanent deletion requires confirmation.")
    with session_scope() as s:
        state=s.execute(text("SELECT status FROM content_items WHERE id=:id AND content_type='ANNOUNCEMENT' FOR UPDATE"),{"id":item_id}).scalar_one_or_none()
        if state is None: raise PublicationNotFound("Announcement was not found.")
        if state!="TRASHED": raise PublicationConflict("Only trashed announcements can be permanently deleted.")
        _audit(s,actor_id,"ANNOUNCEMENT_DELETED",request_id,{"announcement_id":item_id});s.execute(text("DELETE FROM content_items WHERE id=:id"),{"id":item_id})
    return {"deleted":True}

def calculate_points(direction:str,entry:Any,exit_price:Any)->Decimal:
    try: e=Decimal(str(entry)); x=Decimal(str(exit_price))
    except InvalidOperation as exc: raise ValueError("Prices must be valid decimals.") from exc
    if e<=0 or x<=0: raise ValueError("Prices must be positive.")
    return (x-e if direction.upper()=="BUY" else e-x).quantize(Decimal("0.000001"))

def list_results(*,page:int,page_size:int,search:str="",verification:str="all",publication:str="all",symbol:str="",outcome:str="all") -> dict[str,Any]:
    page=max(1,page);page_size=max(1,min(50,page_size));c=["1=1"];p={"l":page_size,"o":(page-1)*page_size}
    for f,v in (("verification_status",verification),("publication_status",publication),("lifecycle_outcome",outcome)):
        if v.lower()!="all":c.append(f"{f}=:{f}");p[f]=v.upper()
    if symbol.strip():c.append("symbol ILIKE :symbol");p["symbol"]=f"%{symbol.strip()[:30]}%"
    if search.strip():c.append("(symbol ILIKE :q OR public_summary ILIKE :q OR CAST(public_id AS TEXT) ILIKE :q)");p["q"]=f"%{search.strip()[:120]}%"
    where=" AND ".join(c); fields="id,public_id,related_signal_id,symbol,direction,timeframe,entry_price,exit_price,stop_loss,targets,lifecycle_outcome,result_unit,result_value,result_points,result_percentage,calculation_basis,opened_at,closed_at,evidence_type,evidence_media_id,evidence_notes,redaction_confirmed,verification_status,rejection_reason,verified_at,compliance_status,compliance_notes,public_summary,featured,publication_status,published_at,created_at,updated_at,deleted_at"
    with session_scope() as s:
        total=s.execute(text(f"SELECT COUNT(*) FROM verified_results WHERE {where}"),p).scalar_one();rows=s.execute(text(f"SELECT {fields} FROM verified_results WHERE {where} ORDER BY updated_at DESC,id DESC LIMIT :l OFFSET :o"),p).mappings().all();stats=dict(s.execute(text("SELECT verification_status,COUNT(*) FROM verified_results GROUP BY verification_status")).all());published=s.execute(text("SELECT COUNT(*) FROM verified_results WHERE publication_status='PUBLISHED'")).scalar_one()
    return {"items":[dict(x) for x in rows],"page":page,"page_size":page_size,"total":int(total),"pages":max(1,(int(total)+page_size-1)//page_size),"stats":{"total":sum(stats.values()),"published":int(published),**{k.lower():int(v) for k,v in stats.items()}}}

def get_result(item_id:int)->dict[str,Any]:
    with session_scope() as s: row=s.execute(text("SELECT * FROM verified_results WHERE id=:id"),{"id":item_id}).mappings().first()
    if not row: raise PublicationNotFound("Verified result was not found.")
    return dict(row)

def save_result(*,actor_id:int,request_id:str,item_id:int|None=None,**v:Any)->dict[str,Any]:
    direction=str(v["direction"]).upper(); points=calculate_points(direction,v["entry_price"],v["exit_price"])
    opened=v["opened_at"];closed=v["closed_at"]
    if closed<opened: raise ValueError("Closed time cannot precede opened time.")
    summary=str(v.get("public_summary") or "").strip()
    if "<script" in summary.lower(): raise ValueError("Executable HTML is not allowed.")
    sensitive=f"{v.get('evidence_notes') or ''} {summary}".lower()
    if re.search(r"(?:account|client|login|password)\s*(?:number|id|name|:)",sensitive): raise ValueError("Remove account, client, login or credential identifiers before saving.")
    p={**v,"direction":direction,"points":points,"symbol":str(v["symbol"]).upper().strip(),"targets":json.dumps([str(x) for x in (v.get("targets") or [])]),"actor":actor_id,"summary":summary}
    with session_scope() as s:
        if v.get("evidence_media_id") and not s.execute(text("SELECT 1 FROM media_assets WHERE id=:id AND deleted_at IS NULL"),{"id":v["evidence_media_id"]}).scalar_one_or_none(): raise ValueError("Evidence media is unavailable.")
        if item_id is None:
            item_id=s.execute(text("""INSERT INTO verified_results(related_signal_id,symbol,direction,timeframe,entry_price,exit_price,stop_loss,targets,lifecycle_outcome,result_unit,result_value,result_points,opened_at,closed_at,evidence_type,evidence_media_id,evidence_notes,redaction_confirmed,compliance_status,compliance_notes,public_summary,featured,created_by,updated_by) VALUES (:related_signal_id,:symbol,:direction,:timeframe,:entry_price,:exit_price,:stop_loss,CAST(:targets AS JSONB),:lifecycle_outcome,:result_unit,:points,:points,:opened_at,:closed_at,:evidence_type,:evidence_media_id,:evidence_notes,:redaction_confirmed,:compliance_status,:compliance_notes,:summary,:featured,:actor,:actor) RETURNING id"""),p).scalar_one()
        else:
            state=s.execute(text("SELECT verification_status FROM verified_results WHERE id=:id FOR UPDATE"),{"id":item_id}).scalar_one_or_none()
            if state not in {"DRAFT","PENDING_EVIDENCE","REJECTED"}: raise PublicationConflict("This result is locked for review.")
            p["id"]=item_id;s.execute(text("""UPDATE verified_results SET related_signal_id=:related_signal_id,symbol=:symbol,direction=:direction,timeframe=:timeframe,entry_price=:entry_price,exit_price=:exit_price,stop_loss=:stop_loss,targets=CAST(:targets AS JSONB),lifecycle_outcome=:lifecycle_outcome,result_unit=:result_unit,result_value=:points,result_points=:points,opened_at=:opened_at,closed_at=:closed_at,evidence_type=:evidence_type,evidence_media_id=:evidence_media_id,evidence_notes=:evidence_notes,redaction_confirmed=:redaction_confirmed,compliance_status=:compliance_status,compliance_notes=:compliance_notes,public_summary=:summary,featured=:featured,updated_by=:actor,updated_at=NOW() WHERE id=:id"""),p)
        _audit(s,actor_id,"RESULT_SAVED",request_id,{"result_id":item_id})
    return get_result(int(item_id))

def transition_result(*,item_id:int,action:str,actor_id:int,request_id:str,reason:str|None=None)->dict[str,Any]:
    action=action.upper();now=datetime.now(timezone.utc)
    with session_scope() as s:
        r=s.execute(text("SELECT * FROM verified_results WHERE id=:id FOR UPDATE"),{"id":item_id}).mappings().first()
        if not r: raise PublicationNotFound("Verified result was not found.")
        state=str(r["verification_status"])
        if action=="COMPLIANCE_PASS" and state=="PENDING_REVIEW":
            s.execute(text("UPDATE verified_results SET compliance_status='PASSED',compliance_notes=:reason,updated_by=:a,updated_at=NOW() WHERE id=:id"),{"reason":reason,"a":actor_id,"id":item_id})
        elif action=="COMPLIANCE_FAIL" and state=="PENDING_REVIEW":
            s.execute(text("UPDATE verified_results SET compliance_status='FAILED',compliance_notes=:reason,updated_by=:a,updated_at=NOW() WHERE id=:id"),{"reason":reason,"a":actor_id,"id":item_id})
        elif action=="UNPUBLISH" and r["publication_status"]=="PUBLISHED":
            s.execute(text("UPDATE verified_results SET publication_status='UNPUBLISHED',published_at=NULL,updated_by=:a,updated_at=NOW() WHERE id=:id"),{"a":actor_id,"id":item_id})
        else:
            if action not in RESULT_TRANSITIONS.get(state,set()): raise PublicationConflict(f"Cannot {action.lower()} a {state.lower()} result.")
            if action in {"SUBMIT","VERIFY","PUBLISH"} and (not r["evidence_media_id"] or not r["redaction_confirmed"]): raise PublicationConflict("Redacted evidence and privacy confirmation are required.")
            if action=="VERIFY" and r["compliance_status"]!="PASSED": raise PublicationConflict("Compliance review must pass before verification.")
            if action=="PUBLISH" and (state!="VERIFIED" or not r["public_summary"]): raise PublicationConflict("Only a verified result with a public summary can be published.")
            vals={"REQUEST_EVIDENCE":("PENDING_EVIDENCE",r["publication_status"],None,None),"SUBMIT":("PENDING_REVIEW",r["publication_status"],None,None),"VERIFY":("VERIFIED",r["publication_status"],now,None),"REJECT":("REJECTED","DRAFT",None,None),"PUBLISH":("VERIFIED","PUBLISHED",r["verified_at"],now),"ARCHIVE":("ARCHIVED","ARCHIVED",r["verified_at"],None),"TRASH":("TRASHED","TRASHED",r["verified_at"],None),"RESTORE":("DRAFT","DRAFT",None,None)}[action]
            s.execute(text("UPDATE verified_results SET verification_status=:v,publication_status=:p,verified_by=CASE WHEN :v='VERIFIED' THEN :a ELSE verified_by END,verified_at=:verified,published_at=:published,rejection_reason=:reason,deleted_at=CASE WHEN :v='TRASHED' THEN NOW() ELSE NULL END,updated_by=:a,updated_at=NOW() WHERE id=:id"),{"v":vals[0],"p":vals[1],"verified":vals[2],"published":vals[3],"reason":reason,"a":actor_id,"id":item_id})
        _audit(s,actor_id,f"RESULT_{action}",request_id,{"result_id":item_id,"from":state})
    return get_result(item_id)

def delete_result(*,item_id:int,actor_id:int,request_id:str,confirmed:bool)->dict[str,Any]:
    if not confirmed: raise ValueError("Permanent deletion requires confirmation.")
    with session_scope() as s:
        state=s.execute(text("SELECT verification_status FROM verified_results WHERE id=:id FOR UPDATE"),{"id":item_id}).scalar_one_or_none()
        if state is None: raise PublicationNotFound("Verified result was not found.")
        if state!="TRASHED": raise PublicationConflict("Only trashed results can be permanently deleted.")
        _audit(s,actor_id,"RESULT_DELETED",request_id,{"result_id":item_id});s.execute(text("DELETE FROM verified_results WHERE id=:id"),{"id":item_id})
    return {"deleted":True}

def list_public_announcements(*,page:int,page_size:int,kind:str="all",priority:str="all")->dict[str,Any]:
    page=max(1,page);page_size=max(1,min(24,page_size));c=["content_type='ANNOUNCEMENT'","status='PUBLISHED'","is_public=TRUE","is_published=TRUE","deleted_at IS NULL","(expires_at IS NULL OR expires_at>NOW())"];p={"l":page_size,"o":(page-1)*page_size}
    for f,v in (("announcement_type",kind),("announcement_priority",priority)):
        if v.lower()!="all":c.append(f"{f}=:{f}");p[f]=v.upper()
    w=" AND ".join(c);fields="slug,title,excerpt AS summary,announcement_type AS type,announcement_priority AS priority,pinned,featured,published_at,expires_at"
    with session_scope() as s: total=s.execute(text(f"SELECT COUNT(*) FROM content_items WHERE {w}"),p).scalar_one(); rows=s.execute(text(f"SELECT {fields} FROM content_items WHERE {w} ORDER BY pinned DESC,published_at DESC,id DESC LIMIT :l OFFSET :o"),p).mappings().all()
    return {"items":[dict(x) for x in rows],"page":page,"page_size":page_size,"total":int(total),"pages":max(1,(int(total)+page_size-1)//page_size)}

def get_public_announcement(slug:str)->dict[str,Any]:
    with session_scope() as s: row=s.execute(text("""SELECT slug,title,excerpt AS summary,body,announcement_type AS type,announcement_priority AS priority,pinned,featured,cta_label,cta_url,published_at,expires_at FROM content_items WHERE slug=:slug AND content_type='ANNOUNCEMENT' AND status='PUBLISHED' AND is_public=TRUE AND is_published=TRUE AND deleted_at IS NULL AND (expires_at IS NULL OR expires_at>NOW())"""),{"slug":slug}).mappings().first()
    if not row: raise PublicationNotFound("Public announcement was not found.")
    return dict(row)

def list_public_results(*,page:int,page_size:int,symbol:str="",outcome:str="all")->dict[str,Any]:
    page=max(1,page);page_size=max(1,min(24,page_size));c=["publication_status='PUBLISHED'","verification_status='VERIFIED'","compliance_status='PASSED'","redaction_confirmed=TRUE","deleted_at IS NULL"];p={"l":page_size,"o":(page-1)*page_size}
    if symbol.strip():c.append("symbol ILIKE :symbol");p["symbol"]=f"%{symbol.strip()[:30]}%"
    if outcome.lower()!="all":c.append("lifecycle_outcome=:outcome");p["outcome"]=outcome.upper()
    w=" AND ".join(c); fields="public_id,symbol,direction,timeframe,entry_price,exit_price,result_points,result_unit,lifecycle_outcome,evidence_type,verified_at,published_at,opened_at,closed_at,public_summary,featured"
    with session_scope() as s: total=s.execute(text(f"SELECT COUNT(*) FROM verified_results WHERE {w}"),p).scalar_one();rows=s.execute(text(f"SELECT {fields} FROM verified_results WHERE {w} ORDER BY featured DESC,published_at DESC,id DESC LIMIT :l OFFSET :o"),p).mappings().all()
    return {"items":[dict(x) for x in rows],"page":page,"page_size":page_size,"total":int(total),"pages":max(1,(int(total)+page_size-1)//page_size)}

def get_public_result(public_id:str)->dict[str,Any]:
    with session_scope() as s: row=s.execute(text("""SELECT public_id,symbol,direction,timeframe,entry_price,exit_price,stop_loss,targets,lifecycle_outcome,result_points,result_unit,calculation_basis,opened_at,closed_at,evidence_type,verified_at,published_at,public_summary,related_signal_id FROM verified_results WHERE public_id=CAST(:id AS UUID) AND publication_status='PUBLISHED' AND verification_status='VERIFIED' AND compliance_status='PASSED' AND redaction_confirmed=TRUE AND deleted_at IS NULL"""),{"id":public_id}).mappings().first()
    if not row: raise PublicationNotFound("Public result was not found.")
    data=dict(row); data.pop("related_signal_id",None); return data
