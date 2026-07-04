"""Database-backed website content, subscriptions, and secure settings."""

from __future__ import annotations

from datetime import datetime, timezone
import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy import text

from core.database import session_scope


PAYMENT_NOT_STARTED = "NOT_STARTED"
PAYMENT_PENDING = "PENDING"
PAYMENT_UNDER_REVIEW = "UNDER_REVIEW"
PAYMENT_VERIFIED = "VERIFIED"
PAYMENT_REJECTED = "REJECTED"
PAYMENT_STATES = (
    PAYMENT_NOT_STARTED,
    PAYMENT_PENDING,
    PAYMENT_UNDER_REVIEW,
    PAYMENT_VERIFIED,
    PAYMENT_REJECTED,
)

CONTENT_TYPES = (
    "SPECIAL_ZONE",
    "ADVISORY",
    "ANALYSIS",
    "EDUCATION",
    "AI_BLOG",
    "ANNOUNCEMENT",
    "PROFIT_SCREENSHOT",
)


def list_categories(public_only: bool = True) -> list[dict[str, Any]]:
    """Return ordered active categories for public or admin rendering."""
    where_clause = (
        "WHERE is_active = TRUE AND is_public = TRUE"
        if public_only
        else ""
    )
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    f"""
                    SELECT id, slug, title, description, icon, display_order,
                           is_public, is_active
                    FROM public.content_categories
                    {where_clause}
                    ORDER BY display_order, title
                    """
                )
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def save_category(
    *,
    title: str,
    slug: str,
    description: str,
    icon: str,
    display_order: int,
    is_public: bool,
    is_active: bool,
    category_id: int | None = None,
) -> None:
    """Create or update one website category."""
    normalized_slug = slug.strip().lower().replace(" ", "-")
    if not title.strip() or not normalized_slug:
        raise ValueError("Category title and slug are required.")
    with session_scope() as session:
        if category_id is None:
            session.execute(
                text(
                    """
                    INSERT INTO public.content_categories (
                        title, slug, description, icon, display_order,
                        is_public, is_active
                    )
                    VALUES (
                        :title, :slug, :description, :icon, :display_order,
                        :is_public, :is_active
                    )
                    """
                ),
                {
                    "title": title.strip(),
                    "slug": normalized_slug,
                    "description": description.strip(),
                    "icon": icon.strip(),
                    "display_order": display_order,
                    "is_public": is_public,
                    "is_active": is_active,
                },
            )
        else:
            session.execute(
                text(
                    """
                    UPDATE public.content_categories
                    SET title = :title,
                        slug = :slug,
                        description = :description,
                        icon = :icon,
                        display_order = :display_order,
                        is_public = :is_public,
                        is_active = :is_active
                    WHERE id = :category_id
                    """
                ),
                {
                    "category_id": category_id,
                    "title": title.strip(),
                    "slug": normalized_slug,
                    "description": description.strip(),
                    "icon": icon.strip(),
                    "display_order": display_order,
                    "is_public": is_public,
                    "is_active": is_active,
                },
            )
    logger.info("Website category saved: slug={}", normalized_slug)


def list_content(
    *,
    content_type: str | None = None,
    public_only: bool = True,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return published public content or the complete admin content list."""
    clauses: list[str] = []
    parameters: dict[str, Any] = {"limit": limit}
    if content_type:
        clauses.append("ci.content_type = :content_type")
        parameters["content_type"] = content_type
    if public_only:
        clauses.extend(
            ("ci.is_public = TRUE", "ci.is_published = TRUE")
        )
    where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    f"""
                    SELECT ci.id, ci.category_id, ci.content_type, ci.title,
                           ci.excerpt, ci.body, ci.image_url, ci.external_url,
                           ci.is_public, ci.is_published, ci.published_at,
                           ci.created_at, cc.title AS category_title,
                           cc.slug AS category_slug
                    FROM public.content_items ci
                    LEFT JOIN public.content_categories cc
                      ON cc.id = ci.category_id
                    {where_clause}
                    ORDER BY COALESCE(ci.published_at, ci.created_at) DESC
                    LIMIT :limit
                    """
                ),
                parameters,
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def list_member_content(limit: int = 30) -> list[dict[str, Any]]:
    """Return published member content, including non-public paid items."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT ci.id, ci.content_type, ci.title, ci.excerpt,
                           ci.body, ci.image_url, ci.external_url,
                           ci.published_at, cc.title AS category_title
                    FROM public.content_items ci
                    LEFT JOIN public.content_categories cc
                      ON cc.id = ci.category_id
                    WHERE ci.is_published = TRUE
                    ORDER BY COALESCE(ci.published_at, ci.created_at) DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def save_content(
    *,
    content_type: str,
    title: str,
    excerpt: str,
    body: str,
    category_id: int | None,
    image_url: str,
    external_url: str,
    is_public: bool,
    is_published: bool,
    created_by: int,
    content_id: int | None = None,
) -> None:
    """Create or update an admin-managed content item."""
    normalized_type = content_type.strip().upper()
    if normalized_type not in CONTENT_TYPES:
        raise ValueError("Unsupported content type.")
    if not title.strip():
        raise ValueError("Content title is required.")
    published_at = datetime.now(timezone.utc) if is_published else None
    parameters = {
        "content_type": normalized_type,
        "title": title.strip(),
        "excerpt": excerpt.strip(),
        "body": body.strip(),
        "category_id": category_id,
        "image_url": image_url.strip(),
        "external_url": external_url.strip(),
        "is_public": is_public,
        "is_published": is_published,
        "published_at": published_at,
        "created_by": created_by,
    }
    with session_scope() as session:
        if content_id is None:
            session.execute(
                text(
                    """
                    INSERT INTO public.content_items (
                        content_type, title, excerpt, body, category_id,
                        image_url, external_url, is_public, is_published,
                        published_at, created_by
                    )
                    VALUES (
                        :content_type, :title, :excerpt, :body, :category_id,
                        :image_url, :external_url, :is_public, :is_published,
                        :published_at, :created_by
                    )
                    """
                ),
                parameters,
            )
        else:
            parameters["content_id"] = content_id
            session.execute(
                text(
                    """
                    UPDATE public.content_items
                    SET content_type = :content_type,
                        title = :title,
                        excerpt = :excerpt,
                        body = :body,
                        category_id = :category_id,
                        image_url = :image_url,
                        external_url = :external_url,
                        is_public = :is_public,
                        is_published = :is_published,
                        published_at = CASE
                            WHEN :is_published = TRUE
                            THEN COALESCE(published_at, :published_at)
                            ELSE NULL
                        END
                    WHERE id = :content_id
                    """
                ),
                parameters,
            )
    logger.info(
        "Website content saved: type={} title={}",
        normalized_type,
        title.strip(),
    )


def delete_content(content_id: int) -> None:
    """Delete one content record; storage cleanup remains explicit."""
    with session_scope() as session:
        session.execute(
            text("DELETE FROM public.content_items WHERE id = :content_id"),
            {"content_id": content_id},
        )
    logger.info("Website content deleted: id={}", content_id)


def get_user_payment(user_id: int) -> dict[str, Any]:
    """Return current payment state and latest subscription submission."""
    with session_scope() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT u.payment_status, s.id AS subscription_id,
                           s.plan_name, s.amount_usdt, s.network,
                           s.transaction_id, s.submitted_at, s.reviewed_at,
                           s.review_note
                    FROM public.users u
                    LEFT JOIN LATERAL (
                        SELECT *
                        FROM public.subscriptions
                        WHERE user_id = u.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) s ON TRUE
                    WHERE u.id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
            .mappings()
            .first()
        )
    if not row:
        raise ValueError("User account was not found.")
    return dict(row)


def submit_payment(
    *,
    user_id: int,
    transaction_id: str,
    amount_usdt: str,
    network: str,
) -> None:
    """Submit a transaction for manual review without granting access."""
    normalized_txid = transaction_id.strip()
    if len(normalized_txid) < 8:
        raise ValueError("Enter a valid transaction ID.")
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO public.subscriptions (
                    user_id, amount_usdt, network, transaction_id,
                    payment_status
                )
                VALUES (
                    :user_id, :amount_usdt, :network, :transaction_id,
                    'PENDING'
                )
                """
            ),
            {
                "user_id": user_id,
                "amount_usdt": amount_usdt or None,
                "network": network or None,
                "transaction_id": normalized_txid,
            },
        )
        session.execute(
            text(
                """
                UPDATE public.users
                SET payment_status = 'PENDING',
                    approval_status = 'PENDING'
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id},
        )
    logger.info("Payment submitted for review: user_id={}", user_id)


def list_payment_reviews() -> list[dict[str, Any]]:
    """Return latest payment record for every non-admin user."""
    with session_scope() as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT u.id AS user_id, u.email, u.whatsapp,
                           u.email_verified, u.payment_status,
                           s.id AS subscription_id, s.amount_usdt, s.network,
                           s.transaction_id, s.submitted_at, s.review_note
                    FROM public.users u
                    LEFT JOIN LATERAL (
                        SELECT *
                        FROM public.subscriptions
                        WHERE user_id = u.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) s ON TRUE
                    WHERE u.role = 'USER'
                    ORDER BY COALESCE(s.submitted_at, u.created_at) DESC
                    """
                )
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def review_payment(
    *,
    user_id: int,
    payment_status: str,
    reviewer_id: int,
    review_note: str,
) -> None:
    """Apply an admin payment decision and synchronize premium approval."""
    normalized_status = payment_status.strip().upper()
    if normalized_status not in PAYMENT_STATES:
        raise ValueError("Unsupported payment status.")
    approval_status = (
        "APPROVED"
        if normalized_status == PAYMENT_VERIFIED
        else "PENDING"
    )
    if normalized_status == PAYMENT_REJECTED:
        approval_status = "PENDING"
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE public.users
                SET payment_status = :payment_status,
                    approval_status = :approval_status,
                    approved_at = CASE
                        WHEN :payment_status = 'VERIFIED' THEN NOW()
                        ELSE NULL
                    END
                WHERE id = :user_id AND role = 'USER'
                """
            ),
            {
                "payment_status": normalized_status,
                "approval_status": approval_status,
                "user_id": user_id,
            },
        )
        session.execute(
            text(
                """
                UPDATE public.subscriptions
                SET payment_status = :payment_status,
                    reviewed_at = NOW(),
                    reviewed_by = :reviewer_id,
                    review_note = :review_note
                WHERE id = (
                    SELECT id FROM public.subscriptions
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC LIMIT 1
                )
                """
            ),
            {
                "payment_status": normalized_status,
                "reviewer_id": reviewer_id,
                "review_note": review_note.strip(),
                "user_id": user_id,
            },
        )
    logger.info(
        "Payment status updated: user_id={} status={}",
        user_id,
        normalized_status,
    )


def get_site_setting(setting_key: str) -> str:
    """Read a protected setting for server-side rendering."""
    with session_scope() as session:
        value = session.execute(
            text(
                """
                SELECT setting_value FROM public.site_settings
                WHERE setting_key = :setting_key
                """
            ),
            {"setting_key": setting_key},
        ).scalar_one_or_none()
    return str(value or "")


def save_site_setting(
    setting_key: str,
    setting_value: str,
    admin_user_id: int,
) -> None:
    """Upsert an admin-managed protected site setting."""
    allowed_keys = {
        "telegram_invite_url",
        "whatsapp_invite_url",
        "profit_proof_telegram_url",
    }
    if setting_key not in allowed_keys:
        raise ValueError("Unsupported site setting.")
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO public.site_settings (
                    setting_key, setting_value, updated_by
                )
                VALUES (:setting_key, :setting_value, :admin_user_id)
                ON CONFLICT (setting_key) DO UPDATE SET
                    setting_value = EXCLUDED.setting_value,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = NOW()
                """
            ),
            {
                "setting_key": setting_key,
                "setting_value": setting_value.strip(),
                "admin_user_id": admin_user_id,
            },
        )
    logger.info("Protected site setting updated: key={}", setting_key)


def upload_profit_screenshot(
    supabase: Any,
    *,
    file_name: str,
    file_bytes: bytes,
) -> str:
    """Upload a profit screenshot and return its public storage URL."""
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Only PNG, JPG, JPEG, and WEBP images are allowed.")
    content_type = mimetypes.guess_type(file_name)[0] or "image/jpeg"
    storage_path = f"{datetime.now(timezone.utc):%Y/%m}/{uuid4().hex}{suffix}"
    (
        supabase.storage.from_("profit-screenshots")
        .upload(
            storage_path,
            file_bytes,
            {"content-type": content_type, "upsert": "false"},
        )
    )
    public_url = (
        supabase.storage.from_("profit-screenshots")
        .get_public_url(storage_path)
    )
    logger.info("Profit screenshot uploaded: path={}", storage_path)
    return str(public_url)
