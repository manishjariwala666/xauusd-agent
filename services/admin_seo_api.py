"""Protected Phase 3B SEO management endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from services.admin_auth_api import _bearer_token, _request_id, _require_bff, _require_identity
from services.admin_auth_service import AdminIdentity
from services.admin_seo_service import (
    SeoNotFoundError, get_admin_seo, get_admin_seo_summary, list_admin_seo_issues,
    save_admin_seo, score_admin_seo, validate_admin_seo,
)


LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-seo"])


class SocialPayload(BaseModel):
    title: str = Field(default="", max_length=240)
    description: str = Field(default="", max_length=500)
    image: str = Field(default="", max_length=2_000)
    media_id: int | None = Field(default=None, ge=1)
    image_alt: str = Field(default="", max_length=500)
    card_type: Literal["summary", "summary_large_image"] | None = None


class FaqPayload(BaseModel):
    question: str = Field(max_length=300)
    answer: str = Field(max_length=4_000)


class SeoPayload(BaseModel):
    meta_title: str | None = Field(default=None, max_length=240)
    meta_description: str | None = Field(default=None, max_length=500)
    focus_keyword: str | None = Field(default=None, max_length=160)
    secondary_keywords: list[str] | None = Field(default=None, max_length=20)
    canonical_url: str | None = Field(default=None, max_length=2_000)
    robots_index: bool | None = None
    robots_follow: bool | None = None
    sitemap_included: bool | None = None
    open_graph: SocialPayload | None = None
    twitter_card: SocialPayload | None = None
    faq: list[FaqPayload] | None = Field(default=None, max_length=20)
    schema_jsonld: dict[str, Any] | list[Any] | None = None


def _identity(authorization: str | None, bff_secret: str | None) -> AdminIdentity:
    _require_bff(bff_secret)
    return _require_identity(_bearer_token(authorization))


def _safe(callback: Callable[[], Any]) -> Any:
    try:
        return callback()
    except SeoNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Admin SEO operation failed safely")
        raise HTTPException(503, "SEO service is temporarily unavailable.") from exc


@router.get("/content/{content_id}/seo")
def seo_detail(content_id: int, response: Response, include_structured: bool = Query(False),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key); response.headers["Cache-Control"] = "private, no-store"
    return _safe(lambda: get_admin_seo(content_id, include_structured=include_structured))


@router.put("/content/{content_id}/seo")
def seo_update(content_id: int, payload: SeoPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: save_admin_seo(content_id=content_id, actor_id=identity.user_id, request_id=_request_id(x_request_id), payload=payload.model_dump(exclude_none=True)))


@router.post("/content/{content_id}/seo/validate")
def seo_validate(content_id: int, payload: SeoPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key)
    return _safe(lambda: validate_admin_seo(content_id, payload.model_dump(exclude_none=True)))


@router.post("/content/{content_id}/seo/score")
def seo_score(content_id: int,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    identity = _identity(authorization, x_admin_bff_key)
    return _safe(lambda: score_admin_seo(content_id=content_id, actor_id=identity.user_id, request_id=_request_id(x_request_id)))


@router.get("/seo/issues")
def seo_issues(response: Response, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
    content_type: str = Query("all", pattern="^(all|posts|pages)$"), status: str = Query("all", pattern="^(all|draft|published)$"),
    min_score: int = Query(0, ge=0, le=100), max_score: int = Query(100, ge=0, le=100),
    issue_type: str = Query("all", max_length=80), category_id: int | None = Query(None, ge=1),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key); response.headers["Cache-Control"] = "private, no-store"
    return _safe(lambda: list_admin_seo_issues(page=page, page_size=page_size, content_type=content_type, status=status, min_score=min_score, max_score=max_score, issue_type=issue_type, category_id=category_id))


@router.get("/seo/summary")
def seo_summary(response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _identity(authorization, x_admin_bff_key); response.headers["Cache-Control"] = "private, no-store"
    return _safe(get_admin_seo_summary)
