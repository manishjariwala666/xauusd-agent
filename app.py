"""AI Market Analytics Pro public website and protected application router."""

from __future__ import annotations

import logging

import streamlit as st
from supabase import Client, create_client

from admin.dashboard import render_admin_dashboard
from components.theme import apply_theme
from config import ConfigurationError, get_settings
from core.auth import (
    ROLE_ADMIN,
    ROLE_USER,
    get_current_role,
    get_current_user_email,
    get_payment_status,
    initialize_session,
    is_authenticated,
    logout_user,
)
from pages.landing import render_landing_page
from pages.login import login_page
from services.migration_service import apply_pending_migrations
from user.dashboard import render_user_dashboard


LOGGER = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI Market Analytics Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


@st.cache_resource
def get_supabase() -> Client:
    """Create the server-side Supabase client from protected configuration."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


@st.cache_resource
def _apply_safe_startup_migrations() -> bool:
    """Apply idempotent DB migrations for the website/admin process."""
    try:
        apply_pending_migrations()
    except Exception:
        LOGGER.exception("Website startup migrations failed.")
        return False
    return True


def _show_login() -> None:
    st.session_state.public_view = "login"
    st.rerun()


def _show_home() -> None:
    st.session_state.public_view = "home"
    st.query_params.clear()
    st.rerun()


def render_sidebar() -> None:
    """Render common authenticated navigation and account controls."""
    settings = get_settings()
    st.sidebar.markdown(f"### {settings.brand_name}")
    st.sidebar.write(get_current_user_email() or "Authenticated user")
    st.sidebar.caption(f"Role: {get_current_role()}")
    if get_current_role() == ROLE_USER:
        st.sidebar.caption(f"Payment: {get_payment_status()}")
    st.sidebar.warning(
        "Trading involves risk. Analysis and signals never guarantee returns."
    )
    if st.sidebar.button("Sign Out", use_container_width=True):
        logout_user()
        st.session_state.public_view = "home"
        st.rerun()


def _render_noindex_marker() -> None:
    """Ask crawlers not to index pre-launch/private migration deployments."""
    st.markdown(
        """
        <meta name="robots" content="noindex,nofollow,noarchive">
        <meta name="googlebot" content="noindex,nofollow,noarchive">
        """,
        unsafe_allow_html=True,
    )


def run() -> None:
    """Initialize dependencies and route public, user, and admin experiences."""
    try:
        _apply_safe_startup_migrations()
        supabase = get_supabase()
        settings = get_settings()
        initialize_session()
    except ConfigurationError as exc:
        LOGGER.error("Application configuration is incomplete: %s", exc)
        st.error("Application configuration is incomplete.")
        st.stop()
    except Exception:
        LOGGER.exception("Application initialization failed.")
        st.error("The application is temporarily unavailable.")
        st.stop()

    if getattr(settings, "block_search_indexing", False):
        _render_noindex_marker()

    if not is_authenticated():
        action = str(st.query_params.get("action", ""))
        if action in {"verify", "reset-password"}:
            login_page()
            return
        if "public_view" not in st.session_state:
            st.session_state.public_view = "home"
        if st.session_state.public_view == "login":
            if st.button("← Back to Website"):
                _show_home()
            login_page()
        else:
            render_landing_page(supabase, _show_login)
        return

    render_sidebar()
    role = get_current_role()
    if role == ROLE_ADMIN:
        render_admin_dashboard(supabase)
        return
    elif role == ROLE_USER:
        render_user_dashboard(supabase)
        return
    else:
        LOGGER.warning("Rejected unsupported session role: %s", role)
        logout_user()
        st.error("Your session is invalid. Please sign in again.")


if __name__ == "__main__":
    run()
