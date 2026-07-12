"""Direct Streamlit route for the public About page."""

from __future__ import annotations

import streamlit as st

from components.theme import apply_theme
from pages.landing import _render_content_route, _render_public_page_footer


st.set_page_config(
    page_title="About | AI Market Analytics Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

_render_content_route("about", allowed_types=("PAGE",))
_render_public_page_footer()
