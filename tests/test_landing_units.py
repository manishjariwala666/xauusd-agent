from pages import landing


def test_local_url_builds_encoded_streamlit_query_links():
    url = landing._local_url(category="gold signals", type="AI_BLOG")

    assert url == "?category=gold+signals&type=AI_BLOG"


def test_path_url_builds_clean_public_routes():
    assert landing._path_url("blog", "xauusd usa") == "/blog/xauusd%20usa"
    assert (
        landing._path_url("category", "xauusd", "usa-market")
        == "/category/xauusd/usa-market"
    )


def test_path_segments_decode_public_routes():
    assert landing._path_segments("/blog/xauusd%20usa/") == [
        "blog",
        "xauusd usa",
    ]


def test_content_url_routes_by_type():
    assert landing._content_url({"content_type": "PAGE", "slug": "about"}) == (
        "/page/about"
    )
    assert landing._content_url(
        {"content_type": "ANNOUNCEMENT", "slug": "launch"}
    ) == "/announcements/launch"
    assert landing._content_url({"content_type": "SIGNAL_POST", "slug": "buy"}) == (
        "/signals/buy"
    )
    assert landing._content_url({"content_type": "BLOG", "slug": "gold"}) == (
        "/blog/gold"
    )


def test_slug_fragment_normalizes_subcategory_routes():
    assert landing._slug_fragment("USA Market / Gold News") == (
        "usa-market-gold-news"
    )


def test_find_category_matches_slug_or_id():
    categories = [
        {"id": 10, "slug": "xauusd", "title": "XAUUSD"},
        {"id": 11, "slug": "crypto", "title": "Crypto"},
    ]

    assert landing._find_category(categories, "xauusd")["title"] == "XAUUSD"
    assert landing._find_category(categories, "11")["title"] == "Crypto"
    assert landing._find_category(categories, "missing") is None


def test_matches_content_identifier_uses_seo_slug_or_id():
    item = {"id": 42, "seo_slug": "usa-market-gold", "title": "Gold"}

    assert landing._matches_content_identifier(item, "usa-market-gold")
    assert landing._matches_content_identifier(item, "42")
    assert not landing._matches_content_identifier(item, "wrong")


def test_fallback_card_html_prevents_empty_visual_cards():
    html = landing._fallback_card_html("", "")

    assert "XAUUSD Market Research" in html
    assert "XAUUSD RESEARCH" in html
