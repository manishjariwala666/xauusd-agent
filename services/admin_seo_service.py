"""ADMIN-only SEO persistence, validation, scoring, and issue reporting."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text

from core.database import session_scope
from services.admin_seo_validation import safe_https_url, validate_and_score


class SeoNotFoundError(ValueError):
    pass


def _approved_origins() -> set[str]:
    configured = os.getenv("SEO_APPROVED_ORIGINS", "").split(",")
    candidates = configured + [os.getenv("PUBLIC_WEBSITE_URL", ""), os.getenv("APP_BASE_URL", "")]
    origins: set[str] = set()
    for candidate in candidates:
        parsed = urlparse(candidate.strip())
        if parsed.scheme == "https" and parsed.hostname:
            origins.add(f"https://{parsed.hostname.lower()}" + (f":{parsed.port}" if parsed.port else ""))
    return origins


def _content_row(session: Any, content_id: int) -> dict[str, Any]:
    row = session.execute(text("""
        SELECT ci.id, ci.content_type, ci.title, ci.slug, ci.excerpt, ci.body,
               ci.is_published, ci.is_public, ci.image_url AS featured_image,
               ci.media_id AS featured_media_id, ci.published_at, ci.updated_at,
               ci.category_id, cc.title AS category, ci.subcategory,
               ma.alt_text AS featured_image_alt
        FROM public.content_items ci
        LEFT JOIN public.content_categories cc ON cc.id=ci.category_id
        LEFT JOIN public.media_assets ma ON ma.id=ci.media_id
        WHERE ci.id=:id AND ci.deleted_at IS NULL
    """), {"id": int(content_id)}).mappings().first()
    if not row:
        raise SeoNotFoundError("Content record was not found.")
    result = dict(row)
    result["status"] = "published" if result["is_published"] else "draft"
    return result


def _seo_row(session: Any, content_id: int) -> dict[str, Any] | None:
    row = session.execute(text("SELECT * FROM public.content_seo WHERE content_id=:id"), {"id": int(content_id)}).mappings().first()
    return dict(row) if row else None


def _defaults(content: dict[str, Any]) -> dict[str, Any]:
    return {
        "content_id": content["id"], "slug": content["slug"], "meta_title": "",
        "meta_description": "", "focus_keyword": "", "secondary_keywords": [],
        "canonical_url": "", "robots_index": True, "robots_follow": True,
        "sitemap_included": False, "open_graph": {}, "twitter_card": {},
        "faq": [], "schema_jsonld": {}, "internal_links": [], "seo_score": 0,
        "seo_validation_issues": [], "updated_at": content["updated_at"],
    }


def get_admin_seo(content_id: int, *, include_structured: bool = False) -> dict[str, Any]:
    with session_scope() as session:
        content = _content_row(session, content_id)
        seo = _defaults(content)
        seo.update(_seo_row(session, content_id) or {})
    if not include_structured:
        seo.pop("faq", None)
        seo.pop("schema_jsonld", None)
    seo["content"] = {key: content.get(key) for key in (
        "id", "content_type", "title", "slug", "excerpt", "status", "is_public",
        "featured_image", "featured_media_id", "featured_image_alt", "category",
        "subcategory", "published_at", "updated_at",
    )}
    return seo


def _resolved_social(session: Any, value: Any, label: str) -> dict[str, Any]:
    social = dict(value) if isinstance(value, dict) else {}
    media_id = social.get("media_id")
    if media_id:
        media = session.execute(text("SELECT id, public_url, alt_text FROM public.media_assets WHERE id=:id AND deleted_at IS NULL"), {"id": int(media_id)}).mappings().first()
        if not media:
            raise ValueError(f"Selected {label} media is unavailable or unauthorized.")
        social.update({"media_id": int(media["id"]), "image": media["public_url"], "image_alt": media["alt_text"]})
    elif social.get("image") and not safe_https_url(str(social["image"])):
        raise ValueError(f"{label} image must use HTTPS or a selected Media Library asset.")
    return social


def _prepare(session: Any, content: dict[str, Any], current: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = {**_defaults(content), **current}
    for key, value in payload.items():
        if value is not None:
            merged[key] = value
    merged["secondary_keywords"] = list(dict.fromkeys(str(item).strip()[:120] for item in merged.get("secondary_keywords", []) if str(item).strip()))[:20]
    merged["open_graph"] = _resolved_social(session, merged.get("open_graph"), "Open Graph")
    merged["twitter_card"] = _resolved_social(session, merged.get("twitter_card"), "X/Twitter")
    duplicate_slug = session.execute(text("SELECT 1 FROM public.content_seo WHERE slug=:slug AND content_id<>:id LIMIT 1"), {"slug": content["slug"], "id": content["id"]}).first()
    result = validate_and_score(merged, content, approved_origins=_approved_origins(), slug_unique=duplicate_slug is None)
    for column, code, label in (("meta_title", "duplicate_seo_title", "SEO title"), ("meta_description", "duplicate_meta_description", "Meta description")):
        value = str(merged.get(column) or "").strip()
        if value and session.execute(text(f"SELECT 1 FROM public.content_seo WHERE {column}=:value AND content_id<>:id LIMIT 1"), {"value": value, "id": content["id"]}).first():
            result["issues"].append({"code": code, "severity": "warning", "message": f"{label} duplicates another content record.", "points_lost": 0})
    return merged, result


def validate_admin_seo(content_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    with session_scope() as session:
        content = _content_row(session, content_id)
        current = _seo_row(session, content_id) or {}
        merged, result = _prepare(session, content, current, payload or {})
    return {**result, "content_id": int(content_id), "values": merged}


def save_admin_seo(*, content_id: int, actor_id: int, request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    with session_scope() as session:
        content = _content_row(session, content_id)
        current = _seo_row(session, content_id) or {}
        merged, result = _prepare(session, content, current, payload)
        fatal = [issue for issue in result["issues"] if issue["severity"] == "error"]
        if fatal:
            raise ValueError(fatal[0]["message"])
        params = {
            "content_id": content["id"], "slug": content["slug"], "meta_title": str(merged.get("meta_title") or "").strip()[:240],
            "meta_description": str(merged.get("meta_description") or "").strip()[:500], "focus_keyword": str(merged.get("focus_keyword") or "").strip()[:160],
            "secondary_keywords": json.dumps(merged["secondary_keywords"]), "canonical_url": str(merged.get("canonical_url") or "").strip()[:2000] or None,
            "robots_index": bool(merged.get("robots_index")), "robots_follow": bool(merged.get("robots_follow")), "sitemap_included": bool(merged.get("sitemap_included")),
            "open_graph": json.dumps(merged["open_graph"]), "twitter_card": json.dumps(merged["twitter_card"]),
            "faq": json.dumps(merged.get("faq", [])), "schema_jsonld": json.dumps(merged.get("schema_jsonld", {})),
            "seo_score": result["score"], "issues": json.dumps(result["issues"]), "actor_id": int(actor_id),
        }
        session.execute(text("""
            INSERT INTO public.content_seo (
                content_id,slug,meta_title,meta_description,focus_keyword,secondary_keywords,
                canonical_url,robots_index,robots_follow,sitemap_included,open_graph,
                twitter_card,faq,schema_jsonld,seo_score,seo_validation_issues,updated_by,updated_at
            ) VALUES (
                :content_id,:slug,:meta_title,:meta_description,:focus_keyword,CAST(:secondary_keywords AS JSONB),
                :canonical_url,:robots_index,:robots_follow,:sitemap_included,CAST(:open_graph AS JSONB),
                CAST(:twitter_card AS JSONB),CAST(:faq AS JSONB),CAST(:schema_jsonld AS JSONB),
                :seo_score,CAST(:issues AS JSONB),:actor_id,NOW()
            ) ON CONFLICT (content_id) DO UPDATE SET
                slug=EXCLUDED.slug,meta_title=EXCLUDED.meta_title,meta_description=EXCLUDED.meta_description,
                focus_keyword=EXCLUDED.focus_keyword,secondary_keywords=EXCLUDED.secondary_keywords,
                canonical_url=EXCLUDED.canonical_url,robots_index=EXCLUDED.robots_index,
                robots_follow=EXCLUDED.robots_follow,sitemap_included=EXCLUDED.sitemap_included,
                open_graph=EXCLUDED.open_graph,twitter_card=EXCLUDED.twitter_card,faq=EXCLUDED.faq,
                schema_jsonld=EXCLUDED.schema_jsonld,seo_score=EXCLUDED.seo_score,
                seo_validation_issues=EXCLUDED.seo_validation_issues,updated_by=EXCLUDED.updated_by,updated_at=NOW()
        """), params)
        _audit(session, actor_id, "CONTENT_SEO_UPDATED", request_id, {"content_id": content_id, "score": result["score"], "issue_count": len(result["issues"])})
    return get_admin_seo(content_id, include_structured=True)


def score_admin_seo(*, content_id: int, actor_id: int, request_id: str) -> dict[str, Any]:
    result = validate_admin_seo(content_id)
    with session_scope() as session:
        session.execute(text("UPDATE public.content_seo SET seo_score=:score,seo_validation_issues=CAST(:issues AS JSONB),updated_by=:actor,updated_at=NOW() WHERE content_id=:id"), {"score": result["score"], "issues": json.dumps(result["issues"]), "actor": actor_id, "id": content_id})
        _audit(session, actor_id, "CONTENT_SEO_SCORED", request_id, {"content_id": content_id, "score": result["score"]})
    return {key: result[key] for key in ("content_id", "score", "issues", "valid")}


def list_admin_seo_issues(*, page: int, page_size: int, content_type: str = "all", status: str = "all", min_score: int = 0, max_score: int = 100, issue_type: str = "all", category_id: int | None = None) -> dict[str, Any]:
    page, page_size = max(1, page), max(1, min(50, page_size))
    clauses = ["ci.deleted_at IS NULL", "COALESCE(cs.seo_score,0) BETWEEN :min_score AND :max_score"]
    params: dict[str, Any] = {"min_score": min_score, "max_score": max_score, "limit": page_size, "offset": (page - 1) * page_size}
    if content_type == "posts": clauses.append("ci.content_type IN ('BLOG','AI_BLOG')")
    elif content_type == "pages": clauses.append("ci.content_type='PAGE'")
    elif content_type != "all": raise ValueError("Unsupported content type filter.")
    if status == "published": clauses.append("ci.is_published=TRUE")
    elif status == "draft": clauses.append("ci.is_published=FALSE")
    elif status != "all": raise ValueError("Unsupported status filter.")
    if category_id is not None: clauses.append("ci.category_id=:category_id"); params["category_id"] = category_id
    if issue_type != "all":
        special = {
            "missing_seo_title": "COALESCE(cs.meta_title,'')=''",
            "missing_meta_description": "COALESCE(cs.meta_description,'')=''",
            "featured_image_missing": "COALESCE(ci.image_url,'')=''",
            "noindex_content": "cs.robots_index=FALSE",
            "indexing_sitemap_inconsistent": "cs.sitemap_included=TRUE AND (ci.is_published=FALSE OR cs.robots_index=FALSE)",
        }.get(issue_type)
        if special:
            clauses.append(special)
        else:
            clauses.append("EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(cs.seo_validation_issues,'[]'::jsonb)) issue WHERE issue->>'code'=:issue_type)")
            params["issue_type"] = issue_type
    where = " AND ".join(clauses)
    with session_scope() as session:
        total = int(session.execute(text(f"SELECT COUNT(*) FROM public.content_items ci LEFT JOIN public.content_seo cs ON cs.content_id=ci.id WHERE {where}"), params).scalar_one())
        rows = session.execute(text(f"""
            SELECT ci.id,ci.content_type,ci.title,ci.slug,ci.is_published,ci.is_public,
                   ci.image_url,ci.media_id,ci.category_id,cc.title AS category,
                   ci.updated_at,COALESCE(cs.seo_score,0) AS seo_score,
                   COALESCE(cs.seo_validation_issues,'[]'::jsonb) AS issues,
                   cs.meta_title,cs.meta_description,cs.canonical_url,cs.robots_index,cs.sitemap_included
            FROM public.content_items ci LEFT JOIN public.content_seo cs ON cs.content_id=ci.id
            LEFT JOIN public.content_categories cc ON cc.id=ci.category_id
            WHERE {where} ORDER BY COALESCE(cs.seo_score,0),ci.updated_at DESC LIMIT :limit OFFSET :offset
        """), params).mappings().all()
    items = []
    for source in rows:
        row = dict(source); issues = list(row.pop("issues") or [])
        synthetic = []
        if not row.get("meta_title"): synthetic.append(("missing_seo_title", "Missing SEO title"))
        if not row.get("meta_description"): synthetic.append(("missing_meta_description", "Missing meta description"))
        if not row.get("image_url"): synthetic.append(("missing_featured_image", "Missing featured image"))
        if row.get("robots_index") is False: synthetic.append(("noindex_content", "Content is set to noindex"))
        if row.get("sitemap_included") and (not row["is_published"] or row.get("robots_index") is False): synthetic.append(("sitemap_inconsistency", "Sitemap setting conflicts with indexing state"))
        known = {issue.get("code") for issue in issues}
        issues.extend({"code": code, "severity": "warning", "message": message, "points_lost": 0} for code, message in synthetic if code not in known)
        row["issues"] = issues; row["status"] = "published" if row.pop("is_published") else "draft"; items.append(row)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": max(1, (total + page_size - 1) // page_size)}


def get_admin_seo_summary() -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(text("""
            SELECT COUNT(ci.id) AS total,ROUND(AVG(COALESCE(cs.seo_score,0))) AS average_score,
                   COUNT(*) FILTER (WHERE COALESCE(cs.seo_score,0)<60) AS low_score,
                   COUNT(*) FILTER (WHERE COALESCE(cs.meta_title,'')='') AS missing_title,
                   COUNT(*) FILTER (WHERE COALESCE(cs.meta_description,'')='') AS missing_description,
                   COUNT(*) FILTER (WHERE cs.robots_index=FALSE) AS noindex
            FROM public.content_items ci LEFT JOIN public.content_seo cs ON cs.content_id=ci.id WHERE ci.deleted_at IS NULL
        """)).mappings().one()
    return {key: int(value or 0) for key, value in row.items()}


def _audit(session: Any, actor_id: int, event: str, request_id: str, details: dict[str, Any]) -> None:
    session.execute(text("""INSERT INTO public.admin_auth_audit_events (user_id,event_type,outcome,request_id,details)
        VALUES (:user_id,:event,'SUCCESS',:request_id,CAST(:details AS JSONB))"""), {"user_id": int(actor_id), "event": event, "request_id": str(request_id or "unknown")[:128], "details": json.dumps(details)})
