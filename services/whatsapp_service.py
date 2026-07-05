"""WhatsApp Business Cloud API delivery with durable error reporting."""

from __future__ import annotations

from typing import Any

from loguru import logger
import requests

from config import ConfigurationError, get_settings


class WhatsAppService:
    """Send text and supported media via the official Meta Cloud API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.whatsapp_access_token:
            raise ConfigurationError("WHATSAPP_ACCESS_TOKEN is not configured.")
        if not settings.whatsapp_phone_number_id:
            raise ConfigurationError(
                "WHATSAPP_PHONE_NUMBER_ID is not configured."
            )
        self._token = settings.whatsapp_access_token
        self._endpoint = (
            "https://graph.facebook.com/v23.0/"
            f"{settings.whatsapp_phone_number_id}/messages"
        )

    def send_text(self, recipient: str, message: str) -> str:
        """Send one WhatsApp text message and return Meta message id."""
        return self._send(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": message[:4096]},
            }
        )

    def send_media(
        self,
        recipient: str,
        media_type: str,
        media_url: str,
        caption: str = "",
    ) -> str:
        """Send image, video, audio, or document by HTTPS URL."""
        if media_type not in {"image", "video", "audio", "document"}:
            raise ValueError("Unsupported WhatsApp media type.")
        media: dict[str, Any] = {"link": media_url}
        if caption and media_type in {"image", "video", "document"}:
            media["caption"] = caption[:1024]
        return self._send(
            {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": media_type,
                media_type: media,
            }
        )

    def _send(self, payload: dict[str, Any]) -> str:
        try:
            response = requests.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            message_id = response.json()["messages"][0]["id"]
        except Exception:
            logger.exception("WhatsApp Cloud API delivery failed")
            raise
        logger.info("WhatsApp message delivered: id={}", message_id)
        return str(message_id)
