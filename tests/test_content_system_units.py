from pathlib import Path

from services.content_service import (
    CONTENT_TYPES,
    _content_seo_select_clause,
    _json_payload,
    _normalize_content_slug,
    _normalize_content_status,
)
from services.migration_service import _AUTOMATIC_MIGRATIONS


ROOT = Path(__file__).resolve().parents[1]


def test_required_content_types_are_supported() -> None:
    assert {
        "BLOG",
        "PAGE",
        "ANNOUNCEMENT",
        "SIGNAL_POST",
        "CATEGORY",
        "SUBCATEGORY",
    } <= set(CONTENT_TYPES)


def test_content_status_normalization_preserves_legacy_publish_boolean() -> None:
    assert _normalize_content_status(None, True) == "published"
    assert _normalize_content_status(None, False) == "draft"
    assert _normalize_content_status("published", False) == "published"


def test_content_slug_and_json_helpers_are_safe() -> None:
    assert _normalize_content_slug("XAUUSD USA Market!") == "xauusd-usa-market"
    assert _json_payload('[{"q": "Risk?"}]', default=[]) == [{"q": "Risk?"}]
    assert _json_payload("", default={}) == {}


def test_content_system_migration_is_automatic_and_complete() -> None:
    assert "008_content_system_extensions.sql" in _AUTOMATIC_MIGRATIONS
    assert "010_admin_operations_extensions.sql" in _AUTOMATIC_MIGRATIONS
    sql = (ROOT / "migrations/008_content_system_extensions.sql").read_text(
        encoding="utf-8"
    )
    ops_sql = (ROOT / "migrations/010_admin_operations_extensions.sql").read_text(
        encoding="utf-8"
    )

    assert "ADD COLUMN IF NOT EXISTS slug TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS subcategory TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS status TEXT" in sql
    assert "'SIGNAL_POST'" in sql
    assert "ADD COLUMN IF NOT EXISTS target_1" in ops_sql
    assert "ADD COLUMN IF NOT EXISTS telegram_id TEXT" in ops_sql


def test_content_seo_select_clause_has_safe_fallbacks() -> None:
    fallback = _content_seo_select_clause(False)

    assert "NULL::text AS seo_slug" in fallback
    assert "'[]'::jsonb AS faq" in fallback
    assert "'{}'::jsonb AS schema_jsonld" in fallback


def test_site_setting_allowlist_contains_admin_settings() -> None:
    import inspect

    from services import content_service

    source = inspect.getsource(content_service.save_site_setting)
    for key in (
        "telegram_public_chat_id",
        "whatsapp_phone_number_id",
        "google_sheet_id",
        "feature_public_blog",
        "feature_public_signals",
        "master_ai_blog_default_status",
    ):
        assert key in source
