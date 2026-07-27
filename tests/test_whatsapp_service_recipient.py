from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import services.whatsapp_service as whatsapp_module


def _settings():
    return SimpleNamespace(
        green_api_instance_id="1234567890",
        green_api_token="secret-token",
        green_api_chat_id="919999999999@c.us",
        whatsapp_access_token="",
        whatsapp_phone_number_id="",
    )


def test_green_api_uses_requested_recipient(monkeypatch):
    monkeypatch.setattr(whatsapp_module, "get_settings", _settings)

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"idMessage": "test-message-id"}

    post = Mock(return_value=response)
    monkeypatch.setattr(whatsapp_module.requests, "post", post)

    service = whatsapp_module.WhatsAppService()
    message_id = service.send_text(
        "919328669308",
        "VenusRealm controlled test",
    )

    assert message_id == "test-message-id"
    assert post.call_args.kwargs["json"] == {
        "chatId": "919328669308@c.us",
        "message": "VenusRealm controlled test",
    }


def test_green_api_rejects_invalid_recipient(monkeypatch):
    monkeypatch.setattr(whatsapp_module, "get_settings", _settings)

    service = whatsapp_module.WhatsAppService()

    with pytest.raises(
        ValueError,
        match="recipient must contain digits only",
    ):
        service.send_text("customer-name", "Test")
