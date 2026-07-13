"""Small, paginated ADMIN-only content operations for Phase 2A."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from core.database import session_scope


POST_TYPES = ("BLOG", "AI_BLOG")
PAGE_TYPES = ("PAGE",)
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SORTS = {
    "updated_desc": "ci.updated_at DESC, ci.id DESC",
    "updated_asc": "ci.updated_at ASC, ci.id ASC",
    "title_asc": "LOWER(ci.title) ASC, ci.id ASC",
    "title_desc": "LOWER(ci.title) DESC, ci.id DESC",
    "published_desc": "ci.published_at DESC NULLS LAST, ci.id DESC",
}


class ContentNotFoundError(ValueError):
    """Requested CMS record does not exist for the expected content type."""


class DuplicateSlugError(ValueError):
    """The normalized public slug is already assigned."""


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if not slug or len(slug) > 160 or not _SLUG_PATTERN.fullmatch(slug):
        raise ValueError("Enter a valid URL slug.")
    return slug


def list_admin_content(
    *,
    kind: str,
    page: int,
    page_size: int,
    search: str = "",
    status: str = "all",
    sort: str = "updated_desc",
) -> dict[str, Any]:
    types = _types_for_kind(kind)
    page = max(1, int(page))
    page_size = max(1, min(50, int(page_size)))
    clauses = ["ci.content_type = ANY(:types)"]
    parameters: dict[str, Any] = {
        "types": list(types),
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    normalized_search = str(search or "").strip()
    if normalized_search:
        clauses.append("(ci.title ILIKE :search OR ci.slug ILIKE :search)")
        parameters["search"] = f"%{normalized_search[:120]}%"
    normalized_status = str(status or "all").lower()
    if normalized_status == "trash":
        clauses.append("ci.deleted_at IS NOT NULL")
    else:
        clauses.append("ci.deleted_at IS NULL")
        if normalized_status == "published":
            clauses.append("ci.is_published = TRUE")
        elif normalized_status == "draft":
            clauses.append("ci.is_published = FALSE")
        elif normalized_status != "all":
            raise ValueError("Unsupported content status filter.")
    order_by = _SORTS.get(str(sort or ""), _SORTS["updated_desc"])
    where_clause = " AND ".join(clauses)
    with session_scope() as session:
        total = session.execute(
            text(f"SELECT COUNT(*) FROM public.content_items ci WHERE {where_clause}"),
            parameters,
        ).scalar_one()
        rows = session.execute(
            text(
                f"""
                SELECT ci.id, ci.title, ci.slug, ci.content_type,
                       CASE WHEN ci.deleted_at IS NOT NULL THEN 'trash'
                            WHEN ci.is_published THEN 'published'
                            ELSE 'draft' END AS status,
                       cc.title AS category,
                       u.email AS author,
                       ci.published_at, ci.scheduled_at, ci.updated_at
                FROM public.content_items ci
                LEFT JOIN public.content_categories cc ON cc.id = ci.category_id
                LEFT JOIN public.users u ON u.id = ci.created_by
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
                """
            ),
            parameters,
        ).mappings().all()
    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": int(total),
        "pages": max(1, (int(total) + page_size - 1) // page_size),
    }


def get_admin_content(*, kind: str, content_id: int) -> dict[str, Any]:
    types = _types_for_kind(kind)
    with session_scope() as session:
        row = session.execute(
            text(
                """
                SELECT ci.id, ci.content_type, ci.title, ci.slug, ci.excerpt,
                       ci.body, ci.category_id, ci.subcategory,
                       CASE WHEN ci.deleted_at IS NOT NULL THEN 'trash'
                            WHEN ci.is_published THEN 'published'
                            ELSE 'draft' END AS status,
                       ci.is_public, ci.published_at, ci.scheduled_at,
                       ci.created_at, ci.updated_at
                FROM public.content_items ci
                WHERE ci.id = :content_id AND ci.content_type = ANY(:types)
                """
            ),
            {"content_id": int(content_id), "types": list(types)},
        ).mappings().first()
    if not row:
        raise ContentNotFoundError("Content record was not found.")
    return dict(row)


def save_admin_content(
    *,
    kind: str,
    actor_id: int,
    title: str,
    slug: str,
    excerpt: str,
    body: str,
    category_id: int | None,
    subcategory: str,
    status: str,
    scheduled_at: datetime | None,
    published_at: datetime | None,
    request_id: str,
    content_id: int | None = None,
) -> dict[str, Any]:
    normalized_title = str(title or "").strip()
    if not normalized_title:
        raise ValueError("Title is required.")
    normalized_slug = normalize_slug(slug or normalized_title)
    normalized_status = str(status or "draft").lower()
    if normalized_status not in {"draft", "published"}:
        raise ValueError("Unsupported content status.")
    now = datetime.now(timezone.utc)
    if scheduled_at and scheduled_at > now:
        normalized_status = "draft"
    is_published = normalized_status == "published"
    publication_time = (published_at or now) if is_published else None
    content_type = "BLOG" if kind == "posts" else "PAGE"
    parameters = {
        "content_id": content_id,
        "content_type": content_type,
        "title": normalized_title[:240],
        "slug": normalized_slug,
        "excerpt": str(excerpt or "").strip()[:2_000],
        "body": str(body or "").strip(),
        "category_id": category_id,
        "subcategory": str(subcategory or "").strip()[:120],
        "status": normalized_status,
        "is_published": is_published,
        "published_at": publication_time,
        "scheduled_at": scheduled_at,
        "actor_id": int(actor_id),
    }
    try:
        with session_scope() as session:
            _assert_unique_slug(session, normalized_slug, content_id)
            if content_id is None:
                saved_id = session.execute(
                    text(
                        """
                        INSERT INTO public.content_items (
                            content_type, title, slug, excerpt, body,
                            category_id, subcategory, status, is_public,
                            is_published, published_at, scheduled_at, created_by
                        ) VALUES (
                            :content_type, :title, :slug, :excerpt, :body,
                            :category_id, :subcategory, :status, TRUE,
                            :is_published, :published_at, :scheduled_at, :actor_id
                        ) RETURNING id
                        """
                    ),
                    parameters,
                ).scalar_one()
                event = "CONTENT_CREATED"
            else:
                result = session.execute(
                    text(
                        """
                        UPDATE public.content_items SET
                            title = :title, slug = :slug, excerpt = :excerpt,
                            body = :body, category_id = :category_id,
                            subcategory = :subcategory, status = :status,
                            is_published = :is_published,
                            published_at = :published_at,
                            scheduled_at = :scheduled_at,
                            updated_at = NOW()
                        WHERE id = :content_id
                          AND content_type = ANY(:types)
                        RETURNING id
                        """
                    ),
                    {**parameters, "types": list(_types_for_kind(kind))},
                ).scalar_one_or_none()
                if result is None:
                    raise ContentNotFoundError("Content record was not found.")
                saved_id = int(result)
                event = "CONTENT_UPDATED"
            _audit(
                session,
                actor_id=actor_id,
                event=event,
                request_id=request_id,
                details={"content_id": int(saved_id), "kind": kind, "status": normalized_status},
            )
    except IntegrityError as exc:
        raise DuplicateSlugError("This slug is already in use.") from exc
    return get_admin_content(kind=kind, content_id=int(saved_id))


def transition_content(
    *,
    kind: str,
    content_id: int,
    actor_id: int,
    action: str,
    request_id: str,
) -> dict[str, Any]:
    if action not in {"publish", "unpublish", "trash"}:
        raise ValueError("Unsupported content action.")
    if action == "trash" and kind != "posts":
        raise ValueError("Pages cannot be trashed in Phase 2A.")
    assignments = {
        "publish": "is_published = TRUE, status = 'published', published_at = COALESCE(published_at, NOW()), scheduled_at = NULL, deleted_at = NULL, deleted_by = NULL",
        "unpublish": "is_published = FALSE, status = 'draft', published_at = NULL, scheduled_at = NULL",
        "trash": "is_published = FALSE, status = 'draft', published_at = NULL, scheduled_at = NULL, deleted_at = NOW(), deleted_by = :actor_id",
    }
    with session_scope() as session:
        saved_id = session.execute(
            text(
                f"""
                UPDATE public.content_items SET {assignments[action]}
                WHERE id = :content_id AND content_type = ANY(:types)
                RETURNING id
                """
            ),
            {
                "content_id": int(content_id),
                "types": list(_types_for_kind(kind)),
                "actor_id": int(actor_id),
            },
        ).scalar_one_or_none()
        if saved_id is None:
            raise ContentNotFoundError("Content record was not found.")
        _audit(
            session,
            actor_id=actor_id,
            event=f"CONTENT_{action.upper()}",
            request_id=request_id,
            details={"content_id": int(content_id), "kind": kind},
        )
    return get_admin_content(kind=kind, content_id=int(content_id))


def list_admin_categories(
    *, page: int, page_size: int, search: str = "", active: str = "all"
) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(1, min(50, int(page_size)))
    clauses = ["TRUE"]
    parameters: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    if str(search or "").strip():
        clauses.append("(title ILIKE :search OR slug ILIKE :search)")
        parameters["search"] = f"%{str(search).strip()[:120]}%"
    if active == "active":
        clauses.append("is_active = TRUE")
    elif active == "inactive":
        clauses.append("is_active = FALSE")
    elif active != "all":
        raise ValueError("Unsupported category filter.")
    where = " AND ".join(clauses)
    with session_scope() as session:
        total = session.execute(
            text(f"SELECT COUNT(*) FROM public.content_categories WHERE {where}"), parameters
        ).scalar_one()
        rows = session.execute(
            text(
                f"""
                SELECT id, title, slug, description, display_order,
                       is_public, is_active, updated_at
                FROM public.content_categories WHERE {where}
                ORDER BY display_order, LOWER(title)
                LIMIT :limit OFFSET :offset
                """
            ),
            parameters,
        ).mappings().all()
    return {
        "items": [dict(row) for row in rows], "page": page,
        "page_size": page_size, "total": int(total),
        "pages": max(1, (int(total) + page_size - 1) // page_size),
    }


def save_admin_category(
    *, actor_id: int, title: str, slug: str, description: str,
    display_order: int, is_public: bool, is_active: bool,
    request_id: str, category_id: int | None = None,
) -> dict[str, Any]:
    normalized_title = str(title or "").strip()
    if not normalized_title:
        raise ValueError("Category name is required.")
    normalized_slug = normalize_slug(slug or normalized_title)
    params = {
        "title": normalized_title[:160], "slug": normalized_slug,
        "description": str(description or "").strip()[:2_000],
        "display_order": max(0, min(100_000, int(display_order))),
        "is_public": bool(is_public), "is_active": bool(is_active),
        "category_id": category_id,
    }
    try:
        with session_scope() as session:
            duplicate_sql = "SELECT id FROM public.content_categories WHERE slug = :slug"
            duplicate_params: dict[str, Any] = {"slug": normalized_slug}
            if category_id is not None:
                duplicate_sql += " AND id <> :category_id"
                duplicate_params["category_id"] = category_id
            duplicate = session.execute(
                text(duplicate_sql), duplicate_params
            ).scalar_one_or_none()
            if duplicate is not None:
                raise DuplicateSlugError("This category slug is already in use.")
            if category_id is None:
                saved_id = session.execute(
                    text(
                        """
                        INSERT INTO public.content_categories (
                            title, slug, description, display_order, is_public, is_active
                        ) VALUES (
                            :title, :slug, :description, :display_order, :is_public, :is_active
                        ) RETURNING id
                        """
                    ), params,
                ).scalar_one()
                event = "CATEGORY_CREATED"
            else:
                saved_id = session.execute(
                    text(
                        """
                            UPDATE public.content_categories SET
                                title = :title, slug = :slug, description = :description,
                                display_order = :display_order, is_public = :is_public,
                                is_active = :is_active, updated_at = NOW()
                        WHERE id = :category_id RETURNING id
                        """
                    ), params,
                ).scalar_one_or_none()
                if saved_id is None:
                    raise ContentNotFoundError("Category was not found.")
                event = "CATEGORY_UPDATED"
            _audit(session, actor_id=actor_id, event=event, request_id=request_id,
                   details={"category_id": int(saved_id)})
    except IntegrityError as exc:
        raise DuplicateSlugError("This category slug is already in use.") from exc
    return get_admin_category(int(saved_id))


def disable_admin_category(*, category_id: int, actor_id: int, request_id: str) -> dict[str, Any]:
    with session_scope() as session:
        saved_id = session.execute(
            text("UPDATE public.content_categories SET is_active = FALSE, updated_at = NOW() WHERE id = :id RETURNING id"),
            {"id": int(category_id)},
        ).scalar_one_or_none()
        if saved_id is None:
            raise ContentNotFoundError("Category was not found.")
        _audit(session, actor_id=actor_id, event="CATEGORY_DISABLED", request_id=request_id,
               details={"category_id": int(category_id)})
    return get_admin_category(int(category_id))


def get_admin_category(category_id: int) -> dict[str, Any]:
    with session_scope() as session:
        row = session.execute(
            text(
                """
                SELECT id, title, slug, description, display_order,
                       is_public, is_active, updated_at
                FROM public.content_categories WHERE id = :id
                """
            ), {"id": int(category_id)},
        ).mappings().first()
    if not row:
        raise ContentNotFoundError("Category was not found.")
    return dict(row)


def _types_for_kind(kind: str) -> tuple[str, ...]:
    if kind == "posts":
        return POST_TYPES
    if kind == "pages":
        return PAGE_TYPES
    raise ValueError("Unsupported content collection.")


def _assert_unique_slug(session: Any, slug: str, content_id: int | None) -> None:
    exclusion = "" if content_id is None else "AND ci.id <> :content_id"
    params: dict[str, Any] = {"slug": slug}
    if content_id is not None:
        params["content_id"] = content_id
    duplicate = session.execute(
        text(
            f"""
            SELECT ci.id FROM public.content_items ci
            LEFT JOIN public.content_seo cs ON cs.content_id = ci.id
            WHERE (ci.slug = :slug OR cs.slug = :slug)
              {exclusion}
            LIMIT 1
            """
        ), params,
    ).scalar_one_or_none()
    if duplicate is not None:
        raise DuplicateSlugError("This slug is already in use.")


def _audit(
    session: Any, *, actor_id: int, event: str, request_id: str, details: dict[str, Any]
) -> None:
    session.execute(
        text(
            """
            INSERT INTO public.admin_auth_audit_events (
                user_id, event_type, outcome, request_id, details
            ) VALUES (:user_id, :event, 'SUCCESS', :request_id, CAST(:details AS JSONB))
            """
        ),
        {
            "user_id": int(actor_id), "event": event,
            "request_id": str(request_id or "unknown")[:128],
            "details": json.dumps(details),
        },
    )
