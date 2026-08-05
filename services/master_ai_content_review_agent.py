"""Read-only content quality review for VenusRealm drafts."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote


APPROVE = "APPROVE"
NEEDS_CHANGES = "NEEDS_CHANGES"
REJECT = "REJECT"

CMS_MARKER_PATTERN = re.compile(
    r"<!--venusrealm-cms-v2:(.*?)-->",
    re.DOTALL,
)

GUARANTEE_PATTERNS = (
    r"\bguaranteed profit\b",
    r"\b100% profit\b",
    r"\brisk[- ]free profit\b",
    r"\bno loss\b",
    r"\bsure profit\b",
)

RISK_TERMS = (
    "trading involves risk",
    "trading carries risk",
    "risk disclaimer",
    "educational content only",
    "not financial advice",
)


def extract_cms_document(body: str) -> dict[str, Any] | None:
    """Decode a Studio V2 document without mutating content."""
    match = CMS_MARKER_PATTERN.search(str(body or ""))

    if not match:
        return None

    try:
        decoded = unquote(match.group(1))
        payload = json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _plain_text(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(value or "")).strip()


def _document_text(document: dict[str, Any]) -> str:
    chunks: list[str] = [
        str(document.get("title") or ""),
        str(document.get("excerpt") or ""),
    ]

    for block in document.get("blocks") or []:
        if not isinstance(block, dict):
            continue

        block_type = str(block.get("type") or "")

        if block_type == "heading":
            chunks.append(str(block.get("text") or ""))
        elif block_type in {"paragraph", "quote", "table"}:
            chunks.append(_plain_text(str(block.get("html") or "")))
        elif block_type == "youtube":
            chunks.extend([
                str(block.get("title") or ""),
                str(block.get("url") or ""),
            ])

    return " ".join(chunks).strip()


def review_cms_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic publish-readiness findings."""
    critical: list[str] = []
    warnings: list[str] = []
    passed: list[str] = []

    title = str(document.get("title") or "").strip()
    slug = str(document.get("slug") or "").strip()
    excerpt = str(document.get("excerpt") or "").strip()
    status = str(document.get("status") or "").strip().lower()
    blocks = document.get("blocks")
    seo = document.get("seo")
    featured_media_id = document.get("featuredMediaId")
    text = _document_text(document)
    normalized_text = text.casefold()

    if status != "draft":
        critical.append("Review agent accepts draft content only.")
    else:
        passed.append("Draft-only state confirmed.")

    if not title:
        critical.append("Title is missing.")
    elif len(title) > 240:
        critical.append("Title exceeds 240 characters.")
    else:
        passed.append("Title is present.")

    if not slug:
        critical.append("Slug is missing.")
    elif not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        critical.append("Slug format is invalid.")
    else:
        passed.append("Slug format is valid.")

    if not isinstance(blocks, list) or not blocks:
        critical.append("Structured content blocks are missing.")
    else:
        passed.append("Structured content blocks are present.")

    for pattern in GUARANTEE_PATTERNS:
        if re.search(pattern, normalized_text, re.IGNORECASE):
            critical.append(
                "Prohibited guaranteed-profit or risk-free claim detected."
            )
            break
    else:
        passed.append("No prohibited profit guarantee detected.")

    word_count = len(re.findall(r"\b[\w'-]+\b", text))

    if word_count < 300:
        warnings.append(
            f"Content is short for review ({word_count} words)."
        )
    else:
        passed.append(f"Content length check passed ({word_count} words).")

    if len(excerpt) < 80:
        warnings.append("Excerpt should be more descriptive.")
    else:
        passed.append("Excerpt is sufficiently descriptive.")

    if not isinstance(seo, dict):
        critical.append("SEO configuration is missing.")
        seo = {}

    meta_title = str(seo.get("metaTitle") or "").strip()
    meta_description = str(
        seo.get("metaDescription") or ""
    ).strip()
    focus_keyword = str(seo.get("focusKeyword") or "").strip()

    if not meta_title:
        warnings.append("SEO meta title is missing.")
    elif len(meta_title) > 60:
        warnings.append("SEO meta title exceeds 60 characters.")
    else:
        passed.append("SEO meta title is present.")

    if not meta_description:
        warnings.append("SEO meta description is missing.")
    elif len(meta_description) > 160:
        warnings.append("SEO meta description exceeds 160 characters.")
    else:
        passed.append("SEO meta description is present.")

    if not focus_keyword:
        warnings.append("Focus keyword is missing.")
    else:
        passed.append("Focus keyword is present.")

    if featured_media_id in (None, ""):
        warnings.append("Featured image is missing.")
    else:
        passed.append("Featured image is assigned.")

    image_blocks = [
        block
        for block in blocks or []
        if isinstance(block, dict)
        and block.get("type") == "image"
    ]

    missing_alt_count = sum(
        1
        for block in image_blocks
        if not str(block.get("alt") or "").strip()
    )

    if missing_alt_count:
        warnings.append(
            f"{missing_alt_count} inline image(s) are missing alt text."
        )
    elif image_blocks:
        passed.append("Inline image alt text check passed.")

    has_risk_disclaimer = any(
        term in normalized_text
        for term in RISK_TERMS
    )

    trading_terms_present = any(
        term in normalized_text
        for term in (
            "xauusd",
            "trading",
            "gold market",
            "forex",
            "entry",
            "stop loss",
            "take profit",
        )
    )

    if trading_terms_present and not has_risk_disclaimer:
        warnings.append(
            "Trading-related content should include a risk disclaimer."
        )
    elif trading_terms_present:
        passed.append("Trading risk disclaimer detected.")

    heading_count = sum(
        1
        for block in blocks or []
        if isinstance(block, dict)
        and block.get("type") == "heading"
    )

    if heading_count < 2:
        warnings.append("Content structure needs more headings.")
    else:
        passed.append("Heading structure is present.")

    if critical:
        decision = REJECT
    elif warnings:
        decision = NEEDS_CHANGES
    else:
        decision = APPROVE

    return {
        "status": "REVIEW_COMPLETE",
        "decision": decision,
        "publish_allowed": False,
        "owner_approval_required": True,
        "critical_issues": critical,
        "warnings": warnings,
        "passed_checks": passed,
        "word_count": word_count,
        "safe_summary": (
            "Draft rejected due to critical issues."
            if decision == REJECT
            else (
                "Draft requires changes before owner approval."
                if decision == NEEDS_CHANGES
                else "Draft passed Master AI review; owner approval is still required."
            )
        ),
    }


def run_master_ai_content_review_agent(
    payload: dict[str, Any],
) -> str:
    """Review supplied draft content without publishing or saving."""
    if payload.get("publish") is True:
        raise PermissionError(
            "Master AI Content Review Agent cannot publish content."
        )

    if payload.get("send_telegram") is True:
        raise PermissionError(
            "Review Agent cannot send Telegram messages."
        )

    if payload.get("send_whatsapp") is True:
        raise PermissionError(
            "Review Agent cannot send WhatsApp messages."
        )

    document = payload.get("document")

    if not isinstance(document, dict):
        document = extract_cms_document(
            str(payload.get("body") or "")
        )

    if not isinstance(document, dict):
        raise ValueError(
            "A valid CMS V2 draft document or encoded body is required."
        )

    result = review_cms_document(document)
    return json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
    )
