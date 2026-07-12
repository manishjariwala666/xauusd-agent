"""Direct Streamlit route for static public pages."""

from __future__ import annotations

from urllib.parse import urlparse

import streamlit as st

from components.theme import apply_theme
from pages.landing import _render_content_route, _render_public_page_footer


st.set_page_config(
    page_title="AI Market Analytics Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()


def _path_segments() -> list[str]:
    """Read nested static-page paths from Streamlit context/headers."""
    candidates: list[str] = []
    try:
        candidates.append(getattr(st.context, "url", "") or "")
    except Exception:
        pass
    try:
        headers = getattr(st.context, "headers", {}) or {}
        for header in ("x-forwarded-uri", "x-original-uri", "referer"):
            value = headers.get(header) if hasattr(headers, "get") else ""
            if value:
                candidates.append(str(value))
    except Exception:
        pass
    for candidate in candidates:
        clean = str(candidate or "").strip()
        if not clean:
            continue
        path = urlparse(clean).path if "://" in clean else clean
        segments = [part for part in path.strip("/").split("/") if part]
        if segments:
            return segments
    return ["page", "privacy-policy"]


segments = _path_segments()
slug = segments[1] if len(segments) > 1 and segments[0] == "page" else "privacy-policy"

_render_content_route(slug, allowed_types=("PAGE",))
_render_public_page_footer()
