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


def test_green_api_group_recipient_is_preserved(monkeypatch):
    service = whatsapp_module.WhatsAppService.__new__(whatsapp_module.WhatsAppService)
    service._use_green_api = True

    captured = {}

    def fake_send(payload):
        captured.update(payload)
        return "group-message-id"

    monkeypatch.setattr(service, "_send", fake_send)

    result = service.send_text(
        "120363000000000000-1234567890@g.us",
        "Group test",
    )

    assert result == "group-message-id"
    assert captured["chatId"] == (
        "120363000000000000-1234567890@g.us"
    )
    assert captured["message"] == "Group test"


def test_green_api_invalid_group_recipient_is_rejected():
    service = whatsapp_module.WhatsAppService.__new__(whatsapp_module.WhatsAppService)
    service._use_green_api = True

    import pytest

    with pytest.raises(
        ValueError,
        match="group recipient has an invalid format",
    ):
        service.send_text("invalid-group@g.us", "Test")
