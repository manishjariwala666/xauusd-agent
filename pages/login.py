"""Public login, account creation, and account-recovery interface."""

from __future__ import annotations

import streamlit as st

from core.auth import (
    AuthResult,
    authenticate_credentials,
    register_user,
    request_password_reset,
    reset_password,
    verify_email,
)


def login_page() -> None:
    """Render public authentication UI without exposing premium resources."""
    st.markdown(
        "<h1 style='text-align:center;margin-top:28px'>"
        "AI Market Analytics Pro</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#94a3b8'>"
        "Secure market intelligence for disciplined traders</p>",
        unsafe_allow_html=True,
    )

    action = str(st.query_params.get("action", ""))
    token = str(st.query_params.get("token", ""))
    if action == "verify":
        _render_verification(token)
        return
    if action == "reset-password":
        _render_password_reset(token)
        return

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        login_tab, create_tab, recovery_tab = st.tabs(
            ["Sign In", "Create New Account", "Forgot Password"]
        )
        with login_tab:
            _render_sign_in()
        with create_tab:
            _render_registration()
        with recovery_tab:
            _render_recovery()


def _render_sign_in() -> None:
    with st.form("login_form"):
        email = st.text_input("Email address", autocomplete="email")
        password = st.text_input(
            "Password",
            type="password",
            autocomplete="current-password",
        )
        submitted = st.form_submit_button(
            "Sign In",
            use_container_width=True,
            type="primary",
        )
    if not submitted:
        return
    result = authenticate_credentials(email, password)
    if result.success:
        st.rerun()
    _display_result(result)


def _render_registration() -> None:
    st.caption(
        "Payment verification is manual. Premium links remain locked until "
        "email verification and admin approval are complete."
    )
    with st.form("registration_form", clear_on_submit=False):
        email = st.text_input(
            "Email address",
            key="register_email",
            autocomplete="email",
        )
        password = st.text_input(
            "Create password",
            type="password",
            key="register_password",
            help="Minimum 12 characters with uppercase, lowercase, number and symbol.",
            autocomplete="new-password",
        )
        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            key="register_confirm_password",
            autocomplete="new-password",
        )
        whatsapp = st.text_input(
            "WhatsApp number with country code",
            key="register_whatsapp",
        )
        accepted = st.checkbox(
            "I understand that market analysis is informational and returns "
            "are not guaranteed."
        )
        submitted = st.form_submit_button(
            "Create Account",
            use_container_width=True,
            type="primary",
        )

    if not submitted:
        return
    if not accepted:
        st.warning("Please accept the risk disclosure to continue.")
        return
    _display_result(
        register_user(
            email,
            password,
            confirm_password,
            whatsapp,
            "",
        )
    )


def _render_recovery() -> None:
    with st.form("recovery_form"):
        email = st.text_input(
            "Registered email address",
            key="recovery_email",
            autocomplete="email",
        )
        submitted = st.form_submit_button(
            "Send Reset Link",
            use_container_width=True,
        )
    if submitted:
        _display_result(request_password_reset(email))


def _render_verification(token: str) -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.subheader("Email Verification")
        _display_result(verify_email(token))
        if st.button("Continue to Sign In", use_container_width=True):
            st.query_params.clear()
            st.rerun()


def _render_password_reset(token: str) -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.subheader("Set New Password")
        with st.form("password_reset_form"):
            password = st.text_input(
                "New password",
                type="password",
                autocomplete="new-password",
            )
            confirm_password = st.text_input(
                "Confirm new password",
                type="password",
                autocomplete="new-password",
            )
            submitted = st.form_submit_button(
                "Update Password",
                use_container_width=True,
                type="primary",
            )
        if submitted:
            result = reset_password(token, password, confirm_password)
            _display_result(result)
            if result.success:
                st.query_params.clear()


def _display_result(result: AuthResult) -> None:
    display_method = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
    }.get(result.level, st.info)
    display_method(result.message)
