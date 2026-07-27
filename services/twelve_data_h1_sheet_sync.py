"""Fetch XAU/USD H1 data from Twelve Data and append it to Google Sheets."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.google_sheets_service import append_row


WORKSHEET_NAME = "xauusd_h1_market_data"
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"


def fetch_latest_xauusd_h1() -> dict[str, Any]:
    api_key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing.")

    query = urlencode(
        {
            "symbol": "XAU/USD",
            "interval": "1h",
            "outputsize": 2,
            "timezone": "UTC",
        }
    )

    request = Request(
        f"{TWELVE_DATA_URL}?{query}",
        headers={
            "Authorization": f"apikey {api_key}",
            "Accept": "application/json",
            "User-Agent": "VenusRealm-XAUUSD-Agent/1.0",
        },
    )

    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") == "error":
        raise RuntimeError(
            f"Twelve Data error {payload.get('code')}: "
            f"{payload.get('message')}"
        )

    values = payload.get("values") or []
    if not values:
        raise RuntimeError("Twelve Data returned no H1 candles.")

    latest = values[0]
    meta = payload.get("meta") or {}

    return {
        "symbol": meta.get("symbol") or "XAU/USD",
        "timeframe": meta.get("interval") or "1h",
        "candle_time_utc": latest["datetime"],
        "open": latest["open"],
        "high": latest["high"],
        "low": latest["low"],
        "close": latest["close"],
        "source": "TWELVE_DATA",
        "record_type": "EXTERNAL_API_H1",
        "is_test": False,
        "synced_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def sync_latest_xauusd_h1(
    worksheet_name: str = WORKSHEET_NAME,
) -> dict[str, Any]:
    row = fetch_latest_xauusd_h1()
    append_row(worksheet_name, row)
    return row
