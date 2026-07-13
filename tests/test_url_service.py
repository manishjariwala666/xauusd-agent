from services import url_service


def test_public_website_canonical_url_uses_root_domain(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://venusrealm.net/")

    assert url_service.public_website_base_url() == "https://venusrealm.net"
    assert url_service.canonical_url("/blog/xauusd") == (
        "https://venusrealm.net/blog/xauusd"
    )


def test_public_content_url_builds_clean_blog_detail_link(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://venusrealm.net")

    url = url_service.public_content_url(
        {"content_type": "AI_BLOG", "seo_slug": "xauusd usa market"}
    )

    assert url == "https://venusrealm.net/blog?post=xauusd+usa+market"


def test_public_content_urls_never_emit_blank_nested_streamlit_paths(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://venusrealm.net")

    assert url_service.public_content_url(
        {"content_type": "ANNOUNCEMENT", "slug": "market update"}
    ) == "https://venusrealm.net/announcements?announcement=market+update"
    assert url_service.public_content_url(
        {"content_type": "PAGE", "slug": "about us"}
    ) == "https://venusrealm.net/?page=about+us"
    assert url_service.public_content_url(
        {"content_type": "SIGNAL_POST", "slug": "gold buy"}
    ) == "https://venusrealm.net/signals?signal=gold+buy"


def test_website_url_and_api_url_stay_separate(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://venusrealm.net")
    monkeypatch.setenv("PUBLIC_API_URL", "https://api.venusrealm.net")

    assert url_service.public_website_base_url() == "https://venusrealm.net"
    assert url_service.public_api_base_url() == "https://api.venusrealm.net"
    assert "api.venusrealm.net" not in url_service.public_content_url(
        {"content_type": "BLOG", "slug": "market-outlook"}
    )


def test_public_api_base_url_keeps_railway_fallback(monkeypatch) -> None:
    for key in ("PUBLIC_API_URL", "BACKEND_BASE_URL"):
        monkeypatch.delenv(key, raising=False)

    assert url_service.public_api_base_url() == (
        "https://xauusd-agent-api-production.up.railway.app"
    )


def test_public_website_fallback_never_uses_old_streamlit_url(monkeypatch) -> None:
    for key in (
        "PUBLIC_WEBSITE_URL",
        "PUBLIC_SITE_URL",
        "STREAMLIT_PUBLIC_URL",
        "APP_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    assert url_service.public_website_base_url() == "https://venusrealm.net"


def test_url_service_has_no_secret_literals() -> None:
    source = url_service.__loader__.get_source(url_service.__name__) or ""

    forbidden = (
        "TELEGRAM_BOT_TOKEN=",
        "SUPABASE_KEY=",
        "JWT_SECRET=",
        "xauusd-buy-sell-signal" + "." + "streamlit" + ".app",
    )
    assert not any(value in source for value in forbidden)
