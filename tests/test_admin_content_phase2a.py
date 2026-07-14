from pathlib import Path

from services.admin_content_api import router as content_router


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
    assert "015_admin_content_cms.sql" not in runner


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
