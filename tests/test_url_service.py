from services import url_service


def test_public_website_canonical_url_uses_custom_subdomain(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://app.venusrealm.net/")

    assert url_service.public_website_base_url() == "https://app.venusrealm.net"
    assert url_service.canonical_url("/blog/xauusd") == (
        "https://app.venusrealm.net/blog/xauusd"
    )


def test_public_content_url_builds_clean_blog_detail_link(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://app.venusrealm.net")

    url = url_service.public_content_url(
        {"content_type": "AI_BLOG", "seo_slug": "xauusd usa market"}
    )

    assert url == "https://app.venusrealm.net/blog/xauusd%20usa%20market"


def test_public_api_base_url_keeps_railway_fallback(monkeypatch) -> None:
    for key in ("PUBLIC_API_URL", "BACKEND_BASE_URL"):
        monkeypatch.delenv(key, raising=False)

    assert url_service.public_api_base_url() == (
        "https://xauusd-agent-api-production.up.railway.app"
    )


def test_url_service_has_no_secret_literals() -> None:
    source = url_service.__loader__.get_source(url_service.__name__) or ""

    forbidden = ("TELEGRAM_BOT_TOKEN=", "SUPABASE_KEY=", "JWT_SECRET=")
    assert not any(value in source for value in forbidden)
