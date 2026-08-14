"""Read-only Marketaux macro-news provider for XAUUSD Captain AI.

This module is secondary intelligence only.
It must never unlock the economic-calendar safety gate.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


MARKETAUX_URL = "https://api.marketaux.com/v1/news/all"

QUERIES = (
    "gold Federal Reserve",
    "gold inflation",
    "gold dollar",
    "Fed rate hike",
    "US inflation",
    "US jobs unemployment",
    "nonfarm payrolls",
    "Treasury yields dollar",
)

HIGH_VALUE_TERMS = (
    "gold",
    "xau",
    "federal reserve",
    "fed ",
    "inflation",
    "cpi",
    "ppi",
    "nonfarm",
    "payroll",
    "unemployment",
    "jobs",
    "interest rate",
    "rate hike",
    "rate cut",
    "treasury",
    "yield",
    "dollar",
    "usd",
)

GOLD_FALSE_POSITIVES = (
    "gold reserve announces",
    "gold reserve inc",
    "gold reserve ltd",
    "gold mining",
    "gold miner",
)


@dataclass(frozen=True)
class MacroHeadline:
    title: str
    source: str
    published_at: str
    url: str
    relevance_score: int
    themes: tuple[str, ...]


@dataclass(frozen=True)
class MarketauxContext:
    available: bool
    headlines: tuple[MacroHeadline, ...]
    reason: str


def _themes(title: str) -> tuple[str, ...]:
    text = title.lower()
    found: list[str] = []

    if "gold" in text or "xau" in text:
        found.append("GOLD")

    if (
        "federal reserve" in text
        or "fed " in text
        or "interest rate" in text
        or "rate hike" in text
        or "rate cut" in text
    ):
        found.append("FED")

    if any(word in text for word in ("inflation", "cpi", "ppi")):
        found.append("INFLATION")

    if any(
        word in text
        for word in (
            "nonfarm",
            "payroll",
            "unemployment",
            "jobs",
            "jobless",
        )
    ):
        found.append("JOBS")

    if "treasury" in text or "yield" in text:
        found.append("YIELDS")

    if "dollar" in text or " usd" in text:
        found.append("USD")

    return tuple(found)


def _score(title: str) -> int:
    text = title.lower()

    if any(term in text for term in GOLD_FALSE_POSITIVES):
        return 0

    score = 0

    for term in HIGH_VALUE_TERMS:
        if term in text:
            score += 1

    themes = _themes(title)

    # Cross-asset/macro combinations matter more for XAUUSD.
    if "GOLD" in themes and (
        "FED" in themes
        or "INFLATION" in themes
        or "USD" in themes
        or "YIELDS" in themes
        or "JOBS" in themes
    ):
        score += 3

    if "FED" in themes and "INFLATION" in themes:
        score += 2

    # US labour-market releases are directly relevant to USD/Fed expectations
    # and therefore deserve at least medium macro relevance for XAUUSD.
    if "JOBS" in themes:
        score += 1

    return score


def load_marketaux_xauusd_context(
    *,
    now: datetime | None = None,
    lookback_hours: int = 36,
    per_query_limit: int = 5,
    min_score: int = 2,
    session: Any = requests,
) -> MarketauxContext:
    api_key = os.getenv("MARKETAUX_API_KEY", "").strip()

    if not api_key:
        return MarketauxContext(
            available=False,
            headlines=(),
            reason="MARKETAUX_API_KEY is not configured.",
        )

    current = now or datetime.now(timezone.utc)

    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    published_after = (
        current - timedelta(hours=lookback_hours)
    ).strftime("%Y-%m-%dT%H:%M")

    candidates: dict[str, MacroHeadline] = {}
    successful_requests = 0

    for query in QUERIES:
        try:
            response = session.get(
                MARKETAUX_URL,
                params={
                    "api_token": api_key,
                    "search": query,
                    "language": "en",
                    "published_after": published_after,
                    "limit": per_query_limit,
                },
                timeout=20,
            )
        except Exception:
            continue

        if response.status_code != 200:
            continue

        try:
            payload = response.json()
        except Exception:
            continue

        successful_requests += 1

        for item in payload.get("data", []):
            title = str(item.get("title") or "").strip()

            if not title:
                continue

            relevance = _score(title)

            if relevance < min_score:
                continue

            key = title.casefold()

            candidate = MacroHeadline(
                title=title,
                source=str(item.get("source") or "").strip(),
                published_at=str(
                    item.get("published_at") or ""
                ).strip(),
                url=str(item.get("url") or "").strip(),
                relevance_score=relevance,
                themes=_themes(title),
            )

            previous = candidates.get(key)

            if (
                previous is None
                or candidate.relevance_score
                > previous.relevance_score
            ):
                candidates[key] = candidate

    if successful_requests == 0:
        return MarketauxContext(
            available=False,
            headlines=(),
            reason="All Marketaux requests failed.",
        )

    ordered = sorted(
        candidates.values(),
        key=lambda item: (
            item.relevance_score,
            item.published_at,
        ),
        reverse=True,
    )

    return MarketauxContext(
        available=True,
        headlines=tuple(ordered[:15]),
        reason="Marketaux macro-news context loaded.",
    )
