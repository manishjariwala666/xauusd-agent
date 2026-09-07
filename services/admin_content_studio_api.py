"""Protected AI Content Studio and unsaved SEO preview endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services.admin_auth_api import _bearer_token, _require_bff, _require_identity
from services.admin_seo_validation import validate_and_score

LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/content-studio", tags=["admin-content-studio"])


class SocialDraft(BaseModel):
    title: str = Field(default="", max_length=240)
    description: str = Field(default="", max_length=500)
    image: str = Field(default="", max_length=2_000)
    media_id: int | None = Field(default=None, ge=1)
    image_alt: str = Field(default="", max_length=500)
    card_type: Literal["summary", "summary_large_image"] | None = None


class FaqDraft(BaseModel):
    question: str = Field(max_length=300)
    answer: str = Field(max_length=4_000)


class LiveSeoPayload(BaseModel):
    title: str = Field(default="", max_length=500)
    slug: str = Field(default="", max_length=500)
    excerpt: str = Field(default="", max_length=5_000)
    body: str = Field(default="", max_length=500_000)
    status: str = Field(default="draft", max_length=40)
    is_public: bool = True

    meta_title: str = Field(default="", max_length=240)
    meta_description: str = Field(default="", max_length=500)
    focus_keyword: str = Field(default="", max_length=160)
    secondary_keywords: list[str] = Field(default_factory=list, max_length=20)
    canonical_url: str = Field(default="", max_length=2_000)

    robots_index: bool = True
    robots_follow: bool = True
    sitemap_included: bool = False

    featured_image: str = Field(default="", max_length=2_000)
    featured_media_id: int | None = Field(default=None, ge=1)
    featured_image_alt: str = Field(default="", max_length=500)

    internal_links: list[str] = Field(default_factory=list, max_length=100)
    open_graph: SocialDraft = Field(default_factory=SocialDraft)
    twitter_card: SocialDraft = Field(default_factory=SocialDraft)
    faq: list[FaqDraft] = Field(default_factory=list, max_length=20)
    schema_jsonld: dict[str, Any] = Field(default_factory=dict)


def _identity(authorization: str | None, bff_secret: str | None) -> None:
    _require_bff(bff_secret)
    _require_identity(_bearer_token(authorization))


@router.post("/seo-preview")
def live_seo_preview(
    payload: LiveSeoPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Validate current unsaved editor values without storing anything."""

    _identity(authorization, x_admin_bff_key)

    draft = payload.model_dump()
    content = {
        "title": draft["title"],
        "slug": draft["slug"],
        "excerpt": draft["excerpt"],
        "body": draft["body"],
        "status": draft["status"],
        "is_public": draft["is_public"],
        "featured_image": draft["featured_image"],
        "featured_media_id": draft["featured_media_id"],
        "featured_image_alt": draft["featured_image_alt"],
        "internal_links": draft["internal_links"],
    }

    seo = {
        "meta_title": draft["meta_title"],
        "meta_description": draft["meta_description"],
        "focus_keyword": draft["focus_keyword"],
        "secondary_keywords": draft["secondary_keywords"],
        "canonical_url": draft["canonical_url"],
        "robots_index": draft["robots_index"],
        "robots_follow": draft["robots_follow"],
        "sitemap_included": draft["sitemap_included"],
        "internal_links": draft["internal_links"],
        "open_graph": draft["open_graph"],
        "twitter_card": draft["twitter_card"],
        "faq": draft["faq"],
        "schema_jsonld": draft["schema_jsonld"],
    }

    approved_origins: set[str] = set()
    canonical = draft["canonical_url"].strip()
    if canonical.startswith("https://"):
        try:
            from urllib.parse import urlparse

            parsed = urlparse(canonical)
            if parsed.scheme and parsed.netloc:
                approved_origins.add(f"{parsed.scheme}://{parsed.netloc}")
        except ValueError:
            pass

    try:
        result = validate_and_score(
            seo,
            content,
            approved_origins=approved_origins,
        )
    except Exception as exc:
        LOGGER.exception("Live SEO preview failed safely")
        raise HTTPException(503, "Live SEO preview is temporarily unavailable.") from exc

    return {
        **result,
        "saved": False,
        "word_count": len(
            str(draft["body"] or "")
            .replace("<", " ")
            .replace(">", " ")
            .split()
        ),
    }


class AiSuggestionPayload(BaseModel):
    topic: str = Field(default="", max_length=500)
    audience: str = Field(default="general", max_length=120)
    content_goal: str = Field(default="educational", max_length=120)
    language: str = Field(default="English", max_length=80)
    title: str = Field(default="", max_length=500)
    slug: str = Field(default="", max_length=500)
    excerpt: str = Field(default="", max_length=5_000)
    body: str = Field(default="", max_length=500_000)
    focus_keyword: str = Field(default="", max_length=160)
    featured_image_alt: str = Field(default="", max_length=500)
    request: Literal[
        "complete_seo",
        "titles",
        "metadata",
        "keywords",
        "excerpt",
        "faq",
        "image_alt",
        "improve_content",
    ] = "complete_seo"


def _clean_text(value: Any, maximum: int) -> str:
    return str(value or "").strip()[:maximum]


def _clean_string_list(value: Any, maximum_items: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        clean = _clean_text(item, 160)
        if clean and clean not in result:
            result.append(clean)
        if len(result) >= maximum_items:
            break
    return result


def _clean_faq(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        question = _clean_text(item.get("question"), 300)
        answer = _clean_text(item.get("answer"), 4_000)
        if question and answer:
            result.append({"question": question, "answer": answer})
        if len(result) >= 8:
            break
    return result


@router.post("/ai-suggestions")
def ai_content_suggestions(
    payload: AiSuggestionPayload,
    authorization: Annotated[str | None, Header()] = None,
    x_admin_bff_key: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Generate reviewable content and SEO suggestions without saving them."""

    _identity(authorization, x_admin_bff_key)

    from services.ai_provider import AIProvider

    system_instruction = """
You are VenusRealm AI Content Studio.

Generate professional, factual, search-friendly editorial suggestions.
Never promise rankings, profits, or trading outcomes.
Never include credentials, private information, executable scripts, or hidden HTML.
Do not publish or save anything.
Return exactly one JSON object with these keys:

title_suggestions: array of 10 unique, useful, search-friendly strings
recommended_title: the strongest title from title_suggestions
recommended_title_reason: one concise sentence explaining why it is strongest
seo_title: string between 30 and 60 characters
meta_description: string between 120 and 160 characters
focus_keyword: string
secondary_keywords: array of 4 to 8 strings
slug: lowercase hyphenated string
excerpt: concise string
image_alt: concise descriptive string
faq: array of objects with question and answer
improved_body: HTML string using p, h2, h3, ul, ol, li, strong, em, blockquote and a tags only
open_graph_title: string
open_graph_description: string
twitter_title: string
twitter_description: string
schema_jsonld: valid JSON object for Article and FAQ where appropriate

Preserve useful existing content. Suggestions require human approval.
"""

    user_instruction = f"""
Request: {payload.request}
Topic or seed keyword: {payload.topic}
Target audience: {payload.audience}
Content goal: {payload.content_goal}
Output language: {payload.language}

Create high-potential editorial titles based on:
- clear search intent
- specificity
- usefulness
- credibility
- natural click appeal
- no misleading promises or guaranteed outcomes

Current title: {payload.title}
Current slug: {payload.slug}
Current excerpt: {payload.excerpt}
Current focus keyword: {payload.focus_keyword}
Current featured-image alt: {payload.featured_image_alt}
Current article body:
{payload.body[:120_000]}
"""

    try:
        generated = AIProvider().generate_json(
            system_instruction=system_instruction,
            user_instruction=user_instruction,
        )
    except Exception as exc:
        LOGGER.exception("AI Content Studio generation failed")
        raise HTTPException(
            503,
            "AI suggestions are temporarily unavailable. Existing content was not changed.",
        ) from exc

    schema = generated.get("schema_jsonld")
    if not isinstance(schema, dict):
        schema = {}

    return {
        "saved": False,
        "request": payload.request,
        "title_suggestions": _clean_string_list(
            generated.get("title_suggestions"), 10
        ),
        "recommended_title": _clean_text(
            generated.get("recommended_title"), 240
        ),
        "recommended_title_reason": _clean_text(
            generated.get("recommended_title_reason"), 500
        ),
        "seo_title": _clean_text(generated.get("seo_title"), 60),
        "meta_description": _clean_text(
            generated.get("meta_description"), 160
        ),
        "focus_keyword": _clean_text(
            generated.get("focus_keyword"), 160
        ),
        "secondary_keywords": _clean_string_list(
            generated.get("secondary_keywords"), 8
        ),
        "slug": _clean_text(generated.get("slug"), 160),
        "excerpt": _clean_text(generated.get("excerpt"), 2_000),
        "image_alt": _clean_text(generated.get("image_alt"), 500),
        "faq": _clean_faq(generated.get("faq")),
        "improved_body": _clean_text(
            generated.get("improved_body"), 500_000
        ),
        "open_graph": {
            "title": _clean_text(
                generated.get("open_graph_title"), 240
            ),
            "description": _clean_text(
                generated.get("open_graph_description"), 500
            ),
        },
        "twitter_card": {
            "card_type": "summary_large_image",
            "title": _clean_text(
                generated.get("twitter_title"), 240
            ),
            "description": _clean_text(
                generated.get("twitter_description"), 500
            ),
        },
        "schema_jsonld": schema,
    }
