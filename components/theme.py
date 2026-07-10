"""Shared premium trading website theme."""

from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    """Apply responsive visual styling without exposing implementation data."""
    st.markdown(
        """
        <style>
            :root {
                --bg: #060914;
                --surface: #0d1424;
                --surface-2: #121c31;
                --border: #24324b;
                --text: #eef4ff;
                --muted: #91a0b8;
                --gold: #f4c15d;
                --green: #32d583;
                --red: #ff6b72;
                --blue: #67a6ff;
            }
            #MainMenu, footer, [data-testid="stToolbar"] {
                visibility: hidden;
            }
            .stApp {
                background:
                    radial-gradient(circle at 12% -10%, #17284d 0, transparent 34%),
                    radial-gradient(circle at 92% 5%, #3b2714 0, transparent 25%),
                    var(--bg);
                color: var(--text);
            }
            .block-container {
                max-width: 100%;
                width: 100%;
                padding-top: 1.25rem;
                padding-bottom: 3rem;
                padding-left: clamp(.9rem, 3vw, 2.4rem);
                padding-right: clamp(.9rem, 3vw, 2.4rem);
            }
            .site-nav {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: .8rem 1rem;
                border: 1px solid var(--border);
                border-radius: 16px;
                background: rgba(13, 20, 36, .88);
                backdrop-filter: blur(14px);
                margin-bottom: 1rem;
            }
            .brand {
                text-decoration: none !important;
                font-weight: 800;
                letter-spacing: -.02em;
                color: var(--text) !important;
            }
            .brand-dot { color: var(--gold); }
            .nav-note { color: var(--muted); font-size: .84rem; }
            .nav-note a {
                color: var(--muted) !important;
                text-decoration: none !important;
                margin-left: .85rem;
                font-weight: 700;
            }
            .nav-note a:hover { color: var(--gold) !important; }
            .hero {
                position: relative;
                overflow: hidden;
                padding: clamp(2rem, 7vw, 5.5rem) clamp(1.2rem, 5vw, 4.5rem);
                border: 1px solid var(--border);
                border-radius: 26px;
                background:
                    linear-gradient(135deg, rgba(20, 31, 54, .96), rgba(8, 12, 24, .96));
                box-shadow: 0 25px 80px rgba(0, 0, 0, .32);
            }
            .hero:after {
                content: "";
                position: absolute;
                width: 340px;
                height: 340px;
                right: -100px;
                top: -130px;
                border-radius: 50%;
                background: rgba(244, 193, 93, .12);
                filter: blur(4px);
            }
            .eyebrow {
                color: var(--gold);
                font-size: .78rem;
                font-weight: 800;
                letter-spacing: .16em;
                text-transform: uppercase;
            }
            .hero h1 {
                max-width: 820px;
                margin: .7rem 0 1rem;
                color: var(--text);
                font-size: clamp(2.4rem, 6vw, 5.2rem);
                line-height: .98;
                letter-spacing: -.055em;
            }
            .hero p {
                max-width: 700px;
                color: #b7c4d9;
                font-size: clamp(1rem, 2vw, 1.18rem);
                line-height: 1.7;
            }
            .trust-row {
                display: flex;
                flex-wrap: wrap;
                gap: .6rem;
                margin-top: 1.4rem;
            }
            .trust-chip {
                padding: .52rem .78rem;
                border: 1px solid #33425e;
                border-radius: 999px;
                color: #c9d5e8;
                background: rgba(8, 13, 26, .54);
                font-size: .82rem;
            }
            .section-title {
                margin: 2.8rem 0 1rem;
                font-size: clamp(1.55rem, 3vw, 2.25rem);
                letter-spacing: -.03em;
                color: var(--text);
            }
            .section-subtitle { color: var(--muted); margin-top: -.6rem; }
            .premium-card {
                display: block;
                height: 100%;
                padding: 1.15rem;
                border: 1px solid var(--border);
                border-radius: 16px;
                background: linear-gradient(145deg, var(--surface-2), var(--surface));
            }
            .clickable-card {
                color: inherit !important;
                text-decoration: none !important;
                transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
            }
            .clickable-card:hover {
                transform: translateY(-3px);
                border-color: rgba(244, 193, 93, .58);
                box-shadow: 0 18px 45px rgba(0, 0, 0, .24);
            }
            .premium-card h3 { color: var(--text); margin: .4rem 0; }
            .premium-card p { color: var(--muted); line-height: 1.6; }
            .category-icon { font-size: 1.45rem; }
            .card-link-text {
                margin-top: .9rem;
                color: var(--gold);
                font-weight: 800;
                font-size: .9rem;
            }
            .announcement-card {
                min-height: 175px;
            }
            .signal-desk-card {
                height: 100%;
                padding: 1.35rem;
                border: 1px solid #554628;
                border-radius: 20px;
                background:
                    radial-gradient(circle at top right, rgba(244, 193, 93, .18), transparent 34%),
                    linear-gradient(140deg, #141f36, #090d18);
            }
            .signal-desk-card h3 {
                margin: .35rem 0 .5rem;
                color: var(--gold);
                font-size: clamp(2rem, 4vw, 3rem);
                letter-spacing: -.04em;
            }
            .signal-desk-card p {
                color: #b7c4d9;
                line-height: 1.65;
            }
            .price-panel {
                padding: 1.3rem;
                border: 1px solid #554628;
                border-radius: 18px;
                background: linear-gradient(140deg, #1a1b1d, #171208);
            }
            .price-value {
                color: var(--gold);
                font-size: clamp(2rem, 5vw, 3.4rem);
                font-weight: 800;
                letter-spacing: -.04em;
            }
            .market-marquee {
                overflow: hidden;
                border: 1px solid var(--border);
                border-radius: 12px;
                background: #080d19;
                white-space: nowrap;
                margin: 1rem 0;
            }
            .market-track {
                display: inline-flex;
                gap: 1.4rem;
                min-width: max-content;
                padding: .72rem 1rem;
                animation: market-scroll 48s linear infinite;
            }
            .market-marquee:hover .market-track {
                animation-play-state: paused;
            }
            .ticker-symbol { color: var(--text); font-weight: 800; }
            .ticker-price { color: #cbd7e8; }
            .ticker-up { color: var(--green); }
            @keyframes market-scroll {
                from { transform: translateX(0); }
                to { transform: translateX(-50%); }
            }
            .status-banner {
                padding: 1rem 1.1rem;
                border-radius: 14px;
                border: 1px solid var(--border);
                background: var(--surface);
            }
            .status-verified { border-color: rgba(50, 213, 131, .5); }
            .status-rejected { border-color: rgba(255, 107, 114, .5); }
            .locked-box {
                padding: 1.2rem;
                border: 1px dashed #42516b;
                border-radius: 14px;
                color: var(--muted);
                background: rgba(13, 20, 36, .7);
            }
            .risk-box {
                padding: 1rem 1.1rem;
                border-left: 4px solid var(--gold);
                border-radius: 8px;
                background: #121522;
                color: #aebbd0;
                font-size: .9rem;
                line-height: 1.6;
            }
            .social-row {
                display: flex;
                flex-wrap: wrap;
                gap: .7rem;
                margin: 1rem 0;
            }
            .social-link {
                color: #cbd7e8 !important;
                text-decoration: none !important;
                border: 1px solid var(--border);
                border-radius: 999px;
                padding: .5rem .8rem;
                background: var(--surface);
            }
            .content-image {
                width: 100%;
                aspect-ratio: 16 / 10;
                object-fit: cover;
                border-radius: 12px;
                border: 1px solid var(--border);
            }
            .content-card {
                display: block;
                height: 100%;
                overflow: hidden;
                border: 1px solid var(--border);
                border-radius: 18px;
                background: linear-gradient(145deg, var(--surface-2), var(--surface));
                color: inherit !important;
                text-decoration: none !important;
            }
            .content-card .content-image,
            .content-card .fallback-trading-card {
                border-radius: 0;
                border-left: 0;
                border-right: 0;
                border-top: 0;
                margin: 0;
            }
            .content-card-body {
                padding: 1rem 1.1rem 1.15rem;
            }
            .content-card h3 {
                margin: .35rem 0 .5rem;
                color: var(--text);
                line-height: 1.25;
            }
            .content-card p {
                color: var(--muted);
                line-height: 1.6;
            }
            .fallback-trading-card {
                min-height: 165px;
                border-radius: 16px;
                padding: 22px;
                margin-bottom: 14px;
                background:
                    linear-gradient(120deg, rgba(255,255,255,.08), transparent 24%),
                    radial-gradient(circle at top left, rgba(245, 158, 11, .35), transparent 34%),
                    linear-gradient(135deg, #101827 0%, #1f2937 48%, #3b2404 100%);
                border: 1px solid rgba(255,255,255,.14);
                display: flex;
                align-items: end;
            }
            .fallback-label {
                font-size: 12px;
                letter-spacing: .16em;
                color: #fbbf24;
                font-weight: 800;
                text-transform: uppercase;
            }
            .fallback-title {
                font-size: 22px;
                line-height: 1.25;
                color: white;
                font-weight: 800;
                margin-top: 8px;
            }
            .active-chip {
                border-color: rgba(244, 193, 93, .7) !important;
                color: var(--gold) !important;
            }
            @media (max-width: 700px) {
                .block-container { padding: .75rem .8rem 2rem; }
                .site-nav { align-items: flex-start; flex-direction: column; }
                .hero { border-radius: 18px; }
                .nav-note { display: none; }
                .fallback-trading-card { min-height: 135px; }
            }
            @media (prefers-reduced-motion: reduce) {
                .market-track { animation: none; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
