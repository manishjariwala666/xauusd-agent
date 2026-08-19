"""Deterministic, explainable SEO validation and scoring."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse


TITLE_MIN, TITLE_MAX = 30, 60
DESCRIPTION_MIN, DESCRIPTION_MAX = 120, 160
MAX_FAQ = 20
ALLOWED_CARD_TYPES = {"summary", "summary_large_image"}
ALLOWED_SCHEMA_TYPES = {
    "Article", "BlogPosting", "NewsArticle", "WebPage", "FAQPage",
    "BreadcrumbList", "Organization", "Person", "ImageObject", "Question",
    "Answer", "ListItem",
}
UNSAFE_TEXT = re.compile(r"<\s*script|javascript\s*:|data\s*:\s*text/html|on\w+\s*=", re.I)
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def safe_https_url(value: str, approved_origins: set[str] | None = None) -> bool:
    if not value:
        return False
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    origin = f"https://{parsed.hostname.lower()}" + (f":{parsed.port}" if parsed.port else "")
    return approved_origins is None or origin in approved_origins


def validate_faq(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["FAQ must be a list of question and answer pairs."]
    if len(value) > MAX_FAQ:
        errors.append(f"FAQ is limited to {MAX_FAQ} entries.")
    for index, entry in enumerate(value[: MAX_FAQ + 1], 1):
        if not isinstance(entry, dict):
            errors.append(f"FAQ {index} must be an object.")
            continue
        question = str(entry.get("question", "")).strip()
        answer = str(entry.get("answer", "")).strip()
        if not question or not answer:
            errors.append(f"FAQ {index} requires both a question and an answer.")
        if len(question) > 300 or len(answer) > 4_000:
            errors.append(f"FAQ {index} is too long.")
        if UNSAFE_TEXT.search(question) or UNSAFE_TEXT.search(answer):
            errors.append(f"FAQ {index} contains unsafe markup.")
    return errors


def validate_schema(value: Any) -> list[str]:
    if value in ({}, [], None):
        return []
    if not isinstance(value, (dict, list)):
        return ["Schema JSON-LD must be an object or an array of objects."]
    if len(json.dumps(value, ensure_ascii=False)) > 50_000:
        return ["Schema JSON-LD exceeds the 50 KB limit."]
    errors: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                if str(key).lower() in {"__proto__", "constructor", "prototype"}:
                    errors.append("Schema contains an unsupported property.")
                if key == "@type":
                    types = item if isinstance(item, list) else [item]
                    for schema_type in types:
                        if str(schema_type) not in ALLOWED_SCHEMA_TYPES:
                            errors.append(f"Schema type '{schema_type}' is not supported.")
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str) and UNSAFE_TEXT.search(node):
            errors.append("Schema contains unsafe executable text.")

    walk(value)
    return list(dict.fromkeys(errors))


def validate_and_score(payload: dict[str, Any], content: dict[str, Any], *, approved_origins: set[str], slug_unique: bool = True) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    def check(code: str, passed: bool, points: int, message: str, severity: str = "warning") -> None:
        if not passed:
            issues.append({"code": code, "severity": severity, "message": message, "points_lost": points})

    title = str(payload.get("meta_title") or "").strip()
    description = str(payload.get("meta_description") or "").strip()
    keyword = str(payload.get("focus_keyword") or "").strip().lower()
    body_text = f"{content.get('excerpt') or ''} {content.get('body') or ''}".lower()
    slug = str(content.get("slug") or "").strip()
    canonical = str(payload.get("canonical_url") or "").strip()
    og = payload.get("open_graph") if isinstance(payload.get("open_graph"), dict) else {}
    twitter = payload.get("twitter_card") if isinstance(payload.get("twitter_card"), dict) else {}
    faq = payload.get("faq", [])
    schema = payload.get("schema_jsonld", {})
    words = re.findall(r"[\w'-]+", str(content.get("body") or ""))
    keyword_count = body_text.count(keyword) if keyword else 0
    keyword_natural = bool(keyword and keyword in body_text and keyword_count <= max(12, len(words) * .05))
    canonical_ok = bool(canonical and safe_https_url(canonical, approved_origins))
    og_image_ok = bool(og.get("media_id") or safe_https_url(str(og.get("image") or "")))
    twitter_image_ok = bool(twitter.get("media_id") or safe_https_url(str(twitter.get("image") or og.get("image") or "")))
    faq_errors, schema_errors = validate_faq(faq), validate_schema(schema)
    published = str(content.get("status") or "").lower() == "published" or bool(content.get("is_published"))
    indexable = bool(payload.get("robots_index", True))
    sitemap = bool(payload.get("sitemap_included", False))

    check("seo_title_length", bool(title) and TITLE_MIN <= len(title) <= TITLE_MAX, 12, f"SEO title should be {TITLE_MIN}–{TITLE_MAX} characters.", "error" if published and not title else "warning")
    check("meta_description_length", bool(description) and DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX, 12, f"Meta description should be {DESCRIPTION_MIN}–{DESCRIPTION_MAX} characters.")
    check("focus_keyword_title", bool(keyword and keyword in title.lower()), 8, "Focus keyword should appear in the SEO title.")
    check("focus_keyword_content", keyword_natural, 8, "Focus keyword should occur naturally in the excerpt or body.")
    check("slug_valid", bool(SLUG.fullmatch(slug)) and len(slug) <= 100 and slug_unique, 10, "Slug must be unique, lowercase, URL-safe, and at most 100 characters.", "error")
    check("canonical_valid", canonical_ok, 8, "Canonical URL must use HTTPS and an approved site origin.", "error" if canonical else "warning")
    check("featured_image_missing", bool(content.get("featured_image")), 6, "Add a featured image.")
    check("image_alt_missing", bool(str(content.get("featured_image_alt") or "").strip()), 4, "Featured image needs alt text.")
    check("open_graph_incomplete", bool(str(og.get("title") or "").strip() and str(og.get("description") or "").strip() and og_image_ok), 8, "Open Graph title, description, and safe image are required.")
    card_type = str(twitter.get("card_type") or twitter.get("card") or "summary_large_image")
    check("twitter_incomplete", bool(str(twitter.get("title") or og.get("title") or "").strip() and str(twitter.get("description") or og.get("description") or "").strip() and twitter_image_ok and card_type in ALLOWED_CARD_TYPES), 7, "X/Twitter metadata needs a valid card, title, description, and safe image.")
    check("faq_invalid", not faq_errors, 4, faq_errors[0] if faq_errors else "FAQ is valid.", "error")
    check("schema_invalid", not schema_errors, 4, schema_errors[0] if schema_errors else "Schema JSON-LD is valid.", "error")
    check("internal_links_missing", bool(payload.get("internal_links") or content.get("internal_links")), 3, "Add at least one internal link.")
    check("content_too_short", len(words) >= 300, 4, "Content should contain at least 300 words.")
    check("indexing_sitemap_inconsistent", not sitemap or (published and indexable and bool(content.get("is_public", True))), 4, "Only published, public, indexable content can be included in the sitemap.", "error")
    return {"score": max(0, 100 - sum(int(issue["points_lost"]) for issue in issues)), "issues": issues, "valid": not any(issue["severity"] == "error" for issue in issues), "faq_errors": faq_errors, "schema_errors": schema_errors}
