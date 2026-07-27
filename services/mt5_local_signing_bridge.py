"""Local-only MT5 signing bridge.

Run this on the same Windows VPS as MT5.
It accepts only local XAUUSD H1 payloads and forwards signed HTTPS requests.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest

from services.mt5_h1_market_data import (
    ALLOWED_BROKER_SYMBOLS,
    ALLOWED_CANONICAL_SYMBOL,
    ALLOWED_TIMEFRAME,
)


app = FastAPI(
    title="MT5 Local Signing Bridge",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _target_url() -> str:
    return os.getenv("MT5_H1_REMOTE_URL", "").strip()


def _secret() -> str:
    return os.getenv("MT5_H1_INGEST_SECRET", "").strip()


@app.post("/local/mt5/h1")
async def forward_mt5_h1(request: FastAPIRequest) -> dict[str, object]:
    client_host = request.client.host if request.client else ""

    if client_host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Local access only.")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Malformed JSON.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required.")

    if str(payload.get("symbol", "")).upper() != ALLOWED_CANONICAL_SYMBOL:
        raise HTTPException(status_code=400, detail="XAUUSD only.")

    if str(payload.get("timeframe", "")).upper() != ALLOWED_TIMEFRAME:
        raise HTTPException(status_code=400, detail="H1 only.")

    broker_symbol = str(payload.get("broker_symbol", "")).upper()
    if broker_symbol not in ALLOWED_BROKER_SYMBOLS:
        raise HTTPException(status_code=400, detail="Broker symbol rejected.")

    target = _target_url()
    secret = _secret()

    if not target.startswith("https://"):
        raise HTTPException(
            status_code=503,
            detail="Remote HTTPS endpoint is not configured.",
        )

    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Signing secret is not configured.",
        )

    raw = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    ).encode("utf-8")

    signature = hmac.new(
        secret.encode("utf-8"),
        raw,
        hashlib.sha256,
    ).hexdigest()

    outbound = Request(
        target,
        data=raw,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-MT5-Signature": signature,
        },
    )

    try:
        with urlopen(outbound, timeout=10) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Remote API rejected payload with HTTP {exc.code}.",
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=502,
            detail="Remote API unavailable.",
        ) from exc

    return {
        "status": "forwarded",
        "remote_status": status,
        "remote_response": body[:500],
    }
