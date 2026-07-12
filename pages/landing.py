"""Public marketing website for AI Market Analytics Pro."""

from __future__ import annotations

import html
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote, unquote, urlencode, urlparse

from loguru import logger
import streamlit as st

from components.market_ticker import render_market_ticker
from config import get_settings
from services.content_service import (
    get_site_setting,
    list_categories,
    list_content,
    record_content_view,
)
from services.content_router import (
    BLOG_CONTENT_TYPES,
    content_slug as router_content_slug,
    content_url_for_item,
    path_url as router_path_url,
    route_source_for,
)
from services.public_market_service import (
    get_live_market_signals,
    get_top_crypto_gainers,
    get_xauusd_snapshot,
)


def render_landing_page(
    supabase: Any,
    on_sign_in: Callable[[], None],
) -> None:
    """Render the public, non-privileged marketing experience."""
    settings = get_settings()
    _render_nav(settings.brand_name, on_sign_in)

    categories = _safe_categories()
    route_segments = _current_public_path_segments()
    if _render_path_route(
        route_segments,
        supabase,
        settings,
        categories,
        on_sign_in,
    ):
        _render_public_page_footer()
        return

    selected_post = _query_param_value("post")
    selected_announcement = _query_param_value("announcement")
    selected_category = _query_param_value("category")

    if selected_post:
        _render_content_route(selected_post)
        _render_public_page_footer()
        return

    if selected_announcement:
        _render_announcement_route(selected_announcement)
        _render_public_page_footer()
        return

    if selected_category:
        _render_category_route(selected_category, categories, on_sign_in)
        _render_public_page_footer()
        return

    _render_hero(on_sign_in)

    if _site_feature_enabled("feature_public_signals", default=True):
        xauusd = get_xauusd_snapshot(supabase)
        crypto_quotes = get_top_crypto_gainers(20)
        render_market_ticker(xauusd, crypto_quotes)
        _render_xauusd_signal_section(xauusd or {}, settings, on_sign_in)

    _render_categories(categories)
    _render_announcements()
    if _site_feature_enabled("feature_public_blog", default=True):
        _render_research_content()
        _render_homepage_post_gallery()
    try:
        profit_proof_url = get_site_setting("profit_proof_telegram_url")
    except Exception:
        profit_proof_url = ""
    _render_profit_proof(
        profit_proof_url or settings.profit_proof_telegram_url
    )
    _render_subscription(settings, on_sign_in)
    _render_locked_contact(on_sign_in)
    _render_social_share(settings.public_website_url or settings.app_base_url)
    _render_public_page_footer()


def _render_nav(brand_name: str, on_sign_in: Callable[[], None]) -> None:
    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            f"""
            <div class="site-nav">
                <a class="brand" href="/" target="_self">
                    {html.escape(brand_name)}<span class="brand-dot">.</span>
                </a>
                <div class="nav-note">
                    <a href="/blog" target="_self">Blog</a>
                    <a href="/signals" target="_self">Signals</a>
                    <a href="/market-analysis" target="_self">Market Analysis</a>
                    <a href="/announcements" target="_self">Announcements</a>
                    <a href="/page/privacy-policy" target="_self">Privacy</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Sign In", type="primary", use_container_width=True):
            on_sign_in()


def _render_hero(on_sign_in: Callable[[], None]) -> None:
    hero_title = (
        _safe_site_setting("website_hero_title")
        or "Clearer signals for gold and digital assets."
    )
    hero_subtitle = (
        _safe_site_setting("website_hero_subtitle")
        or (
            "Structured XAUUSD and crypto market levels, disciplined risk "
            "context, timely announcements, and a verified-member delivery "
            "experience built for traders who value clarity."
        )
    )
    announcement = _safe_site_setting("website_announcement_text")
    st.markdown(
        f"""
        <section class="hero">
            <div class="eyebrow">MARKET INTELLIGENCE · RISK FIRST</div>
            <h1>{html.escape(hero_title)}</h1>
            <p>{html.escape(hero_subtitle)}</p>
            <div class="trust-row">
                <span class="trust-chip">Manual payment verification</span>
                <span class="trust-chip">Protected member access</span>
                <span class="trust-chip">Transparent risk warnings</span>
                <span class="trust-chip">No guaranteed-return claims</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    action_col, note_col = st.columns([1, 2])
    with action_col:
        if st.button(
            "Create Account",
            type="primary",
            use_container_width=True,
        ):
            on_sign_in()
    with note_col:
        st.caption(
            "Telegram and WhatsApp member links unlock only after payment "
            "verification."
        )
    if announcement:
        st.info(announcement)


def _safe_categories() -> list[dict[str, Any]]:
    return _with_deadline(
        lambda: list_categories(public_only=True),
        default=_fallback_categories(),
        label="Public category loading",
    )


def _safe_site_setting(key: str) -> str:
    return _with_deadline(
        lambda: get_site_setting(key),
        default="",
        label=f"Public site setting loading: key={key}",
    )


def _site_feature_enabled(key: str, *, default: bool) -> bool:
    value = _safe_site_setting(key).strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    return default


def _with_deadline(
    callback: Callable[[], Any],
    *,
    default: Any,
    label: str,
    timeout_seconds: float = 1.5,
) -> Any:
    """Run a non-critical public read without blocking the whole page."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(callback)
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        logger.warning("{} timed out; using public fallback", label)
        future.cancel()
        return default
    except Exception:
        logger.exception("{} failed; using public fallback", label)
        return default
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _fallback_categories() -> list[dict[str, Any]]:
    """Professional public fallback categories when DB is slow/unavailable."""
    return [
        {
            "slug": "xauusd-signals",
            "title": "XAUUSD Signals",
            "description": "Live gold targets, buy/sell levels, and risk context.",
            "icon": "🥇",
            "route_path": "/signals/xauusd",
            "source_type": "market_signals",
        },
        {
            "slug": "ai-blog",
            "title": "AI Blog",
            "description": "Published market research and SEO trading education.",
            "icon": "✍️",
            "route_path": "/blog",
            "source_type": "content_items",
        },
        {
            "slug": "market-analysis",
            "title": "Market Analysis",
            "description": "Index, crypto, and XAUUSD structure insights.",
            "icon": "📊",
            "route_path": "/market-analysis",
            "source_type": "content_items",
        },
        {
            "slug": "announcements",
            "title": "Announcements",
            "description": "Service, festival, and market announcements.",
            "icon": "📣",
            "route_path": "/announcements",
            "source_type": "content_items",
        },
        {
            "slug": "payment-subscription",
            "title": "Payment / Subscription",
            "description": "Secure subscription verification and access information.",
            "icon": "💳",
            "route_path": "/page/payment-subscription",
            "source_type": "content_items",
        },
        {
            "slug": "contact-support",
            "title": "Contact / Support",
            "description": "Verified-member support and assistance.",
            "icon": "💬",
            "route_path": "/page/contact-support",
            "source_type": "content_items",
        },
    ]


def _render_categories(categories: list[dict[str, Any]]) -> None:
    st.markdown('<h2 class="section-title">Explore the Platform</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-subtitle">Research, signals, education, proof, and support in one experience.</p>',
        unsafe_allow_html=True,
    )
    if not categories:
        st.info("Website categories are being prepared.")
        return

    for start in range(0, len(categories), 3):
        columns = st.columns(3)
        for column, category in zip(columns, categories[start : start + 3]):
            with column:
                slug = str(category.get("slug") or category.get("id") or "")
                route_path = str(category.get("route_path") or "").strip()
                url = route_path if route_path else _path_url("category", slug)
                st.markdown(
                    f"""
                    <a class="premium-card clickable-card" href="{html.escape(url)}" target="_self">
                        <div class="category-icon">
                            {html.escape(str(category.get('icon') or '•'))}
                        </div>
                        <h3>{html.escape(str(category.get('title') or 'Market Category'))}</h3>
                        <p>{html.escape(str(category.get('description') or 'Explore market education, signals, and updates.'))}</p>
                        <div class="card-link-text">Explore category →</div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )


def _render_announcements() -> None:
    items = _safe_content("ANNOUNCEMENT", 4)
    if not items:
        return
    st.markdown('<h2 class="section-title">Announcements</h2>', unsafe_allow_html=True)
    for start in range(0, len(items), 2):
        columns = st.columns(2)
        for column, item in zip(columns, items[start : start + 2]):
            with column:
                slug = _content_slug(item)
                url = _path_url("announcements", slug) if slug else "#"
                st.markdown(
                    f"""
                    <a class="premium-card announcement-card clickable-card"
                       href="{html.escape(url)}" target="_self">
                        <div class="eyebrow">Announcement</div>
                        <h3>{html.escape(str(item.get('title') or 'Announcement'))}</h3>
                        <p>{html.escape(str(item.get('excerpt') or item.get('body') or 'Read the latest market update.'))}</p>
                        <div class="card-link-text">Read announcement →</div>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )



def _query_param_value(name: str) -> str:
    """Return one Streamlit query param value across old/new Streamlit APIs."""
    try:
        value = st.query_params.get(name, "")
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value or "")
    except Exception:
        try:
            params = st.experimental_get_query_params()
            values = params.get(name, [])
            return str(values[0]) if values else ""
        except Exception:
            return ""


def _current_public_path_segments() -> list[str]:
    """Return clean public URL path segments from Streamlit's request context."""
    try:
        current_url = getattr(st.context, "url", "") or ""
    except Exception:
        current_url = ""
    path = urlparse(current_url).path if current_url else ""
    return _path_segments(path)


def _path_segments(path: str) -> list[str]:
    """Normalize a URL path into decoded route segments."""
    return [
        unquote(part).strip()
        for part in str(path or "").strip("/").split("/")
        if part.strip()
    ]


def _render_path_route(
    segments: list[str],
    supabase: Any,
    settings: Any,
    categories: list[dict[str, Any]],
    on_sign_in: Callable[[], None],
) -> bool:
    """Render a clean public route when the browser path requests one."""
    if not segments:
        return False

    route = segments[0].strip().lower()
    slug = segments[1].strip() if len(segments) > 1 else ""
    source = route_source_for(route)

    if not source:
        return False

    if source.route == "blog":
        if slug == "seo-tools":
            _render_category_route(
                "ai-blog",
                categories,
                on_sign_in,
                subcategory_slug=slug,
            )
        elif slug:
            _render_content_route(slug, allowed_types=source.allowed_content_types)
        else:
            _render_blog_index()
        return True

    if source.route == "category" and slug:
        subcategory_slug = segments[2].strip() if len(segments) > 2 else ""
        _render_category_route(
            slug,
            categories,
            on_sign_in,
            subcategory_slug=subcategory_slug,
        )
        return True

    if source.route == "announcements":
        if slug:
            _render_announcement_route(slug)
        else:
            _render_announcements_index()
        return True

    if source.route == "signals":
        if slug in {"xauusd", "gold", "live"}:
            _render_signals_index(supabase, settings, on_sign_in)
        elif slug:
            _render_content_route(slug, allowed_types=source.allowed_content_types)
        else:
            _render_signals_index(supabase, settings, on_sign_in)
        return True

    if source.route == "page" and slug:
        _render_content_route(slug, allowed_types=source.allowed_content_types)
        return True

    if source.is_category_backed:
        if slug:
            _render_category_route(
                source.category_slug,
                categories,
                on_sign_in,
                subcategory_slug=slug,
            )
        else:
            _render_category_route(
                source.category_slug,
                categories,
                on_sign_in,
            )
        return True

    return False


def _content_slug(item: dict[str, Any]) -> str:
    return router_content_slug(item)


def _local_url(**params: str) -> str:
    """Build an internal Streamlit query URL for clickable public cards."""
    clean_params = {
        key: value
        for key, value in params.items()
        if value is not None and str(value).strip()
    }
    if not clean_params:
        return "?"
    return "?" + urlencode(clean_params)


def _path_url(*parts: str) -> str:
    """Build an absolute public route URL from safe path segments."""
    return router_path_url(*parts)


def _content_url(item: dict[str, Any]) -> str:
    """Return the correct public route for one content item."""
    return content_url_for_item(item)


def _slug_fragment(value: str) -> str:
    """Normalize human category/subcategory text for route matching."""
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _fallback_card_html(
    title: str = "XAUUSD Market Research",
    label: str = "XAUUSD RESEARCH",
) -> str:
    """Return a professional fallback banner when a content image is absent."""
    safe_title = html.escape(title or "XAUUSD Market Research")
    safe_label = html.escape(label or "XAUUSD RESEARCH")
    return (
        '<div class="fallback-trading-card">'
        "<div>"
        f'<div class="fallback-label">{safe_label}</div>'
        f'<div class="fallback-title">{safe_title}</div>'
        "</div>"
        "</div>"
    )


def _fallback_blog_banner(title: str = "XAUUSD Market Research") -> None:
    st.markdown(_fallback_card_html(title), unsafe_allow_html=True)



def _dedupe_research_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep latest unique research/blog cards by slug or normalized title."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []

    for item in items:
        key = (
            str(item.get("seo_slug") or "").strip().lower()
            or str(item.get("title") or "").strip().lower()
        )
        if not key:
            key = str(item.get("id") or "").strip()

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


def _render_content_detail(item: dict[str, Any]) -> None:
    record_content_view(int(item.get("id") or 0))
    title = str(item.get("title") or "Research Article")
    st.markdown(
        f'<h1 class="section-title">{html.escape(title)}</h1>',
        unsafe_allow_html=True,
    )

    if item.get("image_url"):
        st.image(str(item["image_url"]), use_container_width=True)
    else:
        _fallback_blog_banner(title)

    meta_parts = [
        str(item.get("content_type") or "").replace("_", " "),
        str(item.get("category_title") or ""),
        str(item.get("published_at") or item.get("created_at") or ""),
    ]
    meta = " · ".join(part for part in meta_parts if part)
    if meta:
        st.caption(meta)

    excerpt = str(item.get("excerpt") or "").strip()
    if not excerpt:
        excerpt = "Read this public market update for practical trading context."
    if excerpt:
        st.info(excerpt)

    body = str(item.get("body") or "").strip()
    if body:
        st.markdown(body)
    else:
        st.warning("Article body is empty.")

    _render_related_posts(item)

    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("← Back to Research"):
        try:
            st.query_params.clear()
            st.rerun()
        except Exception:
            st.experimental_set_query_params()
            st.experimental_rerun()


def _render_xauusd_signal_section(
    xauusd: dict[str, Any],
    settings: Any,
    on_sign_in: Callable[[], None],
) -> None:
    """Render a public-safe signal area without exposing private AI agents."""
    price = xauusd.get("price") or xauusd.get("last") or xauusd.get("close")
    trend = str(
        xauusd.get("trend") or xauusd.get("direction") or "Live watch"
    ).title()
    try:
        configured_public_telegram = get_site_setting("profit_proof_telegram_url")
    except Exception:
        logger.exception("Public Telegram CTA setting could not be loaded")
        configured_public_telegram = ""
    public_telegram_url = (
        configured_public_telegram or settings.profit_proof_telegram_url
    )

    st.markdown(
        '<h2 class="section-title">XAUUSD Signal Desk</h2>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.3, 1])
    with left:
        price_text = (
            f"${float(price):,.2f}"
            if isinstance(price, (int, float))
            else "Live market"
        )
        st.markdown(
            f"""
            <div class="signal-desk-card">
                <div class="eyebrow">Public Market View</div>
                <h3>{html.escape(price_text)}</h3>
                <p>
                    Gold levels are monitored with a risk-first approach.
                    Premium buy/sell target delivery stays protected inside
                    verified member access.
                </p>
                <div class="trust-row">
                    <span class="trust-chip">{html.escape(trend)}</span>
                    <span class="trust-chip">XAUUSD focus</span>
                    <span class="trust-chip">Public-safe updates</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if public_telegram_url:
            st.link_button(
                "Join Telegram Updates",
                public_telegram_url,
                use_container_width=True,
            )
        if settings.support_whatsapp_url:
            st.link_button(
                "WhatsApp Support",
                settings.support_whatsapp_url,
                use_container_width=True,
            )
        if st.button("Subscribe / Login", use_container_width=True):
            on_sign_in()


def _render_content_route(
    selected_post: str,
    *,
    allowed_types: tuple[str, ...] | None = None,
) -> None:
    items = _all_public_content()
    if allowed_types:
        allowed = {content_type.upper() for content_type in allowed_types}
        items = [
            item for item in items
            if str(item.get("content_type") or "").upper() in allowed
        ]
    for item in items:
        if _matches_content_identifier(item, selected_post):
            _render_content_detail(item)
            return
    st.warning("Article not found or not published.")
    _render_back_home_button()


def _render_announcement_route(selected_announcement: str) -> None:
    items = _safe_content("ANNOUNCEMENT", 30)
    for item in items:
        if _matches_content_identifier(item, selected_announcement):
            _render_content_detail(item)
            return
    st.warning("Announcement not found or not published.")
    _render_back_home_button()


def _render_blog_index() -> None:
    st.markdown(
        '<h1 class="section-title">Market Blog & Research</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="section-subtitle">Latest XAUUSD research, education, and market commentary.</p>',
        unsafe_allow_html=True,
    )
    items = _content_items_by_type(BLOG_CONTENT_TYPES, limit=60)
    _render_view_segments(items)
    _render_content_grid(
        items[:24],
        empty_message="No public blog posts are available yet.",
    )


def _render_announcements_index() -> None:
    st.markdown(
        '<h1 class="section-title">Announcements</h1>',
        unsafe_allow_html=True,
    )
    items = _safe_content("ANNOUNCEMENT", 60)
    _render_content_grid(
        items,
        empty_message="No public announcements are available yet.",
    )


def _render_signals_index(
    supabase: Any,
    settings: Any,
    on_sign_in: Callable[[], None],
) -> None:
    st.markdown(
        '<h1 class="section-title">Public XAUUSD Signals</h1>',
        unsafe_allow_html=True,
    )
    xauusd = get_xauusd_snapshot(supabase) or {}
    _render_xauusd_signal_section(xauusd, settings, on_sign_in)
    live_signals = get_live_market_signals(limit=12)
    _render_live_signal_table(live_signals)
    items = _content_items_by_type(("SIGNAL_POST",), limit=40)
    _render_content_grid(
        items,
        empty_message=(
            "No public signal posts are available yet. "
            "Premium buy/sell targets remain inside verified member access."
        ),
    )


def _render_live_signal_table(signals: list[dict[str, Any]]) -> None:
    """Render live market_signals rows without caching the trading table."""
    st.markdown(
        '<h2 class="section-title">Live Trading Table</h2>',
        unsafe_allow_html=True,
    )
    if not signals:
        st.info("No live public signal rows are available yet.")
        return
    st.dataframe(
        [
            {
                "time": item.get("signal_time"),
                "symbol": item.get("symbol") or "XAUUSD",
                "direction": item.get("signal_type"),
                "entry": item.get("price"),
                "target_1": item.get("target_1") or item.get("target_price"),
                "target_2": item.get("target_2"),
                "target_3": item.get("target_3"),
                "stop_loss": item.get("stop_loss"),
                "risk": item.get("risk_level") or "—",
                "timeframe": item.get("timeframe") or "—",
            }
            for item in signals
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_category_route(
    selected_category: str,
    categories: list[dict[str, Any]],
    on_sign_in: Callable[[], None],
    *,
    subcategory_slug: str = "",
) -> None:
    category = _find_category(categories, selected_category)
    if not category:
        st.warning("Category not found or not active.")
        _render_back_home_button()
        return

    title = str(category.get("title") or "Category")
    st.markdown(
        f'<h1 class="section-title">{html.escape(title)}</h1>',
        unsafe_allow_html=True,
    )
    description = str(category.get("description") or "").strip()
    if description:
        st.markdown(
            f'<p class="section-subtitle">{html.escape(description)}</p>',
            unsafe_allow_html=True,
        )

    items = [
        item for item in _all_public_content()
        if str(item.get("category_slug") or "") == str(category.get("slug") or "")
        or str(item.get("category_id") or "") == str(category.get("id") or "")
    ]
    selected_subcategory = (
        subcategory_slug or _query_param_value("subcategory")
    ).strip()
    available_subcategories = sorted(
        {
            str(item.get("subcategory") or "").strip()
            for item in items
            if str(item.get("subcategory") or "").strip()
        }
    )
    if available_subcategories:
        _render_subcategory_links(
            str(category.get("slug") or ""),
            available_subcategories,
            selected_subcategory,
        )
    if selected_subcategory:
        items = [
            item for item in items
            if _slug_fragment(str(item.get("subcategory") or ""))
            == _slug_fragment(selected_subcategory)
        ]

    selected_type = _query_param_value("type").strip().upper()
    available_types = sorted(
        {
            str(item.get("content_type") or "").strip().upper()
            for item in items
            if item.get("content_type")
        }
    )
    if available_types and not available_subcategories:
        _render_content_type_links(
            str(category.get("slug") or ""),
            available_types,
            selected_type,
        )
    if selected_type:
        items = [
            item for item in items
            if str(item.get("content_type") or "").strip().upper() == selected_type
        ]

    _render_content_grid(
        items[:12],
        empty_message="No public posts are available in this category yet.",
    )
    _render_subscription(get_settings(), on_sign_in)


def _render_subcategory_links(
    category_slug: str,
    subcategories: list[str],
    selected_subcategory: str,
) -> None:
    links = [
        f'<a class="social-link" '
        f'href="{html.escape(_path_url("category", category_slug))}" '
        f'target="_self">All</a>'
    ]
    selected_slug = _slug_fragment(selected_subcategory)
    for subcategory in subcategories:
        subcategory_slug = _slug_fragment(subcategory)
        label = subcategory.replace("_", " ").title()
        css_class = (
            "social-link active-chip"
            if subcategory_slug == selected_slug
            else "social-link"
        )
        links.append(
            f'<a class="{css_class}" '
            f'href="{html.escape(_path_url("category", category_slug, subcategory_slug))}" '
            f'target="_self">{html.escape(label)}</a>'
        )
    st.markdown(
        f'<div class="social-row">{"".join(links)}</div>',
        unsafe_allow_html=True,
    )


def _render_content_type_links(
    category_slug: str,
    content_types: list[str],
    selected_type: str,
) -> None:
    links = [
        f'<a class="social-link" '
        f'href="{html.escape(_path_url("category", category_slug))}" '
        f'target="_self">All</a>'
    ]
    for content_type in content_types:
        label = content_type.replace("_", " ").title()
        css_class = (
            "social-link active-chip"
            if content_type == selected_type
            else "social-link"
        )
        links.append(
            f'<a class="{css_class}" '
            f'href="{html.escape(_local_url(category=category_slug, type=content_type))}" '
            f'target="_self">{html.escape(label)}</a>'
        )
    st.markdown(
        f'<div class="social-row">{"".join(links)}</div>',
        unsafe_allow_html=True,
    )


def _find_category(
    categories: list[dict[str, Any]],
    selected_category: str,
) -> dict[str, Any] | None:
    selected = str(selected_category or "").strip()
    for category in categories:
        if selected in {
            str(category.get("slug") or "").strip(),
            str(category.get("id") or "").strip(),
        }:
            return category
    return None


def _matches_content_identifier(item: dict[str, Any], identifier: str) -> bool:
    selected = str(identifier or "").strip()
    return selected in {
        _content_slug(item),
        str(item.get("id") or "").strip(),
    }


def _all_public_content(limit: int = 80) -> list[dict[str, Any]]:
    items = _with_deadline(
        lambda: list_content(public_only=True, limit=limit),
        default=[],
        label="Public content loading: all",
        timeout_seconds=2.5,
    )
    return _dedupe_research_items(items)


def _content_items_by_type(
    content_types: tuple[str, ...],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Load and merge public content rows across multiple content types."""
    items: list[dict[str, Any]] = []
    for content_type in content_types:
        items.extend(_safe_content(content_type, limit))
    items.sort(
        key=lambda item: item.get("published_at") or item.get("created_at"),
        reverse=True,
    )
    return _dedupe_research_items(items)


def _render_back_home_button() -> None:
    if st.button("← Back to Home"):
        try:
            st.query_params.clear()
            st.rerun()
        except Exception:
            st.experimental_set_query_params()
            st.experimental_rerun()


def _render_research_content() -> None:
    items = _content_items_by_type(BLOG_CONTENT_TYPES, limit=10)[:6]
    if not items:
        return
    st.markdown(
        '<h2 class="section-title">Latest Research & Education</h2>',
        unsafe_allow_html=True,
    )
    _render_content_grid(items, empty_message="")


def _render_homepage_post_gallery() -> None:
    """Render WordPress-style homepage post galleries."""
    items = _content_items_by_type(BLOG_CONTENT_TYPES, limit=60)
    if not items:
        return
    st.markdown(
        '<h2 class="section-title">Post Gallery</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="section-subtitle">Fresh market research, popular reads, and posts that need attention.</p>',
        unsafe_allow_html=True,
    )
    latest, popular, low_view = _split_post_gallery_items(items)
    gallery_tabs = st.tabs(["Latest Posts", "High Views", "Low Views"])
    with gallery_tabs[0]:
        _render_content_grid(latest[:6], empty_message="No latest posts yet.")
    with gallery_tabs[1]:
        _render_content_grid(popular[:6], empty_message="No high-view posts yet.")
    with gallery_tabs[2]:
        _render_content_grid(low_view[:6], empty_message="No low-view posts yet.")


def _split_post_gallery_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    latest = list(items)
    popular = sorted(
        items,
        key=lambda item: int(item.get("view_count") or 0),
        reverse=True,
    )
    low_view = sorted(
        items,
        key=lambda item: (
            int(item.get("view_count") or 0),
            str(item.get("published_at") or item.get("created_at") or ""),
        ),
    )
    return latest, popular, low_view


def _render_view_segments(items: list[dict[str, Any]]) -> None:
    popular = [
        item for item in sorted(
            items,
            key=lambda row: int(row.get("view_count") or 0),
            reverse=True,
        )
        if int(item.get("view_count") or 0) > 0
    ][:4]
    low_view = [
        item for item in sorted(items, key=lambda row: int(row.get("view_count") or 0))
        if int(item.get("view_count") or 0) == 0
    ][:4]
    if not popular and not low_view:
        return
    st.markdown("### Popular / Needs Boost")
    cols = st.columns(2)
    with cols[0]:
        st.caption("High views")
        _render_compact_post_list(popular, "No views recorded yet.")
    with cols[1]:
        st.caption("Low views")
        _render_compact_post_list(low_view, "No low-view posts.")


def _render_compact_post_list(items: list[dict[str, Any]], empty: str) -> None:
    if not items:
        st.info(empty)
        return
    for item in items:
        title = html.escape(str(item.get("title") or "Untitled"))
        url = html.escape(_content_url(item))
        views = int(item.get("view_count") or 0)
        st.markdown(
            f'<a class="social-link" href="{url}" target="_self">{title} · {views} views</a>',
            unsafe_allow_html=True,
        )


def _render_related_posts(item: dict[str, Any]) -> None:
    related = _related_posts(item, _all_public_content(limit=80))
    if not related:
        return
    st.markdown(
        '<h2 class="section-title">Related Posts</h2>',
        unsafe_allow_html=True,
    )
    _render_content_grid(related[:4], empty_message="")


def _related_posts(
    item: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    item_id = str(item.get("id") or "")
    category_id = str(item.get("category_id") or "")
    category_slug = str(item.get("category_slug") or "")
    subcategory = _slug_fragment(str(item.get("subcategory") or ""))
    related: list[dict[str, Any]] = []
    for candidate in candidates:
        if str(candidate.get("id") or "") == item_id:
            continue
        same_category = (
            category_id
            and str(candidate.get("category_id") or "") == category_id
        ) or (
            category_slug
            and str(candidate.get("category_slug") or "") == category_slug
        )
        same_subcategory = (
            subcategory
            and _slug_fragment(str(candidate.get("subcategory") or "")) == subcategory
        )
        if same_category or same_subcategory:
            related.append(candidate)
    return related


def _render_content_grid(
    items: list[dict[str, Any]],
    *,
    empty_message: str,
) -> None:
    if not items:
        if empty_message:
            st.info(empty_message)
        return
    for start in range(0, len(items), 2):
        columns = st.columns(2)
        for column, item in zip(columns, items[start : start + 2]):
            with column:
                _render_content_card(item)


def _render_content_card(item: dict[str, Any]) -> None:
    title = str(item.get("title") or "Research Article")
    content_type = str(item.get("content_type", "")).replace("_", " ").title()
    excerpt = str(item.get("excerpt") or "").strip()
    slug = _content_slug(item)
    url = _content_url(item) if slug else str(item.get("external_url") or "#")
    views = int(item.get("view_count") or 0)
    if item.get("image_url"):
        media = (
            f'<img class="content-image" src="{html.escape(str(item["image_url"]))}" '
            f'alt="{html.escape(title)}" loading="lazy">'
        )
    else:
        media = _fallback_card_html(title, content_type or "Market Research")

    card_html = (
        f'<a class="content-card clickable-card" href="{html.escape(url)}" '
        'target="_self">'
        f"{media}"
        '<div class="content-card-body">'
        f'<div class="eyebrow">{html.escape(content_type or "Research")}</div>'
        f"<h3>{html.escape(title)}</h3>"
        f"<p>{html.escape(excerpt)}</p>"
        f'<div class="card-link-text">{views} views · Read full post →</div>'
        "</div>"
        "</a>"
    )
    st.markdown(card_html, unsafe_allow_html=True)


def _render_profit_proof(public_telegram_url: str) -> None:
    items = _safe_content("PROFIT_SCREENSHOT", 6)
    st.markdown('<h2 class="section-title">Published Trading Results</h2>', unsafe_allow_html=True)
    st.caption(
        "Selected historical outcomes shared for transparency. Individual "
        "results vary and do not guarantee future performance."
    )
    if items:
        for start in range(0, len(items), 3):
            columns = st.columns(3)
            for column, item in zip(columns, items[start : start + 3]):
                with column:
                    if item.get("image_url"):
                        st.image(
                            item["image_url"],
                            caption=item["title"],
                            use_container_width=True,
                        )
    else:
        st.info("No profit screenshots have been published yet.")
    if public_telegram_url:
        st.link_button(
            "View Public Profit-Proof Channel",
            public_telegram_url,
            use_container_width=False,
        )


def _render_subscription(settings: Any, on_sign_in: Callable[[], None]) -> None:
    st.markdown('<h2 class="section-title">Payment & Subscription</h2>', unsafe_allow_html=True)
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown(
            """
            <div class="premium-card">
                <div class="eyebrow">VERIFIED MEMBER ACCESS</div>
                <h3>Private signal delivery and member support</h3>
                <p>
                    Submit your USDT transaction inside the secure User Area.
                    Access links remain hidden while payment is pending or
                    under review.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        price = settings.subscription_price_usdt or "Configured in checkout"
        network = settings.usdt_network or "Shown securely after sign-in"
        st.metric("Subscription", f"{price} USDT" if price[0].isdigit() else price)
        st.caption(f"Network: {network}")
        if st.button("Start Secure Verification", use_container_width=True):
            on_sign_in()


def _render_locked_contact(on_sign_in: Callable[[], None]) -> None:
    st.markdown('<h2 class="section-title">Contact & Member Channels</h2>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="locked-box">
            🔒 Private Telegram and WhatsApp joining links are protected.
            Sign in and complete payment verification to unlock them.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Sign In to Unlock", key="contact_sign_in"):
        on_sign_in()


def _render_social_share(app_url: str) -> None:
    if not app_url:
        return
    encoded_url = quote(app_url, safe="")
    encoded_text = quote(
        "Explore XAUUSD and crypto market intelligence",
        safe="",
    )
    links = {
        "𝕏 Share": f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_text}",
        "Facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        "LinkedIn": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
    }
    link_html = "".join(
        f'<a class="social-link" target="_blank" rel="noopener noreferrer" '
        f'href="{html.escape(url)}">{html.escape(label)}</a>'
        for label, url in links.items()
    )
    st.markdown(
        f'<div class="social-row">{link_html}</div>',
        unsafe_allow_html=True,
    )


def _render_disclaimer() -> None:
    st.markdown(
        """
        <div class="risk-box">
            <strong>Risk Disclaimer:</strong> Trading gold, cryptocurrencies,
            and leveraged instruments involves substantial risk. Market
            analysis and signals are informational only and are not a promise
            of profit or individualized financial advice. You remain
            responsible for every trading decision and should never risk
            capital you cannot afford to lose.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_public_page_footer() -> None:
    """Render the final public page footer stack after all page content."""
    _render_disclaimer()
    _render_site_footer()


def _render_site_footer() -> None:
    """Render public website footer navigation and legal links."""
    settings = get_settings()
    links = [
        ("Home", "/"),
        ("About", "/about"),
        ("Blog", "/blog"),
        ("Signals", "/signals"),
        ("XAUUSD", "/signals/xauusd"),
        ("Market Analysis", "/market-analysis"),
        ("Nifty & Options", "/market-analysis/nifty"),
        ("Crypto Volatility", "/market-analysis/crypto"),
        ("SEO & Automation", "/blog/seo-tools"),
        ("Contact", "/contact"),
        ("Privacy Policy", "/privacy-policy"),
        ("Terms", "/terms"),
        ("Risk Disclaimer", "/risk-disclaimer"),
    ]
    link_html = "".join(
        f'<a href="{html.escape(url)}" target="_self">{html.escape(label)}</a>'
        for label, url in links
    )
    social_links = []
    for label, url in (
        ("Telegram", settings.telegram_invite_url),
        ("Profit Proof", settings.profit_proof_telegram_url),
        ("WhatsApp", settings.support_whatsapp_url),
    ):
        if url:
            social_links.append((label, url))
    social_html = "".join(
        '<a target="_blank" rel="noopener noreferrer" '
        f'href="{html.escape(url)}">{html.escape(label)}</a>'
        for label, url in social_links
    )
    current_year = datetime.now().year
    st.markdown(
        f"""
        <div class="site-footer" role="contentinfo" aria-label="Website footer">
            <div class="footer-grid">
                <div>
                    <div class="footer-brand">AI Market Analytics Pro</div>
                    <div class="footer-note">
                        Research, education, XAUUSD signal context, and member support.
                    </div>
                    <div class="footer-note">
                        © {current_year} AI Market Analytics Pro. All rights reserved.
                    </div>
                </div>
                <div>
                    <div class="footer-links">{link_html}</div>
                    <div class="footer-social">{social_html}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safe_content(content_type: str, limit: int) -> list[dict[str, Any]]:
    return _with_deadline(
        lambda: list_content(
            content_type=content_type,
            public_only=True,
            limit=limit,
        ),
        default=[],
        label=f"Public content loading: type={content_type}",
        timeout_seconds=2.5,
    )
