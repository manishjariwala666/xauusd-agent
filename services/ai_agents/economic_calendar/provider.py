"""Read-only Trading Economics provider for USA/Canada high-impact events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import os
import re
from typing import Any
from urllib.parse import quote

import requests

from .models import EconomicEvent, EventCountry, EventImpact


_API_ROOT = "https://api.tradingeconomics.com"
_COUNTRIES = {
    EventCountry.USA: "united states",
    EventCountry.CANADA: "canada",
}
_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _decimal(value: Any) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None

    match = _NUMBER.search(text)
    if not match:
        return None

    try:
        number = Decimal(match.group(0))
    except InvalidOperation:
        return None

    suffix = text.upper()

    if "T" in suffix:
        number *= Decimal("1000000000000")
    elif "B" in suffix:
        number *= Decimal("1000000000")
    elif "M" in suffix:
        number *= Decimal("1000000")
    elif "K" in suffix:
        number *= Decimal("1000")

    return number


def _datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()

    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _country(value: Any) -> EventCountry | None:
    normalized = str(value or "").strip().lower()

    if normalized == "united states":
        return EventCountry.USA
    if normalized == "canada":
        return EventCountry.CANADA
    return None


def parse_calendar_event(payload: dict[str, Any]) -> EconomicEvent | None:
    """Normalize one approved high-impact USA/Canada calendar event."""
    country = _country(payload.get("Country"))

    if country is None:
        return None

    try:
        importance = int(payload.get("Importance") or 0)
    except (TypeError, ValueError):
        return None

    if importance != 3:
        return None

    scheduled_at = _datetime(payload.get("Date"))

    if scheduled_at is None:
        return None

    event_id = str(
        payload.get("CalendarId")
        or payload.get("CalendarID")
        or payload.get("Ticker")
        or ""
    ).strip()

    title = str(
        payload.get("Event")
        or payload.get("Category")
        or ""
    ).strip()

    if not event_id or not title:
        return None

    return EconomicEvent(
        event_id=event_id,
        country=country,
        currency="USD" if country is EventCountry.USA else "CAD",
        title=title,
        impact=EventImpact.HIGH,
        scheduled_at=scheduled_at,
        previous=_decimal(payload.get("Previous")),
        forecast=_decimal(
            payload.get("Forecast")
            or payload.get("TEForecast")
        ),
        actual=_decimal(payload.get("Actual")),
        source=str(payload.get("Source") or "TRADING_ECONOMICS"),
    )


def load_high_impact_events(
    *,
    now: datetime | None = None,
    hours_before: int = 2,
    hours_after: int = 24,
) -> tuple[EconomicEvent, ...]:
    """Fetch nearby high-impact USA/Canada events without persistence."""
    api_key = os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()

    if not api_key:
        return ()

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = (current - timedelta(hours=hours_before)).date().isoformat()
    end = (current + timedelta(hours=hours_after)).date().isoformat()

    countries = quote("united states,canada", safe=",")
    url = (
        f"{_API_ROOT}/calendar/country/{countries}/{start}/{end}"
    )

    response = requests.get(
        url,
        params={
            "c": api_key,
            "importance": 3,
            "values": "true",
            "f": "json",
        },
        timeout=8,
    )
    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, list):
        return ()

    events = tuple(
        event
        for item in payload
        if isinstance(item, dict)
        if (event := parse_calendar_event(item)) is not None
    )

    return tuple(sorted(events, key=lambda item: item.scheduled_at))
