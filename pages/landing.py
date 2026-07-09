"""Public marketing website for AI Market Analytics Pro."""

from __future__ import annotations

import html
from typing import Any, Callable
from urllib.parse import quote

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
    _render_hero(on_sign_in)

    xauusd = get_xauusd_snapshot(supabase)
    crypto_quotes = get_top_crypto_gainers(20)
    render_market_ticker(xauusd, crypto_quotes)

    categories = _safe_categories()
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
                <div class="brand">
                    {html.escape(brand_name)}<span class="brand-dot">.</span>
                </div>
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
                st.markdown(
                    f"""
                    <div class="premium-card">
                        <div class="category-icon">
                            {html.escape(str(category.get('icon') or '•'))}
                        </div>
                        <h3>{html.escape(str(category['title']))}</h3>
                        <p>{html.escape(str(category.get('description') or ''))}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_announcements() -> None:
    items = _safe_content("ANNOUNCEMENT", 4)
    if not items:
        return
    st.markdown('<h2 class="section-title">Announcements</h2>', unsafe_allow_html=True)
    for item in items:
        with st.container(border=True):
            st.subheader(item["title"])
            st.write(item.get("excerpt") or item.get("body") or "")



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


def _fallback_blog_banner(title: str = "XAUUSD Market Research") -> None:
    safe_title = html.escape(title or "XAUUSD Market Research")
    st.markdown(
        f"""
        <div style="
            min-height: 150px;
            border-radius: 16px;
            padding: 22px;
            margin-bottom: 14px;
            background:
                radial-gradient(circle at top left, rgba(245, 158, 11, .35), transparent 32%),
                linear-gradient(135deg, #101827 0%, #1f2937 48%, #3b2404 100%);
            border: 1px solid rgba(255,255,255,.14);
            display: flex;
            align-items: end;
        ">
            <div>
                <div style="font-size: 12px; letter-spacing: .16em; color: #fbbf24; font-weight: 700;">
                    XAUUSD RESEARCH
                </div>
                <div style="font-size: 22px; line-height: 1.25; color: white; font-weight: 800; margin-top: 8px;">
                    {safe_title}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_content_detail(item: dict[str, Any]) -> None:
    title = str(item.get("title") or "Research Article")
    st.markdown(f'<h1 class="section-title">{html.escape(title)}</h1>', unsafe_allow_html=True)

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


def _render_research_content() -> None:
    items: list[dict[str, Any]] = []
    for content_type in ("AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION"):
        items.extend(_safe_content(content_type, 10))
    items.sort(
        key=lambda item: item.get("published_at") or item.get("created_at"),
        reverse=True,
    )

    selected_post = _query_param_value("post")
    if selected_post:
        for item in items:
            if _content_slug(item) == selected_post or str(item.get("id")) == selected_post:
                _render_content_detail(item)
                return
        st.warning("Article not found or not published.")
        if st.button("← Back to Research"):
            try:
                st.query_params.clear()
                st.rerun()
            except Exception:
                st.experimental_set_query_params()
                st.experimental_rerun()
        return

    items = items[:6]
    if not items:
        return
    st.markdown('<h2 class="section-title">Latest Research & Education</h2>', unsafe_allow_html=True)
    for start in range(0, len(items), 2):
        columns = st.columns(2)
        for column, item in zip(columns, items[start : start + 2]):
            with column:
                with st.container(border=True):
                    title = str(item.get("title") or "Research Article")
                    if item.get("image_url"):
                        st.image(str(item["image_url"]), use_container_width=True)
                    else:
                        _fallback_blog_banner(title)
                    st.caption(
                        str(item.get("content_type", "")).replace("_", " ")
                    )
                    st.subheader(title)
                    st.write(item.get("excerpt") or "")

                    slug = _content_slug(item)
                    if slug:
                        st.markdown(
                            f'<a href="?post={quote(slug)}" target="_self" '
                            f'style="display:block;text-align:center;padding:0.65rem 1rem;'
                            f'border-radius:0.55rem;background:#2563eb;color:white;'
                            f'text-decoration:none;font-weight:700;margin-top:0.75rem;">'
                            f'Read Full Article</a>',
                            unsafe_allow_html=True,
                        )
                    elif item.get("external_url"):
                        st.link_button(
                            "Read More",
                            str(item["external_url"]),
                            use_container_width=True,
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
