"""Read-only content quality and internal duplicate analysis."""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import text

from core.database import session_scope

_WORD = re.compile(r"[A-Za-z0-9\u00C0-\uFFFF']+")
_HEADING = re.compile(r"^\s{0,3}(#{2,6})\s+(.+?)\s*$", re.MULTILINE)
_MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(((?:https?://|/)[^)\s]+)\)", re.IGNORECASE)
_HTML_LINK = re.compile(r"<a\b[^>]*href=[\"'](https?://[^\"']+)", re.IGNORECASE)
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]+\)|<img\b[^>]*?(?:alt=[\"']([^\"']*)[\"'])?[^>]*>", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _plain(value: str) -> str:
    text_value = re.sub(r"```.*?```", " ", value or "", flags=re.DOTALL)
    text_value = re.sub(r"`[^`]*`", " ", text_value)
    text_value = re.sub(r"<[^>]+>", " ", text_value)
    text_value = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text_value)
    text_value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text_value)
    text_value = re.sub(r"^\s{0,3}#{1,6}\s+", "", text_value, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text_value).strip()


def _normalise(value: str) -> str:
    return " ".join(_WORD.findall(_plain(value).lower()))


def _tokens(value: str) -> list[str]:
    return _WORD.findall(_plain(value).lower())


def _similarity(left: str, right: str) -> float:
    a, b = _normalise(left), _normalise(right)
    if not a or not b:
        return 0.0
    sequence = SequenceMatcher(None, a, b).ratio()
    left_words, right_words = set(a.split()), set(b.split())
    union = left_words | right_words
    jaccard = len(left_words & right_words) / len(union) if union else 0.0
    return round((sequence * 0.55 + jaccard * 0.45) * 100, 1)


def _repeated_sentences(body: str) -> list[dict[str, Any]]:
    cleaned = re.sub(r"```.*?```", " ", body or "", flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"^\\s{0,3}#{1,6}\\s+", "", cleaned, flags=re.MULTILINE)

    sentences = []
    for item in _SENTENCE.split(cleaned):
        normalised = re.sub(r"\\s+", " ", item).strip()
        if len(normalised) >= 35:
            sentences.append(normalised)

    counts = Counter(item.lower() for item in sentences)
    originals = {item.lower(): item for item in sentences}

    return [
        {"text": originals[sentence][:180], "count": count}
        for sentence, count in counts.most_common(10)
        if count > 1
    ]


def analyse_content(
    *,
    title: str,
    slug: str,
    body: str,
    focus_keyword: str = "",
) -> dict[str, Any]:
    words = _tokens(body)
    word_count = len(words)
    characters = len(_plain(body))
    headings = Counter(len(marker) for marker, _ in _HEADING.findall(body or ""))

    keyword_tokens = _tokens(focus_keyword)
    keyword = " ".join(keyword_tokens)
    normalised_body = " ".join(words)
    keyword_count = normalised_body.count(keyword) if keyword else 0
    density = round(keyword_count * max(1, len(keyword_tokens)) * 100 / word_count, 2) if word_count else 0.0

    urls = _MARKDOWN_LINK.findall(body or "") + _HTML_LINK.findall(body or "")
    internal_links = sum(
        1 for url in urls
        if url.startswith("/") or "venusrealm.net" in url.lower()
    )
    external_links = len(urls) - internal_links

    image_matches = _IMAGE.findall(body or "")
    images = len(image_matches)
    missing_alt = sum(1 for first, second in image_matches if not (first or second or "").strip())

    checks: list[dict[str, Any]] = []

    def check(code: str, passed: bool, message: str, severity: str = "warning") -> None:
        checks.append({"code": code, "passed": passed, "severity": severity, "message": message})

    check("word_count", word_count >= 300, f"{word_count} words; aim for at least 300 when the topic needs depth.")
    check("body_h1", not bool(re.search(r"^\s{0,3}#\s+", body or "", re.MULTILINE)), "Body should not contain H1; keep the article title as the only H1.")
    check("headings", sum(headings.values()) > 0, f"{sum(headings.values())} H2–H6 headings found.")
    check("focus_keyword", bool(keyword), "Add a focus keyword.")
    check("keyword_density", not keyword or 0.3 <= density <= 3.0, f"Focus keyword density is {density}%.")
    check("internal_links", internal_links > 0, f"{internal_links} internal links found.")
    check("image_alt", missing_alt == 0, f"{missing_alt} body images have missing alt text.")
    check("slug_lowercase", slug == slug.lower(), "Slug should use lowercase characters.")
    repeated = _repeated_sentences(body)
    check("repeated_sentences", not repeated, f"{len(repeated)} repeated sentence groups found.")

    passed = sum(1 for item in checks if item["passed"])
    score = round(passed * 100 / len(checks)) if checks else 0

    return {
        "score": score,
        "word_count": word_count,
        "character_count": characters,
        "reading_time_minutes": max(1, round(word_count / 220)) if word_count else 0,
        "headings": {f"h{level}": headings[level] for level in range(2, 7)},
        "focus_keyword_count": keyword_count,
        "focus_keyword_density": density,
        "internal_links": internal_links,
        "external_links": external_links,
        "images": images,
        "images_missing_alt": missing_alt,
        "repeated_sentences": repeated,
        "checks": checks,
    }


def analyse_internal_duplicates(
    *,
    content_id: int,
    title: str,
    slug: str,
    body: str,
    limit: int = 5,
) -> dict[str, Any]:
    with session_scope() as session:
        rows = session.execute(text("""
            SELECT id, title, slug, body, is_published, updated_at
            FROM public.content_items
            WHERE deleted_at IS NULL AND id <> :id
            ORDER BY updated_at DESC
            LIMIT 500
        """), {"id": int(content_id)}).mappings().all()

    matches = []
    for source in rows:
        row = dict(source)
        title_similarity = _similarity(title, str(row.get("title") or ""))
        body_similarity = _similarity(body, str(row.get("body") or ""))
        combined = round(title_similarity * 0.35 + body_similarity * 0.65, 1)
        if combined >= 15 or str(row.get("slug") or "").lower() == slug.lower():
            matches.append({
                "id": int(row["id"]),
                "title": str(row.get("title") or ""),
                "slug": str(row.get("slug") or ""),
                "status": "published" if row.get("is_published") else "draft",
                "title_similarity": title_similarity,
                "body_similarity": body_similarity,
                "similarity": combined,
                "exact_slug_match": str(row.get("slug") or "").lower() == slug.lower(),
            })

    matches.sort(key=lambda item: (item["exact_slug_match"], item["similarity"]), reverse=True)
    top = matches[:max(1, min(10, int(limit)))]
    highest = top[0]["similarity"] if top else 0.0

    risk = "high" if any(item["exact_slug_match"] or item["similarity"] >= 75 for item in top) else "medium" if highest >= 45 else "low"
    return {
        "risk": risk,
        "highest_similarity": highest,
        "matches": top,
        "scope": "internal_database_only",
    }
