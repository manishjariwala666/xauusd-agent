from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from services.admin_media_storage import (
    MAX_UPLOAD_BYTES, LocalMediaStorage, MediaValidationError,
    validate_image_upload,
)


def image_bytes(format_name: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), (32, 96, 180)).save(output, format_name)
    return output.getvalue()


def test_decoded_image_validation_and_local_thumbnail_storage(tmp_path: Path) -> None:
    validated = validate_image_upload("market-chart.png", "image/png", image_bytes())
    storage = LocalMediaStorage(tmp_path, "http://local.invalid/media")
    first = storage.store(validated)
    second = storage.store(validated)
    assert first.stored_filename != second.stored_filename
    assert (tmp_path / first.storage_path).read_bytes() == validated.data
    assert (tmp_path / first.thumbnail_path).stat().st_size > 0
    assert first.thumbnail_url.endswith(".webp")
    storage.delete(first.storage_path, first.thumbnail_path)
    assert not (tmp_path / first.storage_path).exists()


@pytest.mark.parametrize(("filename", "mime", "data"), [
    ("fake.jpg", "image/jpeg", image_bytes("PNG")),
    ("payload.png", "application/x-php", image_bytes("PNG")),
    ("../escape.png", "image/png", image_bytes("PNG")),
    ("script.php", "image/png", b"<?php echo 'unsafe'; ?>"),
])
def test_unsafe_or_mismatched_uploads_are_rejected(filename: str, mime: str, data: bytes) -> None:
    with pytest.raises(MediaValidationError):
        validate_image_upload(filename, mime, data)


def test_oversized_upload_is_rejected_before_decode() -> None:
    with pytest.raises(MediaValidationError, match="8 MB"):
        validate_image_upload("large.png", "image/png", b"0" * (MAX_UPLOAD_BYTES + 1))


def test_storage_rejects_path_traversal_even_after_validation(tmp_path: Path) -> None:
    storage = LocalMediaStorage(tmp_path, "http://local.invalid/media")
    with pytest.raises(MediaValidationError):
        storage.delete("../outside.png")
