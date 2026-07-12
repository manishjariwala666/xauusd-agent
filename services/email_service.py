"""Transactional authentication email delivery."""

from __future__ import annotations

from email.message import EmailMessage
import logging
import smtplib
import ssl
from urllib.parse import urlencode

from config import Settings, get_settings


LOGGER = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when a transactional email cannot be delivered."""


def send_verification_email(recipient: str, token: str) -> None:
    """Send a single-use account verification link."""
    settings = get_settings()
    link = _build_link(settings, "verify", token)
    _send(
        settings,
        recipient,
        "Verify your AI Market Analytics Pro account",
        (
            "Welcome to AI Market Analytics Pro.\n\n"
            f"Verify your email using this secure link:\n{link}\n\n"
            "This link expires in 24 hours. If you did not create this "
            "account, you can ignore this email."
        ),
    )


def is_email_delivery_configured() -> bool:
    """Return whether transactional SMTP delivery has required settings."""
    settings = get_settings()
    return all(
        (
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.email_from,
            settings.app_base_url or settings.public_website_url,
        )
    )


def send_password_reset_email(recipient: str, token: str) -> None:
    """Send a single-use password reset link."""
    settings = get_settings()
    link = _build_link(settings, "reset-password", token)
    _send(
        settings,
        recipient,
        "Reset your AI Market Analytics Pro password",
        (
            "A password reset was requested for your account.\n\n"
            f"Set a new password using this secure link:\n{link}\n\n"
            "This link expires in 30 minutes. If you did not request this, "
            "you can safely ignore this email."
        ),
    )


def _build_link(settings: Settings, action: str, token: str) -> str:
    base_url = settings.app_base_url or settings.public_website_url
    if not base_url:
        raise EmailDeliveryError("APP_BASE_URL is not configured.")
    query = urlencode({"action": action, "token": token})
    return f"{base_url.rstrip('/')}?{query}"


def _send(
    settings: Settings,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    required = (
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.email_from,
    )
    if not all(required):
        raise EmailDeliveryError("SMTP settings are incomplete.")

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=20,
        ) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        LOGGER.exception("Authentication email delivery failed.")
        raise EmailDeliveryError("Email could not be delivered.") from exc
