"""Public marketing website for AI Market Analytics Pro."""

from __future__ import annotations

import html
from typing import Any, Callable
from urllib.parse import quote, urlencode

from loguru import logger
import streamlit as st

from components.market_ticker import render_market_ticker
from config import get_settings
from services.content_service import (
    get_site_setting,
    list_categories,
    list_content,
)
from services.public_market_service import (
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
    selected_post = _query_param_value("post")
    selected_announcement = _query_param_value("announcement")
    selected_category = _query_param_value("category")

    if selected_post:
        _render_content_route(selected_post)
        _render_disclaimer()
        return

    if selected_announcement:
        _render_announcement_route(selected_announcement)
        _render_disclaimer()
        return

    if selected_category:
        _render_category_route(selected_category, categories, on_sign_in)
        _render_disclaimer()
        return

    _render_hero(on_sign_in)

    xauusd = get_xauusd_snapshot(supabase)
    crypto_quotes = get_top_crypto_gainers(20)
    render_market_ticker(xauusd, crypto_quotes)
    _render_xauusd_signal_section(xauusd or {}, settings, on_sign_in)

    _render_categories(categories)
    _render_announcements()
    _render_research_content()
    try:
        profit_proof_url = get_site_setting("profit_proof_telegram_url")
    except Exception:
        profit_proof_url = ""
    _render_profit_proof(
        profit_proof_url or settings.profit_proof_telegram_url
    )
    _render_subscription(settings, on_sign_in)
    _render_locked_contact(on_sign_in)
    _render_social_share(settings.app_base_url)
    _render_disclaimer()


def _render_nav(brand_name: str, on_sign_in: Callable[[], None]) -> None:
    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            f"""
            <div class="site-nav">
                <a class="brand" href="?" target="_self">
                    {html.escape(brand_name)}<span class="brand-dot">.</span>
                </a>
                <div class="nav-note">
                    XAUUSD · Crypto · Research · Education
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Sign In", type="primary", use_container_width=True):
            on_sign_in()


def _render_hero(on_sign_in: Callable[[], None]) -> None:
    st.markdown(
        """
        <section class="hero">
            <div class="eyebrow">MARKET INTELLIGENCE · RISK FIRST</div>
            <h1>Clearer signals for gold and digital assets.</h1>
            <p>
                Structured XAUUSD and crypto market levels, disciplined risk
                context, timely announcements, and a verified-member delivery
                experience built for traders who value clarity.
            </p>
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


def _safe_categories() -> list[dict[str, Any]]:
    try:
        return list_categories(public_only=True)
    except Exception:
        logger.exception("Public category loading failed")
        return []


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
                url = _local_url(category=slug)
                st.markdown(
                    f"""
                    <a class="premium-card clickable-card" href="{html.escape(url)}" target="_self">
                        <div class="category-icon">
                            {html.escape(str(category.get('icon') or '•'))}
                        </div>
                        <h3>{html.escape(str(category['title']))}</h3>
                        <p>{html.escape(str(category.get('description') or ''))}</p>
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
                url = _local_url(announcement=slug) if slug else "#"
                st.markdown(
                    f"""
                    <a class="premium-card announcement-card clickable-card"
                       href="{html.escape(url)}" target="_self">
                        <div class="eyebrow">Announcement</div>
                        <h3>{html.escape(str(item.get('title') or 'Announcement'))}</h3>
                        <p>{html.escape(str(item.get('excerpt') or item.get('body') or ''))}</p>
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


def _content_slug(item: dict[str, Any]) -> str:
    return str(
        item.get("seo_slug")
        or item.get("slug")
        or item.get("id")
        or ""
    ).strip()


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


def _fallback_card_html(
    title: str = "XAUUSD Market Research",
    label: str = "XAUUSD RESEARCH",
) -> str:
    """Return a professional fallback banner when a content image is absent."""
    safe_title = html.escape(title or "XAUUSD Market Research")
    safe_label = html.escape(label or "XAUUSD RESEARCH")
    return f"""
    <div class="fallback-trading-card">
        <div>
            <div class="fallback-label">{safe_label}</div>
            <div class="fallback-title">{safe_title}</div>
        </div>
    </div>
    """


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
    if excerpt:
        st.info(excerpt)

    body = str(item.get("body") or "").strip()
    if body:
        st.markdown(body)
    else:
        st.warning("Article body is empty.")

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


def _render_content_route(selected_post: str) -> None:
    items = _all_public_content()
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


def _render_category_route(
    selected_category: str,
    categories: list[dict[str, Any]],
    on_sign_in: Callable[[], None],
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
    selected_type = _query_param_value("type").strip().upper()
    available_types = sorted(
        {
            str(item.get("content_type") or "").strip().upper()
            for item in items
            if item.get("content_type")
        }
    )
    if available_types:
        _render_subcategory_links(
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
    content_types: list[str],
    selected_type: str,
) -> None:
    links = [
        f'<a class="social-link" '
        f'href="{html.escape(_local_url(category=category_slug))}" '
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
    try:
        items = list_content(public_only=True, limit=limit)
    except Exception:
        logger.exception("Public content loading failed: all")
        return []
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
    items: list[dict[str, Any]] = []
    for content_type in ("AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"):
        items.extend(_safe_content(content_type, 10))
    items.sort(
        key=lambda item: item.get("published_at") or item.get("created_at"),
        reverse=True,
    )
    items = _dedupe_research_items(items)

    items = items[:6]
    if not items:
        return
    st.markdown(
        '<h2 class="section-title">Latest Research & Education</h2>',
        unsafe_allow_html=True,
    )
    _render_content_grid(items, empty_message="")


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
    url = _local_url(post=slug) if slug else str(item.get("external_url") or "#")
    if item.get("image_url"):
        media = (
            f'<img class="content-image" src="{html.escape(str(item["image_url"]))}" '
            f'alt="{html.escape(title)}" loading="lazy">'
        )
    else:
        media = _fallback_card_html(title, content_type or "Market Research")

    st.markdown(
        f"""
        <a class="content-card clickable-card" href="{html.escape(url)}" target="_self">
            {media}
            <div class="content-card-body">
                <div class="eyebrow">{html.escape(content_type or "Research")}</div>
                <h3>{html.escape(title)}</h3>
                <p>{html.escape(excerpt)}</p>
                <div class="card-link-text">Read full post →</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )


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


def _safe_content(content_type: str, limit: int) -> list[dict[str, Any]]:
    try:
        return list_content(
            content_type=content_type,
            public_only=True,
            limit=limit,
        )
    except Exception:
        logger.exception("Public content loading failed: type={}", content_type)
        return []
