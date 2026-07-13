"""Protected Phase 2A FastAPI endpoints for posts, pages, and categories."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Annotated, Any, Callable

from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from services.admin_auth_api import (
    _bearer_token,
    _request_id,
    _require_bff,
    _require_identity,
)
from services.admin_auth_service import AdminIdentity
from services.admin_content_service import (
    ContentNotFoundError,
    DuplicateSlugError,
    disable_admin_category,
    get_admin_content,
    list_admin_categories,
    list_admin_content,
    save_admin_category,
    save_admin_content,
    transition_content,
)


LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/content", tags=["admin-content"])


class ContentPayload(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    slug: str = Field(default="", max_length=160)
    excerpt: str = Field(default="", max_length=2_000)
    body: str = Field(default="", max_length=200_000)
    category_id: int | None = Field(default=None, ge=1)
    subcategory: str = Field(default="", max_length=120)
    status: str = Field(default="draft", pattern="^(draft|published)$")
    scheduled_at: datetime | None = None
    published_at: datetime | None = None


class CategoryPayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    slug: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=2_000)
    display_order: int = Field(default=0, ge=0, le=100_000)
    is_public: bool = True
    is_active: bool = True


def _admin_identity(
    authorization: str | None,
    bff_secret: str | None,
) -> AdminIdentity:
    _require_bff(bff_secret)
    return _require_identity(_bearer_token(authorization))


def _safe_call(callback: Callable[[], Any]) -> Any:
    try:
        return callback()
    except ContentNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except DuplicateSlugError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Admin content operation failed safely")
        raise HTTPException(503, "Content service is temporarily unavailable.") from exc


def _list(
    *, kind: str, authorization: str | None, bff_secret: str | None,
    response: Response, page: int, page_size: int, search: str,
    status: str, sort: str,
) -> dict[str, Any]:
    _admin_identity(authorization, bff_secret)
    response.headers["Cache-Control"] = "private, no-store"
    return _safe_call(lambda: list_admin_content(
        kind=kind, page=page, page_size=page_size,
        search=search, status=status, sort=sort,
    ))


def _create(
    *, kind: str, payload: ContentPayload, authorization: str | None,
    bff_secret: str | None, request_id: str | None,
) -> dict[str, Any]:
    identity = _admin_identity(authorization, bff_secret)
    return _safe_call(lambda: save_admin_content(
        kind=kind, actor_id=identity.user_id, request_id=_request_id(request_id),
        **payload.model_dump(),
    ))


def _update(
    *, kind: str, content_id: int, payload: ContentPayload,
    authorization: str | None, bff_secret: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    identity = _admin_identity(authorization, bff_secret)
    return _safe_call(lambda: save_admin_content(
        kind=kind, content_id=content_id, actor_id=identity.user_id,
        request_id=_request_id(request_id), **payload.model_dump(),
    ))


def _detail(
    *, kind: str, content_id: int, authorization: str | None,
    bff_secret: str | None, response: Response,
) -> dict[str, Any]:
    _admin_identity(authorization, bff_secret)
    response.headers["Cache-Control"] = "private, no-store"
    return _safe_call(lambda: get_admin_content(kind=kind, content_id=content_id))


def _transition(
    *, kind: str, content_id: int, action: str,
    authorization: str | None, bff_secret: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    identity = _admin_identity(authorization, bff_secret)
    return _safe_call(lambda: transition_content(
        kind=kind, content_id=content_id, actor_id=identity.user_id,
        action=action, request_id=_request_id(request_id),
    ))


@router.get("/posts")
def posts_list(
    response: Response, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50), search: str = Query("", max_length=120),
    status: str = Query("all", pattern="^(all|draft|published|trash)$"),
    sort: str = Query("updated_desc", pattern="^(updated_desc|updated_asc|title_asc|title_desc|published_desc)$"),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return _list(kind="posts", authorization=authorization, bff_secret=x_admin_bff_key,
                 response=response, page=page, page_size=page_size, search=search,
                 status=status, sort=sort)


@router.post("/posts", status_code=201)
def posts_create(payload: ContentPayload,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None,
                 x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _create(kind="posts", payload=payload, authorization=authorization,
                   bff_secret=x_admin_bff_key, request_id=x_request_id)


@router.get("/posts/{content_id}")
def posts_detail(content_id: int, response: Response,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _detail(kind="posts", content_id=content_id, authorization=authorization,
                   bff_secret=x_admin_bff_key, response=response)


@router.patch("/posts/{content_id}")
def posts_update(content_id: int, payload: ContentPayload,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None,
                 x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _update(kind="posts", content_id=content_id, payload=payload,
                   authorization=authorization, bff_secret=x_admin_bff_key,
                   request_id=x_request_id)


@router.post("/posts/{content_id}/{action}")
def posts_transition(content_id: int, action: str,
                     authorization: Annotated[str | None, Header()] = None,
                     x_admin_bff_key: Annotated[str | None, Header()] = None,
                     x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if action not in {"publish", "unpublish", "trash"}:
        raise HTTPException(404, "Content action was not found.")
    return _transition(kind="posts", content_id=content_id, action=action,
                       authorization=authorization, bff_secret=x_admin_bff_key,
                       request_id=x_request_id)


@router.get("/pages")
def pages_list(
    response: Response, page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50), search: str = Query("", max_length=120),
    status: str = Query("all", pattern="^(all|draft|published)$"),
    sort: str = Query("updated_desc", pattern="^(updated_desc|updated_asc|title_asc|title_desc|published_desc)$"),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return _list(kind="pages", authorization=authorization, bff_secret=x_admin_bff_key,
                 response=response, page=page, page_size=page_size, search=search,
                 status=status, sort=sort)


@router.post("/pages", status_code=201)
def pages_create(payload: ContentPayload,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None,
                 x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _create(kind="pages", payload=payload, authorization=authorization,
                   bff_secret=x_admin_bff_key, request_id=x_request_id)


@router.get("/pages/{content_id}")
def pages_detail(content_id: int, response: Response,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _detail(kind="pages", content_id=content_id, authorization=authorization,
                   bff_secret=x_admin_bff_key, response=response)


@router.patch("/pages/{content_id}")
def pages_update(content_id: int, payload: ContentPayload,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None,
                 x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _update(kind="pages", content_id=content_id, payload=payload,
                   authorization=authorization, bff_secret=x_admin_bff_key,
                   request_id=x_request_id)


@router.post("/pages/{content_id}/{action}")
def pages_transition(content_id: int, action: str,
                     authorization: Annotated[str | None, Header()] = None,
                     x_admin_bff_key: Annotated[str | None, Header()] = None,
                     x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if action not in {"publish", "unpublish"}:
        raise HTTPException(404, "Content action was not found.")
    return _transition(kind="pages", content_id=content_id, action=action,
                       authorization=authorization, bff_secret=x_admin_bff_key,
                       request_id=x_request_id)


@router.get("/categories")
def categories_list(
    response: Response, page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50), search: str = Query("", max_length=120),
    active: str = Query("all", pattern="^(all|active|inactive)$"),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _admin_identity(authorization, x_admin_bff_key)
    response.headers["Cache-Control"] = "private, no-store"
    return _safe_call(lambda: list_admin_categories(
        page=page, page_size=page_size, search=search, active=active,
    ))


@router.post("/categories", status_code=201)
def categories_create(payload: CategoryPayload,
                      authorization: Annotated[str | None, Header()] = None,
                      x_admin_bff_key: Annotated[str | None, Header()] = None,
                      x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _admin_identity(authorization, x_admin_bff_key)
    return _safe_call(lambda: save_admin_category(
        actor_id=identity.user_id, request_id=_request_id(x_request_id),
        **payload.model_dump(),
    ))


@router.patch("/categories/{category_id}")
def categories_update(category_id: int, payload: CategoryPayload,
                      authorization: Annotated[str | None, Header()] = None,
                      x_admin_bff_key: Annotated[str | None, Header()] = None,
                      x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _admin_identity(authorization, x_admin_bff_key)
    return _safe_call(lambda: save_admin_category(
        category_id=category_id, actor_id=identity.user_id,
        request_id=_request_id(x_request_id), **payload.model_dump(),
    ))


@router.post("/categories/{category_id}/disable")
def categories_disable(category_id: int,
                       authorization: Annotated[str | None, Header()] = None,
                       x_admin_bff_key: Annotated[str | None, Header()] = None,
                       x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _admin_identity(authorization, x_admin_bff_key)
    return _safe_call(lambda: disable_admin_category(
        category_id=category_id, actor_id=identity.user_id,
        request_id=_request_id(x_request_id),
    ))
