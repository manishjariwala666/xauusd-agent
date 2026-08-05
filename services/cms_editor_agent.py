"""Draft-only CMS V2 conversion agent for VenusRealm."""

from __future__ import annotations

from html import escape
import json
import re
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from services.content_service import save_content


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("CMS Editor Agent requires a valid title or slug.")
    return slug[:160]


def _block_id(block_type: str) -> str:
    return f"cms-agent-{block_type}-{uuid4().hex[:12]}"


def markdown_to_cms_blocks(markdown: str) -> list[dict[str, Any]]:
    """Convert safe Markdown headings and paragraphs into CMS V2 blocks."""
    source = str(markdown or "").replace("\r\n", "\n").strip()
    blocks: list[dict[str, Any]] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return

        text = " ".join(
            line.strip()
            for line in paragraph_lines
            if line.strip()
        ).strip()
        paragraph_lines.clear()

        if not text:
            return

        blocks.append({
            "id": _block_id("paragraph"),
            "type": "paragraph",
            "html": f"<p>{escape(text)}</p>",
        })

    for raw_line in source.split("\n"):
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            blocks.append({
                "id": _block_id("heading"),
                "type": "heading",
                "level": level,
                "text": heading_text,
            })
            continue

        paragraph_lines.append(line)

    flush_paragraph()

    if not blocks:
        blocks.append({
            "id": _block_id("paragraph"),
            "type": "paragraph",
            "html": "<p></p>",
        })

    return blocks


def build_cms_v2_document(payload: dict[str, Any]) -> dict[str, Any]:
    """Build one complete draft-only CmsDocument."""
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("CMS Editor Agent requires title.")

    slug = _slugify(str(payload.get("slug") or title))
    excerpt = str(payload.get("excerpt") or "").strip()[:1000]
    markdown = str(
        payload.get("body_markdown")
        or payload.get("body")
        or ""
    ).strip()

    category_id_raw = payload.get("category_id")
    category_id = (
        int(category_id_raw)
        if category_id_raw not in (None, "")
        else None
    )

    featured_media_raw = payload.get("featured_media_id")
    featured_media_id = (
        int(featured_media_raw)
        if featured_media_raw not in (None, "")
        else None
    )

    schema_jsonld = payload.get("schema_jsonld")
    if not isinstance(schema_jsonld, dict):
        schema_jsonld = None

    return {
        "id": None,
        "title": title[:240],
        "slug": slug,
        "excerpt": excerpt,
        "status": "draft",
        "categoryId": category_id,
        "tags": [
            str(tag).strip()
            for tag in payload.get("tags", [])
            if str(tag).strip()
        ][:30],
        "featuredMediaId": featured_media_id,
        "blocks": markdown_to_cms_blocks(markdown),
        "seo": {
            "metaTitle": str(
                payload.get("meta_title") or title
            ).strip()[:255],
            "metaDescription": str(
                payload.get("meta_description") or excerpt
            ).strip()[:320],
            "focusKeyword": str(
                payload.get("focus_keyword") or ""
            ).strip()[:160],
            "canonicalUrl": "",
            "robotsIndex": False,
            "robotsFollow": False,
            "schemaJsonLd": schema_jsonld,
        },
        "socialSharing": {
            "enabled": False,
            "platforms": [
                "whatsapp",
                "telegram",
                "facebook",
                "x",
                "linkedin",
                "copy",
            ],
        },
        "relatedPosts": {
            "enabled": False,
            "heading": "Related Posts",
            "items": [],
        },
        "toc": {
            "enabled": True,
            "title": "Table of Contents",
            "maxDepth": 3,
        },
        "scheduledAt": None,
        "publishedAt": None,
        "createdAt": None,
        "updatedAt": None,
    }


def _render_block(block: dict[str, Any]) -> str:
    block_type = block.get("type")

    if block_type == "heading":
        level = int(block.get("level") or 2)
        level = min(6, max(1, level))
        return (
            f"<h{level}>"
            f"{escape(str(block.get('text') or ''))}"
            f"</h{level}>"
        )

    if block_type == "paragraph":
        return (
            '<div data-cms-block="paragraph">'
            f"{block.get('html') or '<p></p>'}"
            "</div>"
        )

    return ""


def serialize_cms_v2_document(
    document: dict[str, Any],
) -> str:
    """Serialize using the same marker expected by Studio V2."""
    compact_json = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # Matches JavaScript encodeURIComponent safe characters.
    encoded = quote(
        compact_json,
        safe="-_.!~*'()",
        encoding="utf-8",
        errors="strict",
    )

    rendered = "\n".join(
        rendered_block
        for rendered_block in (
            _render_block(block)
            for block in document["blocks"]
        )
        if rendered_block
    )

    return (
        f"<!--venusrealm-cms-v2:{encoded}-->\n"
        f"{rendered}"
    )


def run_cms_editor_agent(payload: dict[str, Any]) -> str:
    """Create one Studio V2-compatible draft; never publish or schedule."""
    if payload.get("publish") is True:
        raise PermissionError(
            "CMS Editor Agent cannot publish content."
        )

    if payload.get("scheduled_at"):
        raise PermissionError(
            "CMS Editor Agent cannot schedule content."
        )

    document = build_cms_v2_document(payload)
    structured_body = serialize_cms_v2_document(document)

    content_id = save_content(
        content_type="AI_BLOG",
        title=document["title"],
        slug=document["slug"],
        excerpt=document["excerpt"],
        body=structured_body,
        category_id=document["categoryId"],
        subcategory=str(
            payload.get("subcategory") or ""
        ).strip(),
        image_url="",
        external_url="",
        is_public=True,
        is_published=False,
        status="draft",
        created_by=(
            int(payload["created_by"])
            if payload.get("created_by") not in (None, "")
            else None
        ),
        meta_title=document["seo"]["metaTitle"],
        meta_description=document["seo"]["metaDescription"],
        focus_keyword=document["seo"]["focusKeyword"],
        faq=payload.get("faq") or [],
        schema_jsonld=document["seo"]["schemaJsonLd"] or {},
        internal_links=payload.get("internal_links") or [],
        open_graph={},
        twitter_card={},
        image_prompt=str(
            payload.get("image_prompt") or ""
        ).strip()[:2000],
    )

    return (
        f"CMS V2 draft #{content_id} created. "
        "Master AI review and owner approval are required before publish."
    )
