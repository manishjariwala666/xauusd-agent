"""Offline webhook parsing tests."""

from backend import _telegram_media, _whatsapp_content


def test_telegram_photo_metadata() -> None:
    assert _telegram_media(
        {"photo": [{"file_id": "small"}, {"file_id": "large"}]}
    ) == {"type": "photo", "file_id": "large"}


def test_whatsapp_text_content() -> None:
    body, media = _whatsapp_content(
        {"type": "text", "text": {"body": "hello"}}
    )
    assert body == "hello"
    assert media == {}
