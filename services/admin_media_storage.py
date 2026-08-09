"""Isolated media storage adapter with decoded-image validation."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import re
from typing import Any, Protocol
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", {".jpg", ".jpeg"}, ".jpg"),
    "PNG": ("image/png", {".png"}, ".png"),
    "WEBP": ("image/webp", {".webp"}, ".webp"),
    "GIF": ("image/gif", {".gif"}, ".gif"),
}
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class MediaValidationError(ValueError):
    """Upload is not a safe supported image."""


@dataclass(frozen=True)
class ValidatedImage:
    data: bytes
    original_filename: str
    safe_stem: str
    extension: str
    mime_type: str
    width: int
    height: int


@dataclass(frozen=True)
class StoredMedia:
    provider: str
    bucket: str
    storage_path: str
    thumbnail_path: str
    public_url: str
    thumbnail_url: str
    stored_filename: str


class MediaStorage(Protocol):
    def store(self, image: ValidatedImage) -> StoredMedia: ...
    def read(self, path: str) -> bytes: ...
    def delete(self, *paths: str) -> None: ...


def validate_image_upload(filename: str, claimed_mime: str, data: bytes) -> ValidatedImage:
    raw_name = str(filename or "")
    if not raw_name or Path(raw_name).name != raw_name or "/" in raw_name or "\\" in raw_name:
        raise MediaValidationError("Unsafe filename.")
    if len(data) == 0:
        raise MediaValidationError("The uploaded image is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise MediaValidationError("Image exceeds the 8 MB upload limit.")
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(BytesIO(data)) as probe:
            detected_format = str(probe.format or "").upper()
            probe.verify()
        with Image.open(BytesIO(data)) as decoded:
            width, height = decoded.size
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise MediaValidationError("File content is not a valid supported image.") from exc
    details = ALLOWED_FORMATS.get(detected_format)
    if not details:
        raise MediaValidationError("Unsupported image type.")
    detected_mime, valid_extensions, canonical_extension = details
    supplied_extension = Path(raw_name).suffix.lower()
    if supplied_extension not in valid_extensions:
        raise MediaValidationError("Filename extension does not match image content.")
    if str(claimed_mime or "").lower() != detected_mime:
        raise MediaValidationError("Declared MIME type does not match image content.")
    safe_stem = _SAFE_NAME.sub("-", Path(raw_name).stem).strip("-._")[:80] or "image"
    return ValidatedImage(
        data=data, original_filename=raw_name, safe_stem=safe_stem,
        extension=canonical_extension, mime_type=detected_mime,
        width=int(width), height=int(height),
    )


class LocalMediaStorage:
    """Local/staging adapter; never reads production storage credentials."""

    def __init__(self, root: Path | None = None, public_base_url: str | None = None):
        self.root = (root or Path(os.getenv("ADMIN_MEDIA_LOCAL_ROOT", "/tmp/xauusd-admin-media"))).resolve()
        self.public_base_url = (public_base_url or os.getenv(
            "ADMIN_MEDIA_PUBLIC_BASE_URL", "http://127.0.0.1:8000/media-local"
        )).rstrip("/")
        self.bucket = "admin-media-local"

    def store(self, image: ValidatedImage) -> StoredMedia:
        unique = uuid4().hex
        stored_filename = f"{image.safe_stem}-{unique}{image.extension}"
        relative = Path("uploads") / stored_filename
        thumb_relative = Path("thumbnails") / f"{image.safe_stem}-{unique}.webp"
        original_target = self._target(relative)
        thumbnail_target = self._target(thumb_relative)
        original_target.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_target.parent.mkdir(parents=True, exist_ok=True)
        original_temp = original_target.with_suffix(original_target.suffix + ".part")
        thumbnail_temp = thumbnail_target.with_suffix(thumbnail_target.suffix + ".part")
        try:
            original_temp.write_bytes(image.data)
            with Image.open(BytesIO(image.data)) as decoded:
                frame = decoded.convert("RGB")
                frame.thumbnail((480, 480), Image.Resampling.LANCZOS)
                canvas = ImageOps.exif_transpose(frame)
                canvas.save(thumbnail_temp, "WEBP", quality=78, method=6)
            original_temp.replace(original_target)
            thumbnail_temp.replace(thumbnail_target)
        except Exception:
            for target in (original_temp, thumbnail_temp, original_target, thumbnail_target):
                target.unlink(missing_ok=True)
            raise
        storage_path = relative.as_posix()
        thumbnail_path = thumb_relative.as_posix()
        return StoredMedia(
            provider="LOCAL", bucket=self.bucket, storage_path=storage_path,
            thumbnail_path=thumbnail_path,
            public_url=f"{self.public_base_url}/{storage_path}",
            thumbnail_url=f"{self.public_base_url}/{thumbnail_path}",
            stored_filename=stored_filename,
        )

    def delete(self, *paths: str) -> None:
        for path in paths:
            if path:
                self._target(Path(path)).unlink(missing_ok=True)

    def read(self, path: str) -> bytes:
        return self._target(Path(path)).read_bytes()

    def _target(self, relative: Path) -> Path:
        if relative.is_absolute() or ".." in relative.parts:
            raise MediaValidationError("Unsafe storage path.")
        target = (self.root / relative).resolve()
        if self.root not in target.parents:
            raise MediaValidationError("Unsafe storage path.")
        return target


class SupabaseMediaStorage:
    """Durable production adapter backed by an existing public Storage bucket."""

    def __init__(
        self,
        *,
        url: str | None = None,
        key: str | None = None,
        bucket: str | None = None,
        prefix: str | None = None,
        client: Any | None = None,
    ):
        self.bucket = (bucket or os.getenv(
            "ADMIN_MEDIA_SUPABASE_BUCKET", "profit-screenshots"
        )).strip()
        self.prefix = (prefix or os.getenv(
            "ADMIN_MEDIA_SUPABASE_PREFIX", "admin-media"
        )).strip(" /")
        if not self.bucket or not self.prefix:
            raise RuntimeError("Durable media storage is not configured.")

        if client is None:
            storage_url = (url or os.getenv("SUPABASE_URL", "")).strip()
            storage_key = (key or os.getenv("SUPABASE_KEY", "")).strip()
            if not storage_url or not storage_key:
                raise RuntimeError("Durable media storage is not configured.")
            from supabase import create_client

            client = create_client(storage_url, storage_key)
        self._client = client

    def store(self, image: ValidatedImage) -> StoredMedia:
        unique = uuid4().hex
        stored_filename = f"{image.safe_stem}-{unique}{image.extension}"
        storage_path = f"{self.prefix}/uploads/{stored_filename}"
        thumbnail_path = f"{self.prefix}/thumbnails/{image.safe_stem}-{unique}.webp"
        thumbnail_data = _thumbnail_bytes(image.data)
        uploaded: list[str] = []
        bucket = self._client.storage.from_(self.bucket)
        try:
            bucket.upload(
                storage_path,
                image.data,
                {"content-type": image.mime_type, "upsert": "false"},
            )
            uploaded.append(storage_path)
            bucket.upload(
                thumbnail_path,
                thumbnail_data,
                {"content-type": "image/webp", "upsert": "false"},
            )
            uploaded.append(thumbnail_path)
        except Exception:
            if uploaded:
                try:
                    bucket.remove(uploaded)
                except Exception:
                    pass
            raise

        return StoredMedia(
            provider="SUPABASE",
            bucket=self.bucket,
            storage_path=storage_path,
            thumbnail_path=thumbnail_path,
            public_url=str(bucket.get_public_url(storage_path)),
            thumbnail_url=str(bucket.get_public_url(thumbnail_path)),
            stored_filename=stored_filename,
        )

    def delete(self, *paths: str) -> None:
        safe_paths = [self._safe_path(path) for path in paths if path]
        if safe_paths:
            self._client.storage.from_(self.bucket).remove(safe_paths)

    def read(self, path: str) -> bytes:
        result = self._client.storage.from_(self.bucket).download(
            self._safe_path(path)
        )
        return bytes(result)

    def _safe_path(self, path: str) -> str:
        normalized = str(path or "").strip("/")
        if not normalized or ".." in Path(normalized).parts:
            raise MediaValidationError("Unsafe storage path.")
        if normalized != self.prefix and not normalized.startswith(
            f"{self.prefix}/"
        ):
            raise MediaValidationError("Unsafe storage path.")
        return normalized


def _thumbnail_bytes(data: bytes) -> bytes:
    output = BytesIO()
    with Image.open(BytesIO(data)) as decoded:
        frame = ImageOps.exif_transpose(decoded).convert("RGB")
        frame.thumbnail((480, 480), Image.Resampling.LANCZOS)
        frame.save(output, "WEBP", quality=78, method=6)
    return output.getvalue()


def get_media_storage(provider: str | None = None) -> MediaStorage:
    requested = str(provider or os.getenv("ADMIN_MEDIA_STORAGE_PROVIDER", "")).upper()
    if requested == "LOCAL" or (not requested and os.getenv("ADMIN_MEDIA_LOCAL_ROOT")):
        return LocalMediaStorage()
    if requested == "SUPABASE" or (
        not requested and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")
    ):
        return SupabaseMediaStorage()
    return LocalMediaStorage()
