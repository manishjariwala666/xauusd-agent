from services.content_router import (
    BLOG_CONTENT_TYPES,
    content_url_for_item,
    path_url,
    route_source_for,
    streamlit_safe_public_url,
)


def test_route_source_supports_blog_aliases() -> None:
    source = route_source_for("blogs")

    assert source is not None
    assert source.route == "blog"
    assert source.source_kind == "content_items"
    assert source.allowed_content_types == BLOG_CONTENT_TYPES


def test_route_source_maps_subject_urls_to_category_sources() -> None:
    market = route_source_for("market-analysis")
    education = route_source_for("education")
    xauusd = route_source_for("xauusd")

    assert market is not None
    assert market.category_slug == "analysis-department"
    assert education is not None
    assert education.category_slug == "market-education"
    assert xauusd is not None
    assert xauusd.category_slug == "xauusd-signals"


def test_content_url_for_item_routes_to_correct_section() -> None:
    assert content_url_for_item({"content_type": "BLOG", "slug": "gold"}) == (
        "/blog?post=gold"
    )
    assert content_url_for_item(
        {"content_type": "ANNOUNCEMENT", "slug": "launch"}
    ) == "/announcements?announcement=launch"
    assert content_url_for_item({"content_type": "PAGE", "slug": "about"}) == (
        "/?page=about"
    )
    assert content_url_for_item({"content_type": "SIGNAL_POST", "slug": "buy"}) == (
        "/signals?signal=buy"
    )


def test_path_url_encodes_each_dynamic_segment() -> None:
    assert path_url("category", "XAUUSD Signals", "USA Market") == (
        "/category/XAUUSD%20Signals/USA%20Market"
    )


def test_streamlit_safe_url_converts_all_nested_public_routes() -> None:
    assert streamlit_safe_public_url("/signals/xauusd") == "/signals"
    assert streamlit_safe_public_url("/signals/buy-now") == (
        "/signals?signal=buy-now"
    )
    assert streamlit_safe_public_url("/announcements/launch") == (
        "/announcements?announcement=launch"
    )
    assert streamlit_safe_public_url("/page/about") == "/?page=about"
    assert streamlit_safe_public_url("/category/gold/usa-market") == (
        "/category?category=gold&subcategory=usa-market"
    )
    assert streamlit_safe_public_url("/market-analysis/nifty") == (
        "/category?category=analysis-department&subcategory=nifty"
    )
    assert streamlit_safe_public_url("/blog/seo-tools") == (
        "/category?category=ai-blog&subcategory=seo-tools"
    )
