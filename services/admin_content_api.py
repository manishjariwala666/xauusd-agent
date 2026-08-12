"""Protected Phase 2A FastAPI endpoints for posts, pages, and categories."""

from __future__ import annotations

from datetime import datetime
import logging
import re
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
from services.ai_provider import AIProvider
from services.production_agents import run_blog_agent
from services.ai_content_studio_service import (
    build_repair_preview,
    extract_pdf_source,
)
from services.admin_content_service import (
    apply_admin_content_repair,
    ContentNotFoundError,
    DuplicateSlugError,
    disable_admin_category,
    get_admin_content,
    list_admin_categories,
    list_admin_content,
    duplicate_admin_content,
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


class AIBlogPlanPayload(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    target_keyword: str = Field(default="", max_length=240)
    target_audience: str = Field(default="", max_length=240)
    location: str = Field(default="", max_length=160)


class AIBlogDraftPayload(AIBlogPlanPayload):
    selected_title: str = Field(min_length=3, max_length=240)
    content_type: str = Field(
        default="complete_guide",
        pattern="^(complete_guide|news_analysis|how_to)$",
    )
    content_length: str = Field(
        default="standard",
        pattern="^(short|standard|long)$",
    )
    include_comparison_table: bool = True
    include_faq: bool = True
    include_schema: bool = True
    include_internal_links: bool = True
    include_risk_disclaimer: bool = True
    outline: list[str] = Field(default_factory=list, max_length=20)


class AIPdfDraftPayload(BaseModel):
    filename: str = Field(min_length=5, max_length=240)
    pdf_base64: str = Field(min_length=8, max_length=7_500_000)
    target_keyword: str = Field(default="", max_length=240)
    target_audience: str = Field(default="", max_length=240)
    location: str = Field(default="", max_length=160)
    content_length: str = Field(default="standard", pattern="^(short|standard|long)$")
    include_comparison_table: bool = False
    include_faq: bool = True
    include_schema: bool = True
    include_internal_links: bool = True
    include_risk_disclaimer: bool = True


class AIRepairPreviewPayload(BaseModel):
    options: list[str] = Field(min_length=1, max_length=7)


class AIRepairApplyPayload(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    slug: str = Field(min_length=1, max_length=160)
    excerpt: str = Field(default="", max_length=2_000)
    body: str = Field(default="", max_length=200_000)
    meta_title: str = Field(default="", max_length=255)
    meta_description: str = Field(default="", max_length=500)
    focus_keyword: str = Field(default="", max_length=160)
    faq: list[dict[str, str]] = Field(default_factory=list, max_length=8)
    schema_jsonld: dict[str, Any] = Field(default_factory=dict)


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
    status: str, sort: str, category_id: int | None,
) -> dict[str, Any]:
    _admin_identity(authorization, bff_secret)
    response.headers["Cache-Control"] = "private, no-store"
    return _safe_call(lambda: list_admin_content(
        kind=kind, page=page, page_size=page_size,
        search=search, status=status, sort=sort, category_id=category_id,
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
    status: str = Query("all", pattern="^(all|draft|published|scheduled|trash)$"),
    sort: str = Query("updated_desc", pattern="^(updated_desc|updated_asc|title_asc|title_desc|published_desc)$"),
    category_id: int | None = Query(None, ge=1),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return _list(kind="posts", authorization=authorization, bff_secret=x_admin_bff_key,
                 response=response, page=page, page_size=page_size, search=search,
                 status=status, sort=sort, category_id=category_id)


@router.post("/posts", status_code=201)
def posts_create(payload: ContentPayload,
                 authorization: Annotated[str | None, Header()] = None,
                 x_admin_bff_key: Annotated[str | None, Header()] = None,
                 x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _create(kind="posts", payload=payload, authorization=authorization,
                   bff_secret=x_admin_bff_key, request_id=x_request_id)


@router.post("/posts/plan-ai-draft")
def posts_plan_ai_draft(
    payload: AIBlogPlanPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _admin_identity(authorization, x_admin_bff_key)

    topic = " ".join(payload.topic.split())
    keyword = " ".join(payload.target_keyword.split()) or topic
    audience = (
        " ".join(payload.target_audience.split())
        or "readers seeking practical educational guidance"
    )
    location = " ".join(payload.location.split())

    fallback = {
        "recommended_title": f"{topic}: Complete Practical Guide",
        "title_options": [
            f"{topic}: Complete Practical Guide",
            f"{topic}: Expert Analysis, Risks and Outlook",
            f"How to Understand {topic}: Step-by-Step Guide",
            f"{topic} Explained for Beginners",
            f"{topic}: Key Facts, Comparison and FAQs",
        ],
        "focus_keyword": keyword,
        "secondary_keywords": [
            f"{keyword} guide",
            f"{keyword} analysis",
            f"{keyword} comparison",
            f"{keyword} FAQ",
        ],
        "search_intent": "Informational and educational",
        "recommended_content_type": "complete_guide",
        "recommended_length": "standard",
        "outline": [
            "Introduction and reader intent",
            f"What is {topic}?",
            f"Why does {topic} matter?",
            "Important factors and evidence",
            "Comparison table",
            "Risks and limitations",
            "Practical steps",
            "Frequently asked questions",
            "Conclusion and disclaimer",
        ],
        "draft_created": False,
    }

    try:
        generated = AIProvider().generate_json(
            system_instruction=(
                "You are the VenusRealm AI content strategist. Return one JSON "
                "object only. Create exactly five distinct natural title options "
                "and a concise article outline. Never invent keyword volume, "
                "competition scores, prices, returns or sources. Required keys: "
                "recommended_title, title_options, focus_keyword, "
                "secondary_keywords, search_intent, recommended_content_type, "
                "recommended_length, outline."
            ),
            user_instruction=(
                f"Topic: {topic}\n"
                f"Focus keyword: {keyword}\n"
                f"Audience: {audience}\n"
                f"Location: {location or 'Global'}\n"
                "Create a review-ready plan only. Do not save a post."
            ),
        )
    except Exception:
        generated = fallback

    titles = generated.get("title_options")
    if not isinstance(titles, list):
        titles = fallback["title_options"]

    clean_titles: list[str] = []
    seen_titles: set[str] = set()
    for item in [*titles, *fallback["title_options"]]:
        clean_title = " ".join(str(item).split())[:240]
        title_key = clean_title.casefold()
        if not clean_title or title_key in seen_titles:
            continue
        clean_titles.append(clean_title)
        seen_titles.add(title_key)
        if len(clean_titles) == 5:
            break

    outline = generated.get("outline")
    if not isinstance(outline, list) or len(outline) < 5:
        outline = fallback["outline"]

    valid_types = {"complete_guide", "news_analysis", "how_to"}
    recommended_type = str(
        generated.get("recommended_content_type") or "complete_guide"
    )
    if recommended_type not in valid_types:
        recommended_type = "complete_guide"
    recommended_length = str(generated.get("recommended_length") or "standard")
    if recommended_length not in {"short", "standard", "long"}:
        recommended_length = "standard"

    return {
        **fallback,
        **{
            key: value
            for key, value in generated.items()
            if value not in (None, "", [])
        },
        "title_options": clean_titles,
        "recommended_title": (
            str(generated.get("recommended_title") or clean_titles[0])[:240]
            if str(generated.get("recommended_title") or "") in clean_titles
            else clean_titles[0]
        ),
        "recommended_content_type": recommended_type,
        "recommended_length": recommended_length,
        "outline": [
            " ".join(str(item).split())
            for item in outline
            if str(item).strip()
        ],
        "draft_created": False,
    }


@router.post("/posts/generate-ai-draft", status_code=201)
def posts_generate_ai_draft(
    payload: AIBlogDraftPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _admin_identity(authorization, x_admin_bff_key)

    def generate() -> dict[str, Any]:
        result = run_blog_agent({
            **payload.model_dump(),
            "publish": False,
            "include_image": False,
            "master_ai_action": "run_blog_agent",
        })

        match = re.search(r"SEO blog #(\d+) saved as draft", result)
        if not match:
            raise RuntimeError(
                "AI Blog Agent did not return a draft identifier."
            )

        return {
            "id": int(match.group(1)),
            "status": "draft",
            "message": result,
        }

    return _safe_call(generate)


@router.post("/posts/generate-pdf-draft", status_code=201)
def posts_generate_pdf_draft(
    payload: AIPdfDraftPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _admin_identity(authorization, x_admin_bff_key)

    def generate() -> dict[str, Any]:
        source_text, page_count = extract_pdf_source(payload.pdf_base64)
        clean_name = payload.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        clean_name = " ".join(clean_name.split())[:180] or "Uploaded document"
        result = run_blog_agent({
            "topic": f"Summary and practical guide: {clean_name}",
            "selected_title": f"{clean_name}: Source-Based Summary and Guide",
            "target_keyword": payload.target_keyword or clean_name,
            "target_audience": payload.target_audience,
            "location": payload.location,
            "content_type": "complete_guide",
            "content_length": payload.content_length,
            "include_comparison_table": payload.include_comparison_table,
            "include_faq": payload.include_faq,
            "include_schema": payload.include_schema,
            "include_internal_links": payload.include_internal_links,
            "include_risk_disclaimer": payload.include_risk_disclaimer,
            "source_material": source_text,
            "publish": False,
            "include_image": False,
            "master_ai_action": "run_blog_agent",
        })
        match = re.search(r"SEO blog #(\d+) saved as draft", result)
        if not match:
            raise RuntimeError("PDF draft generator did not return a draft identifier.")
        return {
            "id": int(match.group(1)),
            "status": "draft",
            "source_pages": page_count,
            "message": "PDF source processed and one review draft created.",
        }

    return _safe_call(generate)


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


@router.post("/posts/{content_id}/repair-preview")
def posts_repair_preview(
    content_id: int,
    payload: AIRepairPreviewPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _admin_identity(authorization, x_admin_bff_key)
    return _safe_call(
        lambda: build_repair_preview(
            get_admin_content(kind="posts", content_id=content_id),
            set(payload.options),
        )
    )


@router.post("/posts/{content_id}/repair-apply")
def posts_repair_apply(
    content_id: int,
    payload: AIRepairApplyPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    identity = _admin_identity(authorization, x_admin_bff_key)
    return _safe_call(
        lambda: apply_admin_content_repair(
            content_id=content_id,
            actor_id=identity.user_id,
            request_id=_request_id(x_request_id),
            **payload.model_dump(),
        )
    )


@router.post("/posts/{content_id}/{action}")
def posts_transition(content_id: int, action: str,
                     authorization: Annotated[str | None, Header()] = None,
                     x_admin_bff_key: Annotated[str | None, Header()] = None,
                     x_request_id: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if action == "duplicate":
        identity = _admin_identity(authorization, x_admin_bff_key)
        return _safe_call(lambda: duplicate_admin_content(
            content_id=content_id, actor_id=identity.user_id,
            request_id=_request_id(x_request_id),
        ))
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
    category_id: int | None = Query(None, ge=1),
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return _list(kind="pages", authorization=authorization, bff_secret=x_admin_bff_key,
                 response=response, page=page, page_size=page_size, search=search,
                 status=status, sort=sort, category_id=category_id)


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
