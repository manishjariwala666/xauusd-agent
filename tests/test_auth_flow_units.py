import inspect

from core import auth
from pages import login
from services import email_service


def test_registration_saves_whatsapp_as_phone_when_column_exists() -> None:
    source = inspect.getsource(auth.register_user)

    assert '_table_columns(session, "users")' in source
    assert 'user_columns.get("phone")' in source
    assert '"phone": normalized_whatsapp' in source


def test_resend_verification_flow_exists_and_is_email_config_safe() -> None:
    source = inspect.getsource(auth.resend_verification_email)

    assert "verification_token_hash" in source
    assert "verification_expires_at" in source
    assert "is_email_delivery_configured()" in source
    assert "send_verification_email" in source


def test_password_reset_requires_email_delivery_configuration() -> None:
    source = inspect.getsource(auth.request_password_reset)

    assert "is_email_delivery_configured()" in source
    assert "Email delivery is not configured yet" in source


def test_login_ui_has_gmail_resend_and_forgot_password_controls() -> None:
    page_source = inspect.getsource(login.login_page)
    google_source = inspect.getsource(login._render_google_login)
    resend_source = inspect.getsource(login._render_resend_verification)

    assert "Continue with Gmail" in google_source
    assert "google_oauth_login_url" in google_source
    assert "disabled=True" not in google_source
    assert "Resend Verification" in page_source
    assert "Forgot Password" in page_source
    assert "resend_verification_email" in resend_source
    assert "_render_site_footer()" in page_source


def test_email_links_can_use_public_website_url_fallback() -> None:
    link_source = inspect.getsource(email_service._build_link)
    config_source = inspect.getsource(email_service.is_email_delivery_configured)

    assert "settings.app_base_url or settings.public_website_url" in link_source
    assert "settings.app_base_url or settings.public_website_url" in config_source
