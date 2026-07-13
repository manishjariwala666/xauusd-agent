"""Production boundaries for the lightweight Next.js public website."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "public-web"


def test_next_public_site_has_required_routes() -> None:
    required = (
        "app/page.tsx",
        "app/blog/page.tsx",
        "app/blog/[slug]/page.tsx",
        "app/signals/page.tsx",
        "app/announcements/page.tsx",
        "app/announcements/[slug]/page.tsx",
        "app/category/[slug]/page.tsx",
        "app/category/[slug]/[subcategory]/page.tsx",
        "app/page/[slug]/page.tsx",
        "app/admin/page.tsx",
        "app/api/health/route.ts",
        "app/robots.ts",
        "app/sitemap.ts",
    )
    assert all((WEB / relative).is_file() for relative in required)


def test_next_public_api_has_two_second_fallback_and_cache() -> None:
    source = (WEB / "lib/api.ts").read_text(encoding="utf-8")

    assert "setTimeout(() => controller.abort(), 2000)" in source
    assert "next: { revalidate }" in source
    assert "return fallback" in source
    assert "/public/signals?limit=12" in source


def test_next_images_are_compressed_to_modern_formats() -> None:
    config = (WEB / "next.config.ts").read_text(encoding="utf-8")
    card = (WEB / "components/content-card.tsx").read_text(encoding="utf-8")

    assert 'formats: ["image/avif", "image/webp"]' in config
    assert 'from "next/image"' in card
    assert "sizes=" in card


def test_next_public_site_keeps_admin_separate() -> None:
    admin = (WEB / "app/admin/page.tsx").read_text(encoding="utf-8")
    environment = (WEB / ".env.example").read_text(encoding="utf-8")

    assert "ADMIN_DASHBOARD_URL" in admin
    assert "https://venusrealm.net/admin?page=command-center" in environment
    assert "BACKEND_BASE_URL" in environment


def test_next_railway_preview_has_lightweight_healthcheck() -> None:
    health = (WEB / "app/api/health/route.ts").read_text(encoding="utf-8")
    railway = (WEB / "railway.toml").read_text(encoding="utf-8")

    assert 'status: "healthy"' in health
    assert "fetch(" not in health
    assert "DATABASE" not in health
    assert 'healthcheckPath = "/api/health"' in railway
    assert 'startCommand = "pnpm start -H 0.0.0.0 -p $PORT"' in railway


def test_next_preview_admin_redirect_uses_working_production_path() -> None:
    admin = (WEB / "app/admin/page.tsx").read_text(encoding="utf-8")

    assert "ADMIN_DASHBOARD_URL" in admin
    assert "https://venusrealm.net/admin?page=command-center" in admin
    assert "https://admin.venusrealm.net" not in admin


def test_next_public_tree_has_no_secret_values() -> None:
    forbidden = (
        "BEGIN PRIVATE KEY",
        "TELEGRAM_BOT_TOKEN=",
        "SUPABASE_KEY=",
        "DATABASE_URL=postgres",
        "JWT_SECRET=",
    )
    source = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in WEB.rglob("*")
        if path.is_file()
        and "node_modules" not in path.parts
        and ".next" not in path.parts
    )
    assert not any(secret in source for secret in forbidden)
