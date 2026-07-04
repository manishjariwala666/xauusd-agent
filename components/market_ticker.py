"""Responsive public market price components."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from services.public_market_service import CryptoQuote


def render_market_ticker(
    xauusd: dict[str, Any] | None,
    crypto_quotes: list[CryptoQuote],
) -> None:
    """Render XAUUSD pricing and an animated top-gainers ticker."""
    st.markdown('<h2 class="section-title">Live Market Pulse</h2>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-subtitle">Current gold reference and top liquid crypto gainers.</p>',
        unsafe_allow_html=True,
    )
    if xauusd:
        observed_at = xauusd["observed_at"].strftime("%d %b %Y · %H:%M %Z")
        st.markdown(
            f"""
            <div class="price-panel">
                <div class="eyebrow">XAUUSD MARKET REFERENCE</div>
                <div class="price-value">${float(xauusd['price']):,.2f}</div>
                <div class="nav-note">
                    Updated {html.escape(observed_at)} ·
                    {html.escape(str(xauusd['source']))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Live XAUUSD pricing is temporarily unavailable.")

    if not crypto_quotes:
        st.caption("Crypto ticker is temporarily unavailable.")
        return

    items = "".join(_quote_html(quote) for quote in crypto_quotes)
    # Duplicate track content creates a seamless CSS loop.
    st.markdown(
        f"""
        <div class="market-marquee" aria-label="Top crypto gainers">
            <div class="market-track">{items}{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _quote_html(quote: CryptoQuote) -> str:
    return (
        '<span class="ticker-item">'
        f'<span class="ticker-symbol">{html.escape(quote.symbol)}</span> '
        f'<span class="ticker-price">${quote.price_usd:,.6g}</span> '
        f'<span class="ticker-up">▲ {quote.change_24h:.2f}%</span>'
        "</span>"
    )
