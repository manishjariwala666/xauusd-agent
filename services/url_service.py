"""Public URL helpers for custom-domain and Railway fallback safety."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote


RAILWAY_API_FALLBACK_URL = "https://xauusd-agent-api-production.up.railway.app"
DEFAULT_PUBLIC_WEBSITE_URL = "https://venusrealm.net"


def normalize_base_url(value: str | None) -> str:
    """Return a clean HTTPS base URL without a trailing slash."""
    return str(value or "").strip().rstrip("/")


def public_api_base_url(settings: Any | None = None) -> str:
    """Resolve the public API base URL while keeping the Railway URL usable."""
    return normalize_base_url(
        os.getenv("PUBLIC_API_URL")
        or getattr(settings, "public_api_url", "")
        or getattr(settings, "backend_base_url", "")
        or os.getenv("BACKEND_BASE_URL")
        or RAILWAY_API_FALLBACK_URL
    )


def public_website_base_url(settings: Any | None = None) -> str:
    """Resolve the public website base URL for canonical/blog/admin links."""
    return normalize_base_url(
        os.getenv("PUBLIC_WEBSITE_URL")
        or os.getenv("PUBLIC_SITE_URL")
        or os.getenv("STREAMLIT_PUBLIC_URL")
        or getattr(settings, "public_website_url", "")
        or getattr(settings, "app_base_url", "")
        or os.getenv("APP_BASE_URL")
        or DEFAULT_PUBLIC_WEBSITE_URL
    )


def canonical_url(path: str = "", *, base_url: str | None = None) -> str:
    """Build an absolute public URL from a base URL and route path."""
    base = normalize_base_url(base_url) or public_website_base_url()
    clean_path = "/" + str(path or "").strip("/")
    return base + ("" if clean_path == "/" else clean_path)


def public_content_url(
    item: dict[str, Any],
    *,
    base_url: str | None = None,
) -> str:
    """Build the public absolute route for one content item."""
    slug = str(
        item.get("seo_slug")
        or item.get("slug")
        or item.get("id")
        or ""
    ).strip()
    if not slug:
        return ""

    content_type = str(item.get("content_type") or "").strip().upper()
    encoded_slug = quote(slug)
    if content_type == "ANNOUNCEMENT":
        return canonical_url(f"/announcements/{encoded_slug}", base_url=base_url)
    if content_type == "PAGE":
        return canonical_url(f"/page/{encoded_slug}", base_url=base_url)
    if content_type == "SIGNAL_POST":
        return canonical_url(f"/signals/{encoded_slug}", base_url=base_url)
    return canonical_url(f"/blog/{encoded_slug}", base_url=base_url)
