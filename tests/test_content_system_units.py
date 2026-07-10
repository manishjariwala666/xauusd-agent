from pathlib import Path

from services.content_service import (
    CONTENT_TYPES,
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
    sql = (ROOT / "migrations/008_content_system_extensions.sql").read_text(
        encoding="utf-8"
    )

    assert "ADD COLUMN IF NOT EXISTS slug TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS subcategory TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS status TEXT" in sql
    assert "'SIGNAL_POST'" in sql
