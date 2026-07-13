from services.content_router import (
    BLOG_CONTENT_TYPES,
    content_url_for_item,
    path_url,
    route_source_for,
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
    ) == "/announcements/launch"
    assert content_url_for_item({"content_type": "PAGE", "slug": "about"}) == (
        "/page/about"
    )
    assert content_url_for_item({"content_type": "SIGNAL_POST", "slug": "buy"}) == (
        "/signals/buy"
    )


def test_path_url_encodes_each_dynamic_segment() -> None:
    assert path_url("category", "XAUUSD Signals", "USA Market") == (
        "/category/XAUUSD%20Signals/USA%20Market"
    )
