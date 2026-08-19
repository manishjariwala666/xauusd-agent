from pathlib import Path

import pytest

from services.admin_content_api import router as content_router
from services import admin_content_service


ROOT = Path(__file__).resolve().parents[1]


def test_phase2a_admin_routes_are_registered() -> None:
    routes = {route.path for route in content_router.routes if hasattr(route, "path")}
    required = {
        "/admin/content/posts",
        "/admin/content/posts/{content_id}",
        "/admin/content/posts/{content_id}/{action}",
        "/admin/content/pages",
        "/admin/content/pages/{content_id}",
        "/admin/content/pages/{content_id}/{action}",
        "/admin/content/categories",
        "/admin/content/categories/{category_id}",
        "/admin/content/categories/{category_id}/disable",
    }
    assert required.issubset(routes)
    assert "app.include_router(admin_content_router)" in (ROOT / "backend.py").read_text()


def test_phase2a_migration_is_additive_manual_and_reversible() -> None:
    forward = (ROOT / "migrations/015_admin_content_cms.sql").read_text()
    rollback = (ROOT / "migrations/015_admin_content_cms.rollback.sql").read_text()
    runner = (ROOT / "services/migration_service.py").read_text()
    assert "ADD COLUMN IF NOT EXISTS scheduled_at" in forward
    assert "ADD COLUMN IF NOT EXISTS deleted_at" in forward
    assert "ADD COLUMN IF NOT EXISTS deleted_by" in forward
    assert "DROP TABLE" not in forward.upper()
    assert "DROP COLUMN IF EXISTS scheduled_at" in rollback
    assert '"015_admin_content_cms.sql"' in runner


def test_existing_public_content_service_and_streamlit_admin_are_preserved() -> None:
    public_service = (ROOT / "services/content_service.py").read_text()
    streamlit = (ROOT / "admin/dashboard.py").read_text()
    assert "def list_content" in public_service
    assert "def save_content" in public_service
    assert "streamlit" in streamlit.lower()


def test_phase2b_extends_existing_contract_without_new_seo_writes() -> None:
    api = (ROOT / "services/admin_content_api.py").read_text()
    service = (ROOT / "services/admin_content_service.py").read_text()
    assert 'action == "duplicate"' in api
    assert 'status: str = Query("all", pattern="^(all|draft|published|scheduled|trash)$")' in api
    assert "category_id: int | None" in api
    assert "duplicate_admin_content" in service
    assert '"stats"' in service
    assert "save_admin_content" in service
    assert '"publish": "is_public = TRUE, is_published = TRUE' in service


def test_content_publish_transition_is_locked_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CONTENT_PUBLISH_ENABLED", raising=False)

    with pytest.raises(ValueError, match="Content publishing is currently locked"):
        admin_content_service.transition_content(
            kind="posts",
            content_id=1,
            actor_id=1,
            action="publish",
            request_id="content-publish-lock-test",
        )


def test_content_save_as_published_is_locked_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CONTENT_PUBLISH_ENABLED", raising=False)

    with pytest.raises(ValueError, match="Content publishing is currently locked"):
        admin_content_service.save_admin_content(
            kind="posts",
            actor_id=1,
            title="Locked publish test",
            slug="locked-publish-test",
            excerpt="",
            body="Test body",
            category_id=None,
            subcategory="",
            status="published",
            scheduled_at=None,
            published_at=None,
            request_id="content-save-publish-lock-test",
        )


def test_content_publish_lock_can_be_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_PUBLISH_ENABLED", "true")

    class ScalarResult:
        def scalar_one_or_none(self):
            return 1

    class Session:
        def execute(self, statement, params=None):
            return ScalarResult()

    class Scope:
        def __enter__(self):
            return Session()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(admin_content_service, "session_scope", lambda: Scope())
    monkeypatch.setattr(admin_content_service, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        admin_content_service,
        "get_admin_content",
        lambda **kwargs: {"id": kwargs["content_id"], "status": "published"},
    )

    result = admin_content_service.transition_content(
        kind="posts",
        content_id=1,
        actor_id=1,
        action="publish",
        request_id="content-publish-enabled-test",
    )

    assert result["status"] == "published"
