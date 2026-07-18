"""Protected Phase 3A media and featured-image endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

from services.admin_auth_api import _bearer_token, _request_id, _require_bff, _require_identity
from services.admin_auth_service import AdminIdentity
from services.admin_media_service import (
    MediaConflictError, MediaNotFoundError, create_admin_media, delete_admin_media,
    get_admin_media, list_admin_media, remove_featured_image, set_featured_image,
    set_media_trash, update_admin_media,
)
from services.admin_media_storage import MAX_UPLOAD_BYTES, MediaValidationError, get_media_storage, validate_image_upload


LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-media"])


class MediaMetadataPayload(BaseModel):
    alt_text: str | None = Field(default=None, max_length=500)
    caption: str | None = Field(default=None, max_length=2_000)


class FeaturedImagePayload(BaseModel):
    media_id: int = Field(ge=1)


def _identity(authorization: str | None, bff_secret: str | None) -> AdminIdentity:
    _require_bff(bff_secret)
    return _require_identity(_bearer_token(authorization))


def _safe(callback: Callable[[], Any]) -> Any:
    try:
        return callback()
    except MediaNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except MediaConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except MediaValidationError as exc:
        status = 413 if "8 MB" in str(exc) else 400
        raise HTTPException(status, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Admin media operation failed safely")
        raise HTTPException(503, "Media service is temporarily unavailable.") from exc


@router.get("/media")
def media_list(
    response: Response, page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=50),
    search: str = Query("", max_length=120), source: str = Query("all"),
    state: str = Query("active"), date_filter: str = Query("all"),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    return _safe(lambda: list_admin_media(page=page, page_size=page_size, search=search, source=source, state=state, date_filter=date_filter))


@router.post("/media/upload", status_code=201)
async def media_upload(
    file: Annotated[UploadFile, File()], alt_text: Annotated[str, Form()] = "",
    caption: Annotated[str, Form()] = "",
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    storage = get_media_storage()
    try:
        validated = _safe(lambda: validate_image_upload(file.filename or "", file.content_type or "", data))
        stored = _safe(lambda: storage.store(validated))
        return _safe(lambda: create_admin_media(
            actor_id=identity.user_id, request_id=_request_id(x_request_id),
            original_filename=validated.original_filename, mime_type=validated.mime_type,
            size_bytes=len(validated.data), width=validated.width, height=validated.height,
            alt_text=alt_text, caption=caption, stored=stored, storage=storage,
        ))
    finally:
        await file.close()


@router.get("/media/{media_id}")
def media_detail(media_id: int, response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key); response.headers["Cache-Control"] = "private, no-store"
    return _safe(lambda: get_admin_media(media_id))


@router.patch("/media/{media_id}")
def media_update(media_id: int, payload: MediaMetadataPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: update_admin_media(media_id=media_id, actor_id=identity.user_id, request_id=_request_id(x_request_id), **payload.model_dump()))


@router.post("/media/{media_id}/{action}")
def media_transition(media_id: int, action: str,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if action not in {"trash", "restore"}: raise HTTPException(404, "Media action was not found.")
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: set_media_trash(media_id=media_id, actor_id=identity.user_id, request_id=_request_id(x_request_id), restore=action == "restore"))


@router.delete("/media/{media_id}")
def media_delete(media_id: int, confirmed: bool = Query(False),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: delete_admin_media(media_id=media_id, actor_id=identity.user_id, request_id=_request_id(x_request_id), confirmed=confirmed))


@router.post("/content/{content_id}/featured-image")
def featured_image_set(content_id: int, payload: FeaturedImagePayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: set_featured_image(content_id=content_id, media_id=payload.media_id, actor_id=identity.user_id, request_id=_request_id(x_request_id)))


@router.delete("/content/{content_id}/featured-image")
def featured_image_remove(content_id: int,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: remove_featured_image(content_id=content_id, actor_id=identity.user_id, request_id=_request_id(x_request_id)))
