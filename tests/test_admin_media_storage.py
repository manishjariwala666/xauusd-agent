from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from services.admin_media_storage import (
    MAX_UPLOAD_BYTES, LocalMediaStorage, MediaValidationError,
    SupabaseMediaStorage,
    validate_image_upload,
)
from services import admin_media_service


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
    assert storage.read(first.storage_path) == validated.data
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
    with pytest.raises(MediaValidationError):
        storage.read("../outside.png")


def test_media_service_reads_real_file_and_falls_back_from_missing_thumbnail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalMediaStorage(tmp_path, "http://local.invalid/media")
    original = image_bytes()
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "one.png").write_bytes(original)
    monkeypatch.setattr(admin_media_service, "get_admin_media", lambda _media_id: {
        "id": 1,
        "storage_provider": "LOCAL",
        "storage_path": "uploads/one.png",
        "thumbnail_path": "thumbnails/missing.webp",
        "mime_type": "image/png",
        "deleted_at": None,
    })

    data, mime_type = admin_media_service.read_admin_media_file(
        media_id=1, variant="thumbnail", storage=storage,
    )

    assert data == original
    assert mime_type == "image/png"


class _FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(self, path: str, data: bytes, _options: dict[str, str]) -> None:
        self.objects[path] = bytes(data)

    def download(self, path: str) -> bytes:
        return self.objects[path]

    def remove(self, paths: list[str]) -> None:
        for path in paths:
            self.objects.pop(path, None)

    def get_public_url(self, path: str) -> str:
        return f"https://cdn.example.invalid/{path}"


class _FakeStorage:
    def __init__(self, bucket: _FakeBucket) -> None:
        self.bucket = bucket

    def from_(self, _name: str) -> _FakeBucket:
        return self.bucket


class _FakeSupabase:
    def __init__(self) -> None:
        self.bucket = _FakeBucket()
        self.storage = _FakeStorage(self.bucket)


def test_supabase_storage_keeps_original_and_thumbnail_durable() -> None:
    client = _FakeSupabase()
    storage = SupabaseMediaStorage(
        bucket="media-test", prefix="admin-media", client=client,
    )
    validated = validate_image_upload("chart.png", "image/png", image_bytes())

    stored = storage.store(validated)

    assert stored.provider == "SUPABASE"
    assert stored.storage_path.startswith("admin-media/uploads/")
    assert stored.thumbnail_path.startswith("admin-media/thumbnails/")
    assert stored.public_url.startswith("https://cdn.example.invalid/")
    assert storage.read(stored.storage_path) == validated.data
    assert storage.read(stored.thumbnail_path)
    storage.delete(stored.storage_path, stored.thumbnail_path)
    assert client.bucket.objects == {}


def test_supabase_storage_rejects_paths_outside_admin_prefix() -> None:
    storage = SupabaseMediaStorage(
        bucket="media-test", prefix="admin-media", client=_FakeSupabase(),
    )
    with pytest.raises(MediaValidationError):
        storage.read("other-feature/private.png")
