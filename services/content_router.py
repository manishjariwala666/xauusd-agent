"""Public website route-to-source mapping for dynamic content pages.

This module keeps URL structure separate from rendering code.  Each public
route declares which content source it reads from, which content types are
allowed, and whether the route represents a category-backed subject page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote


BLOG_CONTENT_TYPES = ("BLOG", "AI_BLOG", "ADVISORY", "ANALYSIS", "EDUCATION")


@dataclass(frozen=True)
class ContentRouteSource:
    """Declarative public route mapping for one website section."""

    route: str
    source_kind: str
    index_renderer: str
    detail_renderer: str | None = None
    allowed_content_types: tuple[str, ...] = ()
    category_slug: str = ""
    description: str = ""

    @property
    def is_category_backed(self) -> bool:
        """Return True when the route should render a category feed."""
        return bool(self.category_slug)


ROUTE_SOURCES: dict[str, ContentRouteSource] = {
    "blog": ContentRouteSource(
        route="blog",
        source_kind="content_items",
        index_renderer="blog_index",
        detail_renderer="content_detail",
        allowed_content_types=BLOG_CONTENT_TYPES,
        description="SEO blogs, market research, advisory, and education posts.",
    ),
    "announcements": ContentRouteSource(
        route="announcements",
        source_kind="content_items",
        index_renderer="announcements_index",
        detail_renderer="announcement_detail",
        allowed_content_types=("ANNOUNCEMENT",),
        description="Public service and market announcements.",
    ),
    "signals": ContentRouteSource(
        route="signals",
        source_kind="market_signals",
        index_renderer="signals_index",
        detail_renderer="content_detail",
        allowed_content_types=("SIGNAL_POST",),
        description="Public XAUUSD signal posts and market previews.",
    ),
    "page": ContentRouteSource(
        route="page",
        source_kind="content_items",
        index_renderer="page_detail",
        detail_renderer="content_detail",
        allowed_content_types=("PAGE",),
        description="Static public website pages.",
    ),
    "category": ContentRouteSource(
        route="category",
        source_kind="content_categories",
        index_renderer="category_index",
        allowed_content_types=(),
        description="Category and subcategory content feeds.",
    ),
    "market-analysis": ContentRouteSource(
        route="market-analysis",
        source_kind="content_items",
        index_renderer="category_index",
        detail_renderer="content_detail",
        allowed_content_types=("ANALYSIS", "AI_BLOG", "BLOG"),
        category_slug="analysis-department",
        description="Technical, macro, and XAUUSD market analysis.",
    ),
    "education": ContentRouteSource(
        route="education",
        source_kind="content_items",
        index_renderer="category_index",
        detail_renderer="content_detail",
        allowed_content_types=("EDUCATION", "BLOG", "AI_BLOG"),
        category_slug="market-education",
        description="Trading concepts, risk control, and learning resources.",
    ),
    "xauusd-signals": ContentRouteSource(
        route="xauusd-signals",
        source_kind="content_items",
        index_renderer="category_index",
        detail_renderer="content_detail",
        allowed_content_types=("SIGNAL_POST", "ANALYSIS", "BLOG", "AI_BLOG"),
        category_slug="xauusd-signals",
        description="Gold signal notes, target posts, and XAUUSD research.",
    ),
}

ROUTE_ALIASES = {
    "blogs": "blog",
    "posts": "blog",
    "market": "market-analysis",
    "analysis": "market-analysis",
    "learn": "education",
    "xauusd": "xauusd-signals",
}


def route_source_for(route: str) -> ContentRouteSource | None:
    """Return the configured source mapping for a public route."""
    normalized = str(route or "").strip().lower().strip("/")
    canonical = ROUTE_ALIASES.get(normalized, normalized)
    return ROUTE_SOURCES.get(canonical)


def path_url(*parts: str) -> str:
    """Build a public path URL from safe route segments."""
    clean_parts = [
        quote(str(part).strip("/"), safe="")
        for part in parts
        if part is not None and str(part).strip("/")
    ]
    return "/" + "/".join(clean_parts)


def content_slug(item: dict[str, Any]) -> str:
    """Return the best public slug for a content row."""
    return str(
        item.get("seo_slug")
        or item.get("slug")
        or item.get("id")
        or ""
    ).strip()


def content_url_for_item(item: dict[str, Any]) -> str:
    """Return the correct public URL for one content item."""
    slug = content_slug(item)
    if not slug:
        return str(item.get("external_url") or "#")

    content_type = str(item.get("content_type") or "").upper()
    if content_type == "ANNOUNCEMENT":
        return path_url("announcements", slug)
    if content_type == "PAGE":
        return path_url("page", slug)
    if content_type == "SIGNAL_POST":
        return path_url("signals", slug)
    return path_url("blog", slug)
