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
            .admin-hero {
                position: relative;
                overflow: hidden;
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                align-items: center;
                gap: 1rem;
                padding: clamp(1.4rem, 4vw, 3rem);
                margin-bottom: 1.2rem;
                border-radius: 28px;
                border: 1px solid rgba(103, 166, 255, .35);
                background:
                    radial-gradient(circle at 82% 18%, rgba(103, 166, 255, .32), transparent 26%),
                    linear-gradient(135deg, rgba(47, 107, 255, .95), rgba(96, 139, 255, .72));
                box-shadow: 0 24px 70px rgba(37, 99, 235, .24);
            }
            .admin-hero:before {
                content: "";
                position: absolute;
                inset: 0;
                background:
                    linear-gradient(120deg, transparent 0 34%, rgba(255,255,255,.12) 34% 48%, transparent 48%),
                    radial-gradient(circle at 10% 100%, rgba(255,255,255,.18), transparent 35%);
                pointer-events: none;
            }
            .admin-hero > * { position: relative; z-index: 1; }
            .admin-hero h1 {
                margin: .45rem 0 .55rem;
                font-size: clamp(2rem, 5vw, 3.6rem);
                color: white;
                line-height: 1.02;
                letter-spacing: -.055em;
            }
            .admin-hero p {
                max-width: 760px;
                margin: 0;
                color: rgba(255,255,255,.86);
                font-size: 1.02rem;
                line-height: 1.65;
            }
            .admin-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: .55rem;
                margin-top: 1rem;
            }
            .admin-chip-row span {
                padding: .48rem .72rem;
                border-radius: 999px;
                background: rgba(255,255,255,.14);
                border: 1px solid rgba(255,255,255,.22);
                color: white;
                font-size: .82rem;
                font-weight: 800;
            }
            .admin-hero-orb {
                width: clamp(72px, 10vw, 124px);
                height: clamp(72px, 10vw, 124px);
                display: grid;
                place-items: center;
                border-radius: 999px;
                background: rgba(255,255,255,.18);
                border: 1px solid rgba(255,255,255,.28);
                font-size: clamp(2.2rem, 5vw, 4rem);
                box-shadow: inset 0 0 35px rgba(255,255,255,.2);
            }
            .admin-agent-card {
                height: 100%;
                padding: 1.05rem;
                border-radius: 20px;
                border: 1px solid rgba(103, 166, 255, .22);
                background:
                    linear-gradient(145deg, rgba(18, 28, 49, .96), rgba(13, 20, 36, .94));
                box-shadow: 0 14px 40px rgba(0,0,0,.18);
            }
            .admin-agent-icon {
                width: 44px;
                height: 44px;
                display: grid;
                place-items: center;
                border-radius: 14px;
                background: rgba(103, 166, 255, .13);
                border: 1px solid rgba(103, 166, 255, .2);
                font-size: 1.35rem;
                margin-bottom: .75rem;
            }
            .admin-agent-card h3 {
                margin: 0 0 .35rem;
                color: var(--text);
                font-size: 1.05rem;
            }
            .admin-agent-card p {
                min-height: 44px;
                margin: 0 0 .8rem;
                color: var(--muted);
                line-height: 1.5;
                font-size: .9rem;
            }
            .admin-agent-status {
                color: #cbd7e8;
                font-weight: 800;
                font-size: .88rem;
                margin-bottom: .65rem;
            }
            .admin-agent-meta {
                display: flex;
                justify-content: space-between;
                gap: .5rem;
                color: var(--muted);
                font-size: .82rem;
                border-top: 1px solid rgba(255,255,255,.08);
                padding-top: .65rem;
            }
            @media (max-width: 700px) {
                .block-container { padding: .75rem .8rem 2rem; }
                .site-nav { align-items: flex-start; flex-direction: column; }
                .hero { border-radius: 18px; }
                .nav-note { display: none; }
                .fallback-trading-card { min-height: 135px; }
                .admin-hero { grid-template-columns: 1fr; border-radius: 20px; }
                .admin-hero-orb { display: none; }
            }
            @media (prefers-reduced-motion: reduce) {
                .market-track { animation: none; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_admin_light_theme() -> None:
    """Apply a scoped Able-Pro-inspired light admin skin.

    The public website keeps the dark trading theme. Admin screens inject this
    later so the protected control room can use a clean SaaS dashboard look
    without changing business logic or exposing internal agent details.
    """
    st.markdown(
        """
        <style>
            :root {
                --admin-bg: #f6f8fc;
                --admin-card: #ffffff;
                --admin-card-soft: #f8fafc;
                --admin-border: #e5eaf3;
                --admin-text: #182235;
                --admin-muted: #748196;
                --admin-blue: #4b7cff;
                --admin-blue-soft: #e8efff;
                --admin-green: #22b981;
                --admin-red: #ef4444;
                --admin-orange: #f59e0b;
                --admin-shadow: 0 18px 45px rgba(32, 57, 108, .08);
            }
            .stApp {
                background:
                    radial-gradient(circle at 78% -8%, rgba(75,124,255,.12), transparent 28%),
                    var(--admin-bg) !important;
                color: var(--admin-text) !important;
            }
            .block-container {
                padding-top: 1rem;
                padding-left: clamp(1rem, 2.4vw, 2rem);
                padding-right: clamp(1rem, 2.4vw, 2rem);
            }
            .stSidebar {
                background: #ffffff !important;
                border-right: 1px solid var(--admin-border);
            }
            .stSidebar [data-testid="stMarkdownContainer"],
            .stSidebar p,
            .stSidebar span,
            .stSidebar label {
                color: var(--admin-text) !important;
            }
            .admin-topbar {
                display: grid;
                grid-template-columns: auto minmax(220px, 520px) 1fr auto;
                align-items: center;
                gap: .9rem;
                margin: .2rem 0 1.2rem;
            }
            .admin-menu-button,
            .admin-icon-button {
                width: 46px;
                height: 46px;
                display: grid;
                place-items: center;
                border-radius: 12px;
                background: #edf2f8;
                color: var(--admin-muted);
                font-weight: 900;
                border: 1px solid var(--admin-border);
            }
            .admin-search-pill {
                height: 46px;
                display: flex;
                align-items: center;
                gap: .55rem;
                padding: 0 .95rem;
                border: 1px solid #d9e2ef;
                border-radius: 13px;
                background: #ffffff;
                color: #9aa7ba;
                box-shadow: 0 8px 25px rgba(27, 46, 92, .04);
            }
            .admin-topbar-actions {
                display: flex;
                justify-content: flex-end;
                align-items: center;
                gap: .55rem;
            }
            .admin-avatar {
                width: 42px;
                height: 42px;
                display: grid;
                place-items: center;
                border-radius: 999px;
                background: linear-gradient(135deg, #dbeafe, #bfdbfe);
                color: #1d4ed8;
                font-weight: 900;
                border: 1px solid #bfdbfe;
            }
            .admin-sidebar-brand {
                display: flex;
                align-items: baseline;
                gap: .25rem;
                padding: .3rem .1rem 1rem;
                color: var(--admin-blue);
                font-size: 1.65rem;
                font-weight: 900;
                letter-spacing: -.04em;
            }
            .admin-sidebar-brand small {
                color: var(--admin-blue);
                font-size: .72rem;
                font-weight: 800;
            }
            .admin-sidebar-section {
                margin: 1.05rem 0 .45rem;
                color: #5f6f86;
                font-size: .72rem;
                font-weight: 900;
                text-transform: uppercase;
                letter-spacing: .08em;
            }
            .admin-sidebar-item {
                display: flex;
                align-items: center;
                gap: .72rem;
                padding: .68rem .78rem;
                border-radius: 12px;
                color: #69778d;
                font-weight: 800;
                margin: .22rem 0;
            }
            .admin-sidebar-item.active {
                background: #edf3ff;
                color: var(--admin-blue);
            }
            .admin-hero {
                border: 0 !important;
                background:
                    radial-gradient(circle at 88% 26%, rgba(255,255,255,.34), transparent 16%),
                    linear-gradient(135deg, #3f78ff, #81a4ff) !important;
                box-shadow: 0 22px 55px rgba(75, 124, 255, .22) !important;
            }
            .admin-light-kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 1rem;
                margin: 1rem 0 1.4rem;
            }
            .admin-light-kpi {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: .8rem;
                align-items: center;
                min-height: 118px;
                padding: 1.2rem;
                border: 1px solid var(--admin-border);
                border-radius: 18px;
                background: var(--admin-card);
                box-shadow: var(--admin-shadow);
            }
            .admin-light-kpi .value {
                color: var(--admin-text);
                font-size: clamp(1.55rem, 3vw, 2.25rem);
                font-weight: 900;
                letter-spacing: -.04em;
            }
            .admin-light-kpi .label {
                color: var(--admin-muted);
                font-weight: 800;
                margin-top: .15rem;
            }
            .admin-light-kpi .trend {
                display: inline-flex;
                width: fit-content;
                margin-top: .55rem;
                padding: .22rem .48rem;
                border-radius: 999px;
                background: #ecfdf5;
                color: var(--admin-green);
                font-size: .78rem;
                font-weight: 900;
            }
            .admin-kpi-icon {
                width: 54px;
                height: 54px;
                display: grid;
                place-items: center;
                border-radius: 16px;
                background: var(--admin-blue-soft);
                color: var(--admin-blue);
                font-size: 1.55rem;
            }
            .admin-agent-card {
                border: 1px solid var(--admin-border) !important;
                background: var(--admin-card) !important;
                box-shadow: var(--admin-shadow) !important;
            }
            .admin-agent-card h3,
            .admin-agent-status {
                color: var(--admin-text) !important;
            }
            .admin-agent-card p,
            .admin-agent-meta {
                color: var(--admin-muted) !important;
            }
            .admin-agent-meta {
                border-top: 1px solid var(--admin-border) !important;
            }
            .admin-agent-icon {
                background: var(--admin-blue-soft) !important;
                border-color: #dbe7ff !important;
            }
            div[data-testid="stMetric"] {
                padding: 1rem;
                border: 1px solid var(--admin-border);
                border-radius: 16px;
                background: var(--admin-card);
                box-shadow: var(--admin-shadow);
            }
            div[data-testid="stMetric"] label,
            div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
                color: var(--admin-muted) !important;
                font-weight: 800;
            }
            div[data-testid="stMetricValue"] {
                color: var(--admin-text) !important;
                font-weight: 900;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: .2rem;
                border-bottom: 1px solid var(--admin-border);
            }
            .stTabs [data-baseweb="tab"] {
                color: var(--admin-muted);
                font-weight: 800;
                border-radius: 10px 10px 0 0;
            }
            .stTabs [aria-selected="true"] {
                color: var(--admin-blue) !important;
                background: #eef4ff;
            }
            h1, h2, h3, h4,
            [data-testid="stMarkdownContainer"] h1,
            [data-testid="stMarkdownContainer"] h2,
            [data-testid="stMarkdownContainer"] h3 {
                color: var(--admin-text);
            }
            .stDataFrame, div[data-testid="stDataFrame"] {
                border-radius: 16px;
                overflow: hidden;
                box-shadow: var(--admin-shadow);
            }
            @media (max-width: 980px) {
                .admin-topbar {
                    grid-template-columns: auto 1fr auto;
                }
                .admin-search-pill {
                    display: none;
                }
                .admin-light-kpi-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
            @media (max-width: 620px) {
                .admin-light-kpi-grid {
                    grid-template-columns: 1fr;
                }
                .admin-topbar-actions .admin-icon-button:nth-child(n+3) {
                    display: none;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
