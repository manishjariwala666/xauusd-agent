"""ADMIN-only media catalog and featured-image operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from sqlalchemy import text

from core.database import session_scope
from services.admin_media_storage import MediaStorage, get_media_storage


class MediaNotFoundError(ValueError): pass
class MediaConflictError(ValueError): pass


def list_admin_media(*, page: int, page_size: int, search: str = "", source: str = "all", state: str = "active", date_filter: str = "all") -> dict[str, Any]:
    page, page_size = max(1, int(page)), max(1, min(50, int(page_size)))
    clauses, params = [], {"limit": page_size, "offset": (page - 1) * page_size}
    if state == "active": clauses.append("ma.deleted_at IS NULL")
    elif state == "trash": clauses.append("ma.deleted_at IS NOT NULL")
    elif state != "all": raise ValueError("Unsupported media state filter.")
    if source != "all":
        normalized = source.upper()
        if normalized not in {"MANUAL_UPLOAD", "LOCAL_IMPORT", "AI_GENERATED"}: raise ValueError("Unsupported media source filter.")
        clauses.append("ma.source_type = :source"); params["source"] = normalized
    term = str(search or "").strip()[:120]
    if term:
        clauses.append("(ma.original_filename ILIKE :search OR ma.alt_text ILIKE :search OR ma.caption ILIKE :search)")
        params["search"] = f"%{term}%"
    days = {"7d": 7, "30d": 30, "90d": 90}.get(date_filter)
    if date_filter != "all" and days is None: raise ValueError("Unsupported date filter.")
    if days:
        clauses.append("ma.created_at >= :cutoff"); params["cutoff"] = datetime.now(timezone.utc) - timedelta(days=days)
    where = " AND ".join(clauses) if clauses else "TRUE"
    with session_scope() as session:
        total = session.execute(text(f"SELECT COUNT(*) FROM public.media_assets ma WHERE {where}"), params).scalar_one()
        rows = session.execute(text(f"""
            SELECT ma.*, u.email AS uploaded_by_email,
                   COUNT(ci.id) AS usage_count,
                   COUNT(ci.id) FILTER (WHERE ci.is_published AND ci.deleted_at IS NULL) AS published_usage_count
            FROM public.media_assets ma
            LEFT JOIN public.users u ON u.id = ma.uploaded_by
            LEFT JOIN public.content_items ci ON ci.media_id = ma.id
            WHERE {where}
            GROUP BY ma.id, u.email
            ORDER BY ma.created_at DESC, ma.id DESC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()
    return {"items": [dict(row) for row in rows], "page": page, "page_size": page_size, "total": int(total), "pages": max(1, (int(total) + page_size - 1) // page_size)}


def get_admin_media(media_id: int) -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(text("""
            SELECT ma.*, u.email AS uploaded_by_email,
                   COUNT(ci.id) AS usage_count,
                   COUNT(ci.id) FILTER (WHERE ci.is_published AND ci.deleted_at IS NULL) AS published_usage_count
            FROM public.media_assets ma
            LEFT JOIN public.users u ON u.id = ma.uploaded_by
            LEFT JOIN public.content_items ci ON ci.media_id = ma.id
            WHERE ma.id = :id GROUP BY ma.id, u.email
        """), {"id": int(media_id)}).mappings().first()
    if not row: raise MediaNotFoundError("Media item was not found.")
    return dict(row)


def create_admin_media(*, actor_id: int, request_id: str, original_filename: str, mime_type: str, size_bytes: int, width: int, height: int, alt_text: str, caption: str, stored: Any, storage: MediaStorage | None = None) -> dict[str, Any]:
    storage = storage or get_media_storage()
    try:
        with session_scope() as session:
            media_id = session.execute(text("""
                INSERT INTO public.media_assets (
                    storage_provider, bucket, storage_path, thumbnail_path,
                    public_url, thumbnail_url, original_filename, stored_filename,
                    mime_type, size_bytes, width, height, alt_text, caption,
                    source_type, uploaded_by
                ) VALUES (
                    :provider, :bucket, :storage_path, :thumbnail_path,
                    :public_url, :thumbnail_url, :original_filename, :stored_filename,
                    :mime_type, :size_bytes, :width, :height, :alt_text, :caption,
                    'MANUAL_UPLOAD', :actor_id
                ) RETURNING id
            """), {
                **stored.__dict__, "original_filename": original_filename,
                "mime_type": mime_type, "size_bytes": int(size_bytes),
                "width": int(width), "height": int(height),
                "alt_text": str(alt_text or "").strip()[:500],
                "caption": str(caption or "").strip()[:2000], "actor_id": int(actor_id),
            }).scalar_one()
            _audit(session, actor_id, "MEDIA_UPLOADED", request_id, {"media_id": int(media_id), "mime_type": mime_type, "size_bytes": int(size_bytes)})
    except Exception:
        storage.delete(stored.storage_path, stored.thumbnail_path)
        raise
    return get_admin_media(int(media_id))


def update_admin_media(*, media_id: int, actor_id: int, request_id: str, alt_text: str | None, caption: str | None) -> dict[str, Any]:
    with session_scope() as session:
        saved = session.execute(text("""UPDATE public.media_assets SET
            alt_text=COALESCE(:alt, alt_text), caption=COALESCE(:caption, caption), updated_at=NOW()
            WHERE id=:id RETURNING id"""), {"id": int(media_id), "alt": None if alt_text is None else str(alt_text).strip()[:500], "caption": None if caption is None else str(caption).strip()[:2000]}).scalar_one_or_none()
        if saved is None: raise MediaNotFoundError("Media item was not found.")
        _audit(session, actor_id, "MEDIA_METADATA_UPDATED", request_id, {"media_id": int(media_id)})
    return get_admin_media(media_id)


def set_media_trash(*, media_id: int, actor_id: int, request_id: str, restore: bool = False) -> dict[str, Any]:
    assignment = "deleted_at=NULL, deleted_by=NULL" if restore else "deleted_at=NOW(), deleted_by=:actor_id"
    with session_scope() as session:
        saved = session.execute(text(f"UPDATE public.media_assets SET {assignment}, updated_at=NOW() WHERE id=:id RETURNING id"), {"id": int(media_id), "actor_id": int(actor_id)}).scalar_one_or_none()
        if saved is None: raise MediaNotFoundError("Media item was not found.")
        _audit(session, actor_id, "MEDIA_RESTORED" if restore else "MEDIA_TRASHED", request_id, {"media_id": int(media_id)})
    return get_admin_media(media_id)


def delete_admin_media(*, media_id: int, actor_id: int, request_id: str, confirmed: bool, storage: MediaStorage | None = None) -> dict[str, Any]:
    if not confirmed: raise ValueError("Permanent deletion requires confirmation.")
    storage = storage or get_media_storage()
    with session_scope() as session:
        row = session.execute(text("SELECT storage_path, thumbnail_path, deleted_at FROM public.media_assets WHERE id=:id FOR UPDATE"), {"id": int(media_id)}).mappings().first()
        if not row: raise MediaNotFoundError("Media item was not found.")
        if row["deleted_at"] is None: raise MediaConflictError("Trash the media item before permanent deletion.")
        references = session.execute(text("SELECT COUNT(*) FROM public.content_items WHERE media_id=:id"), {"id": int(media_id)}).scalar_one()
        if references: raise MediaConflictError("Media is still used by content and cannot be permanently deleted.")
        storage.delete(row["storage_path"], row["thumbnail_path"] or "")
        _audit(session, actor_id, "MEDIA_DELETED", request_id, {"media_id": int(media_id)})
        session.execute(text("DELETE FROM public.media_assets WHERE id=:id"), {"id": int(media_id)})
    return {"deleted": True, "id": int(media_id)}


def set_featured_image(*, content_id: int, media_id: int, actor_id: int, request_id: str) -> dict[str, Any]:
    with session_scope() as session:
        media = session.execute(text("SELECT id, public_url, alt_text FROM public.media_assets WHERE id=:id AND deleted_at IS NULL"), {"id": int(media_id)}).mappings().first()
        if not media: raise MediaNotFoundError("Active media item was not found.")
        saved = session.execute(text("UPDATE public.content_items SET media_id=:media_id, image_url=:url, updated_at=NOW() WHERE id=:content_id RETURNING id"), {"content_id": int(content_id), "media_id": int(media_id), "url": media["public_url"]}).scalar_one_or_none()
        if saved is None: raise MediaNotFoundError("Content record was not found.")
        _audit(session, actor_id, "CONTENT_FEATURED_IMAGE_SET", request_id, {"content_id": int(content_id), "media_id": int(media_id)})
    return {"content_id": int(content_id), "media_id": int(media_id), "public_url": media["public_url"], "alt_text": media["alt_text"]}


def remove_featured_image(*, content_id: int, actor_id: int, request_id: str) -> dict[str, Any]:
    with session_scope() as session:
        saved = session.execute(text("UPDATE public.content_items SET media_id=NULL, image_url=NULL, updated_at=NOW() WHERE id=:id RETURNING id"), {"id": int(content_id)}).scalar_one_or_none()
        if saved is None: raise MediaNotFoundError("Content record was not found.")
        _audit(session, actor_id, "CONTENT_FEATURED_IMAGE_REMOVED", request_id, {"content_id": int(content_id)})
    return {"content_id": int(content_id), "media_id": None, "public_url": None}


def _audit(session: Any, actor_id: int, event: str, request_id: str, details: dict[str, Any]) -> None:
    session.execute(text("""INSERT INTO public.admin_auth_audit_events
        (user_id,event_type,outcome,request_id,details)
        VALUES (:user_id,:event,'SUCCESS',:request_id,CAST(:details AS JSONB))"""), {
        "user_id": int(actor_id), "event": event, "request_id": str(request_id or "unknown")[:128], "details": json.dumps(details),
    })
