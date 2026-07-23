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

        self._green_api_instance_id = settings.green_api_instance_id
        self._green_api_token = settings.green_api_token
        self._green_api_chat_id = settings.green_api_chat_id

        self._use_green_api = bool(
            self._green_api_instance_id
            and self._green_api_token
            and self._green_api_chat_id
        )

        if self._use_green_api:
            self._token = ""
            self._endpoint = (
                "https://api.green-api.com/"
                f"waInstance{self._green_api_instance_id}/"
                f"sendMessage/{self._green_api_token}"
            )
            return

        if not settings.whatsapp_access_token:
            raise ConfigurationError(
                "WHATSAPP_ACCESS_TOKEN is not configured."
            )
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
        """Send one WhatsApp text message using Green API or Meta Cloud API."""
        if self._use_green_api:
            return self._send(
                {
                    "chatId": self._green_api_chat_id,
                    "message": message[:4096],
                }
            )

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
            headers = {"Content-Type": "application/json"}
            if not self._use_green_api:
                headers["Authorization"] = f"Bearer {self._token}"

            response = requests.post(
                self._endpoint,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            response_payload = response.json()
            if self._use_green_api:
                message_id = response_payload.get("idMessage")
            else:
                message_id = response_payload["messages"][0]["id"]

            if not message_id:
                raise RuntimeError(
                    "WhatsApp provider returned no message id."
                )
        except Exception:
            logger.exception("WhatsApp Cloud API delivery failed")
            raise
        logger.info("WhatsApp message delivered: id={}", message_id)
        return str(message_id)
