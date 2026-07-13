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
    assert not html.startswith("\n")


def test_content_card_uses_single_html_block_to_avoid_literal_markup() -> None:
    import inspect

    source = inspect.getsource(landing._render_content_card)

    assert "card_html =" in source
    assert "st.markdown(card_html, unsafe_allow_html=True)" in source
    assert 'href="{html.escape(url)}"' in source
    assert '<a class="content-card clickable-card"' in source
    assert '"""' not in source


def test_blog_detail_renders_canonical_schema_and_fallback_body() -> None:
    import inspect

    detail_source = inspect.getsource(landing._render_content_detail)
    seo_source = inspect.getsource(landing._render_content_seo_meta)

    assert "_render_content_seo_meta(item, title)" in detail_source
    assert "_fallback_article_body(title, excerpt)" in detail_source
    assert 'alt="{image_alt}"' in detail_source
    assert 'rel="canonical"' in seo_source
    assert 'property="og:image"' in seo_source
    assert 'property="og:image:alt"' in seo_source
    assert 'type="application/ld+json"' in seo_source
    assert '"@type": "Article"' in seo_source


def test_public_footer_contains_professional_legal_links() -> None:
    import inspect

    source = inspect.getsource(landing._render_site_footer)

    assert "AI Market Analytics Pro" in source
    assert "About" in source
    assert "Blog" in source
    assert "Signals" in source
    assert "Contact" in source
    assert "Privacy Policy" in source
    assert "Terms" in source
    assert "Risk Disclaimer" in source
    assert "Telegram" in source
    assert "© {current_year}" in source
    assert 'role="contentinfo"' in source
    assert "/?page=privacy-policy" in source
    assert "/?page=terms-and-conditions" in source
    assert "_safe_site_setting" not in source


def test_public_footer_stack_renders_disclaimer_then_footer() -> None:
    import inspect

    source = inspect.getsource(landing._render_public_page_footer)

    assert source.index("_render_disclaimer()") < source.index("_render_site_footer()")


def test_public_routes_call_footer_stack_after_every_early_return() -> None:
    import inspect

    source = inspect.getsource(landing.render_landing_page)

    assert source.count("_render_public_page_footer()") >= 5
    assert "_render_disclaimer()" not in source


def test_public_content_reads_are_deadline_safe() -> None:
    import inspect

    all_source = inspect.getsource(landing._all_public_content)
    type_source = inspect.getsource(landing._safe_content)

    assert "_with_deadline" in all_source
    assert "_with_deadline" in type_source
    assert "@st.cache_data" in inspect.getsource(landing._all_public_content)
    assert "timeout_seconds=2.0" in all_source
    assert "timeout_seconds=2.0" in type_source


def test_post_gallery_split_orders_by_view_count():
    items = [
        {"id": 1, "title": "Fresh", "view_count": 2, "created_at": "2026-07-11"},
        {"id": 2, "title": "Popular", "view_count": 90, "created_at": "2026-07-10"},
        {"id": 3, "title": "Needs Boost", "view_count": 0, "created_at": "2026-07-09"},
    ]

    latest, popular, low_view = landing._split_post_gallery_items(items)

    assert [item["title"] for item in latest] == [
        "Fresh",
        "Popular",
        "Needs Boost",
    ]
    assert popular[0]["title"] == "Popular"
    assert low_view[0]["title"] == "Needs Boost"


def test_related_posts_match_category_or_subcategory_and_exclude_current():
    current = {
        "id": 10,
        "category_id": 5,
        "category_slug": "xauusd",
        "subcategory": "USA Market",
    }
    candidates = [
        {"id": 10, "title": "Self", "category_id": 5},
        {"id": 11, "title": "Same Category", "category_id": 5},
        {
            "id": 12,
            "title": "Same Subcategory",
            "category_id": 7,
            "subcategory": "USA Market",
        },
        {"id": 13, "title": "Other", "category_id": 8, "subcategory": "Crypto"},
    ]

    related = landing._related_posts(current, candidates)

    assert [item["title"] for item in related] == [
        "Same Category",
        "Same Subcategory",
    ]


def test_blog_detail_by_slug_route_dispatches_to_content_detail(monkeypatch):
    calls = []

    def fake_render_content_route(slug, *, allowed_types=None):
        calls.append((slug, allowed_types))

    monkeypatch.setattr(landing, "_render_content_route", fake_render_content_route)

    handled = landing._render_path_route(
        ["blog", "xauusd-usa-market"],
        supabase=None,
        settings=object(),
        categories=[],
        on_sign_in=lambda: None,
    )

    assert handled
    assert calls == [("xauusd-usa-market", landing.BLOG_CONTENT_TYPES)]


def test_blog_alias_route_dispatches_to_same_blog_source(monkeypatch):
    calls = []

    def fake_render_content_route(slug, *, allowed_types=None):
        calls.append((slug, allowed_types))

    monkeypatch.setattr(landing, "_render_content_route", fake_render_content_route)

    handled = landing._render_path_route(
        ["blogs", "xauusd-usa-market"],
        supabase=None,
        settings=object(),
        categories=[],
        on_sign_in=lambda: None,
    )

    assert handled
    assert calls == [("xauusd-usa-market", landing.BLOG_CONTENT_TYPES)]


def test_category_page_route_dispatches_with_subcategory(monkeypatch):
    calls = []

    def fake_render_category_route(
        selected_category,
        categories,
        on_sign_in,
        *,
        subcategory_slug="",
    ):
        calls.append((selected_category, categories, subcategory_slug))

    monkeypatch.setattr(landing, "_render_category_route", fake_render_category_route)
    categories = [{"slug": "xauusd", "title": "XAUUSD"}]

    handled = landing._render_path_route(
        ["category", "xauusd", "usa-market"],
        supabase=None,
        settings=object(),
        categories=categories,
        on_sign_in=lambda: None,
    )

    assert handled
    assert calls == [("xauusd", categories, "usa-market")]


def test_subject_route_dispatches_to_mapped_category(monkeypatch):
    calls = []

    def fake_render_category_route(
        selected_category,
        categories,
        on_sign_in,
        *,
        subcategory_slug="",
    ):
        calls.append((selected_category, categories, subcategory_slug))

    monkeypatch.setattr(landing, "_render_category_route", fake_render_category_route)
    categories = [{"slug": "analysis-department", "title": "Analysis"}]

    handled = landing._render_path_route(
        ["market-analysis"],
        supabase=None,
        settings=object(),
        categories=categories,
        on_sign_in=lambda: None,
    )

    assert handled
    assert calls == [("analysis-department", categories, "")]


def test_subject_subroute_dispatches_to_category_subsection(monkeypatch):
    calls = []

    def fake_render_category_route(
        selected_category,
        categories,
        on_sign_in,
        *,
        subcategory_slug="",
    ):
        calls.append((selected_category, subcategory_slug))

    monkeypatch.setattr(landing, "_render_category_route", fake_render_category_route)

    handled = landing._render_path_route(
        ["market-analysis", "nifty"],
        supabase=None,
        settings=object(),
        categories=[],
        on_sign_in=lambda: None,
    )

    assert handled
    assert calls == [("analysis-department", "nifty")]


def test_signals_xauusd_route_dispatches_to_live_signal_index(monkeypatch):
    calls = []

    def fake_render_signals_index(supabase, settings, on_sign_in):
        calls.append((supabase, settings))

    monkeypatch.setattr(landing, "_render_signals_index", fake_render_signals_index)

    handled = landing._render_path_route(
        ["signals", "xauusd"],
        supabase="db",
        settings="settings",
        categories=[],
        on_sign_in=lambda: None,
    )

    assert handled
    assert calls == [("db", "settings")]
