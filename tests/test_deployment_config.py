"""Deployment configuration invariants that must not regress."""

from pathlib import Path
import tomllib

from config import Settings
import worker


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    with (ROOT / name).open("rb") as file:
        return tomllib.load(file)


def test_railway_api_uses_injected_port_and_healthcheck() -> None:
    config = _load("railway.toml")
    deploy = config["deploy"]
    assert "$PORT" in deploy["startCommand"]
    assert deploy["healthcheckPath"] == "/health"
    assert deploy["restartPolicyType"] == "ON_FAILURE"


def test_railway_web_uses_streamlit_and_real_healthcheck() -> None:
    config = _load("railway.web.toml")
    deploy = config["deploy"]
    assert deploy["startCommand"] == (
        "streamlit run app.py --server.address 0.0.0.0 "
        "--server.port $PORT --server.headless true"
    )
    assert deploy["healthcheckPath"] == "/_stcore/health"
    assert deploy["healthcheckPath"] != "/health"
    assert deploy["restartPolicyType"] == "ON_FAILURE"


def test_streamlit_public_site_hides_auto_page_navigation() -> None:
    config = _load(".streamlit/config.toml")

    assert config["client"]["showSidebarNavigation"] is False


def test_global_theme_allows_vertical_scroll_and_custom_footer() -> None:
    source = (ROOT / "components" / "theme.py").read_text(encoding="utf-8")

    assert "overflow-y: auto !important" in source
    assert "overflow-x: hidden !important" in source
    assert "footer," not in source
    assert ".site-footer" in source
    assert "[data-testid=\"stSidebar\"]" in source
    assert "overflow-y: auto !important;" in source


def test_streamlit_admin_direct_route_exists() -> None:
    source = (ROOT / "pages" / "admin.py").read_text(encoding="utf-8")

    assert "from app import run" in source
    assert "run()" in source


def test_streamlit_public_direct_routes_exist() -> None:
    for filename in (
        "blog.py",
        "signals.py",
        "announcements.py",
        "market_analysis.py",
        "category.py",
    ):
        source = (ROOT / "pages" / filename).read_text(encoding="utf-8")

        assert "from app import run" in source
        assert "run()" in source


def test_streamlit_static_page_direct_route_renders_public_footer() -> None:
    source = (ROOT / "pages" / "page.py").read_text(encoding="utf-8")

    assert "_render_content_route" in source
    assert "_render_public_page_footer()" in source
    assert "from app import run" not in source


def test_streamlit_app_applies_safe_startup_migrations() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "from services.migration_service import apply_pending_migrations" in source
    assert "@st.cache_resource(show_spinner=False)" in source
    assert "def _apply_safe_startup_migrations" in source
    assert "_apply_safe_startup_migrations()" in source
    assert "Website startup migrations failed" in source


def test_streamlit_app_routes_admin_paths_to_login_or_admin() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "def _current_path_segments" in source
    assert 'path_segments[0] in {"admin", "login", "signup"}' in source
    assert "x-forwarded-uri" in source
    assert "referer" in source


def test_railway_worker_uses_dedicated_process() -> None:
    config = _load("railway.worker.toml")
    deploy = config["deploy"]
    assert deploy["startCommand"] == "python worker.py"
    assert "healthcheckPath" not in deploy


def test_worker_startup_helpers_are_non_fatal(monkeypatch) -> None:
    monkeypatch.setattr(
        "worker.apply_pending_migrations",
        lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")),
    )
    monkeypatch.setattr(
        "worker.get_settings",
        lambda: (_ for _ in ()).throw(RuntimeError("config unavailable")),
    )

    worker._apply_startup_migrations()

    assert worker._worker_poll_seconds() == 30


def test_environment_template_contains_all_config_keys() -> None:
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    required = {
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "JWT_SECRET",
        "APP_BASE_URL",
        "BACKEND_BASE_URL",
        "PUBLIC_WEBSITE_URL",
        "PUBLIC_API_URL",
        "BLOCK_SEARCH_INDEXING",
        "TELEGRAM_WEBHOOK_SECRET",
        "MASTER_AI_TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ADMIN_USER_ID",
        "TELEGRAM_ADMIN_USER_IDS",
        "MASTER_AI_ALLOW_NATURAL_COMMANDS",
        "WHATSAPP_ACCESS_TOKEN",
        "META_APP_SECRET",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_SHEET_ID",
        "GOOGLE_OAUTH_LOGIN_URL",
    }
    keys = {
        line.split("=", 1)[0]
        for line in template.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert required <= keys


def test_malformed_google_json_does_not_block_runtime_settings(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/xauusd",
    )
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{not-json")

    settings = Settings.load()

    assert settings.google_sheet_id == "sheet-id"
    assert settings.google_service_account_json == ""


def test_scheduled_agent_requires_runtime_validation_gate() -> None:
    workflow = (ROOT / ".github/workflows/auto_news.yml").read_text(
        encoding="utf-8"
    )

    assert "id: validate_runtime" in workflow
    assert (
        "steps.preflight.outputs.ready == 'true' && "
        "steps.validate_runtime.outputs.ready == 'true'"
    ) in workflow
    assert "JWT_SECRET must contain at least 32 characters." in workflow
    assert "TELEGRAM_BOT_TOKEN must be a BotFather token" in workflow
    assert "GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}" in workflow
    assert "check_secret GOOGLE_SHEET_ID" in workflow


def test_domain_migration_crawl_lock_is_documented() -> None:
    deployment = (ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")
    agent_source = (ROOT / "services/production_agents.py").read_text(
        encoding="utf-8"
    )

    assert "BLOCK_SEARCH_INDEXING" in deployment
    assert "https://venusrealm.net" in deployment
    assert "https://api.venusrealm.net" in deployment
    assert "xauusd-agent-web" in deployment
    assert "xauusd-agent-api" in deployment
    assert "app.venusrealm.net" not in deployment
    assert "permanent redirect to the root domain" in deployment
    assert "Do not attach `venusrealm.net` or `www.venusrealm.net` to" in deployment
    assert "noindex,nofollow,noarchive" in app_source
    assert "settings.block_search_indexing" in agent_source
    assert "Disallow: /" in agent_source


def test_sitemap_uses_public_website_url_and_blog_routes() -> None:
    source = (ROOT / "services/production_agents.py").read_text(encoding="utf-8")

    assert "public_website_base_url(settings)" in source
    assert "/blog/" in source
    assert "Sitemap: {base}/sitemap.xml" in source
    assert "?post=" not in source
