"""Deterministic, review-first helpers for the private AI Content Studio."""

from __future__ import annotations

import base64
from io import BytesIO
import re
from typing import Any

from pypdf import PdfReader

from services.admin_content_service import normalize_slug


MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_PDF_TEXT = 60_000


def extract_pdf_source(pdf_base64: str) -> tuple[str, int]:
    """Extract bounded PDF text; never follows links or executes embedded content."""
    try:
        raw = base64.b64decode(pdf_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Upload a valid PDF file.") from exc
    if not raw or len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF"):
        raise ValueError("PDF must be valid and no larger than 5 MB.")
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
    except Exception as exc:
        raise ValueError("PDF could not be read safely.") from exc
    if not reader.pages or len(reader.pages) > MAX_PDF_PAGES:
        raise ValueError("PDF must contain between 1 and 20 pages.")
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(str(page.extract_text() or ""))
        if sum(len(item) for item in chunks) >= MAX_PDF_TEXT:
            break
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", "\n".join(chunks))
    text = re.sub(r"[ \t]+", " ", text).strip()[:MAX_PDF_TEXT]
    if len(text) < 80:
        raise ValueError("PDF does not contain enough extractable text.")
    return text, len(reader.pages)


def build_repair_preview(
    current: dict[str, Any], options: set[str]
) -> dict[str, Any]:
    """Return a deterministic preview for the same post; this function never saves."""
    allowed = {"title", "structure", "repetition", "table", "faq", "seo", "readability"}
    selected = options & allowed
    title = " ".join(str(current.get("title") or "Untitled post").split())[:240]
    body = str(current.get("body") or "").strip()
    excerpt = " ".join(str(current.get("excerpt") or "").split())
    focus_keyword = " ".join(str(current.get("focus_keyword") or title).split())[:160]

    if "title" in selected:
        title = title.rstrip(" .:-")
    if "structure" in selected and not re.search(r"(?m)^#\s+", body):
        body = f"# {title}\n\n{body}"
    if "repetition" in selected:
        paragraphs = body.split("\n\n")
        seen: set[str] = set()
        unique: list[str] = []
        for paragraph in paragraphs:
            key = re.sub(r"\W+", " ", paragraph).strip().lower()
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            unique.append(paragraph)
        body = "\n\n".join(unique)
    if "readability" in selected:
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if "table" in selected and "<table" not in body.lower():
        body += (
            "\n\n## Verification Table\n\n<table>\n"
            "<thead><tr><th>Claim</th><th>Evidence</th><th>Status</th></tr></thead>\n"
            "<tbody><tr><td>Primary topic</td><td>Source review</td>"
            "<td>Verification required</td></tr></tbody>\n</table>"
        )

    faq = list(current.get("faq") or [])
    if "faq" in selected and len(faq) < 6:
        faq = [
            {
                "question": f"What should readers verify about {focus_keyword}?",
                "answer": "Check the source, date, scope and any assumptions before relying on the claim.",
            },
            {
                "question": f"Why does {focus_keyword} matter?",
                "answer": "Its relevance depends on the reader's goal, current evidence and risk context.",
            },
            {
                "question": "When should this information be reviewed?",
                "answer": "Review it whenever source data, market conditions or applicable guidance changes.",
            },
            {
                "question": "Where should supporting facts come from?",
                "answer": "Use current primary or authoritative sources and record the publication date.",
            },
            {
                "question": "How are unknown figures handled?",
                "answer": "Unknown metrics are labelled verification required rather than estimated.",
            },
            {
                "question": "Does this draft guarantee an outcome?",
                "answer": "No. It is educational content and remains subject to human review.",
            },
        ]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Article", "headline": title, "about": focus_keyword},
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item.get("question", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": item.get("answer", "")},
                    }
                    for item in faq
                ],
            },
        ],
    }
    if not excerpt:
        excerpt = re.sub(r"[#*_<>]", "", body)[:240].strip()
    return {
        "content_id": int(current["id"]),
        "title": title,
        "slug": normalize_slug(str(current.get("slug") or title)),
        "excerpt": excerpt[:2_000],
        "body": body,
        "meta_title": (title if "seo" in selected else current.get("meta_title") or title)[:255],
        "meta_description": (
            excerpt[:155] if "seo" in selected else str(current.get("meta_description") or excerpt[:155])
        ),
        "focus_keyword": focus_keyword,
        "faq": faq,
        "schema_jsonld": schema,
        "status": current.get("status"),
        "published_at": current.get("published_at"),
        "review_required": True,
        "applied": False,
    }
