from pathlib import Path

from services.admin_media_api import router as media_router


ROOT = Path(__file__).resolve().parents[1]


def test_phase3a_routes_and_additive_reversible_migration() -> None:
    routes = {(route.path, method) for route in media_router.routes for method in getattr(route, "methods", set())}
    required = {
        ("/admin/media", "GET"), ("/admin/media/upload", "POST"),
        ("/admin/media/{media_id}", "GET"), ("/admin/media/{media_id}", "PATCH"),
        ("/admin/media/{media_id}/{action}", "POST"), ("/admin/media/{media_id}", "DELETE"),
        ("/admin/content/{content_id}/featured-image", "POST"),
        ("/admin/content/{content_id}/featured-image", "DELETE"),
    }
    assert required.issubset(routes)
    forward = (ROOT / "migrations/016_admin_media_library.sql").read_text()
    rollback = (ROOT / "migrations/016_admin_media_library.rollback.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS public.media_assets" in forward
    assert "ADD COLUMN IF NOT EXISTS media_id" in forward
    assert "DROP COLUMN IF EXISTS media_id" in rollback
    assert "DROP COLUMN IF EXISTS image_url" not in rollback


def test_browser_code_never_references_storage_or_database_secrets() -> None:
    frontend = "\n".join(
        path.read_text()
        for folder in ("app", "components", "lib")
        for path in (ROOT / "admin-web" / folder).rglob("*.ts*")
    )
    assert "SUPABASE_SERVICE_ROLE" not in frontend
    assert "DATABASE_URL" not in frontend
    assert "base64" not in (ROOT / "services/admin_media_service.py").read_text()
