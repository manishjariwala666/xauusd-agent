from pages import landing


def test_local_url_builds_encoded_streamlit_query_links():
    url = landing._local_url(category="gold signals", type="AI_BLOG")

    assert url == "?category=gold+signals&type=AI_BLOG"


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
