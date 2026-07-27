"""Secure MT5 XAUUSD H1 candle ingestion and source selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
from typing import Any

from services.mt5_h1_repository import H1Candle, H1Repository


ALLOWED_CANONICAL_SYMBOL = "XAUUSD"
ALLOWED_BROKER_SYMBOLS = frozenset({"XAUUSD", "GOLD", "XAUUSDM"})
ALLOWED_TIMEFRAME = "H1"


class MT5H1ValidationError(ValueError):
    """Raised when an MT5 payload fails closed validation."""


class MT5H1AuthenticationError(PermissionError):
    """Raised when the HMAC signature is invalid."""


class MT5H1DuplicateError(RuntimeError):
    """Raised when a source event has already been processed."""


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
    ).encode("utf-8")


def calculate_signature(secret: str, raw_body: bytes) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(secret: str, raw_body: bytes, signature: str) -> None:
    if not secret.strip():
        raise MT5H1AuthenticationError("MT5 ingestion is not configured.")

    supplied = signature.strip()
    if supplied.lower().startswith("sha256="):
        supplied = supplied[7:]

    expected = calculate_signature(secret, raw_body)

    if not hmac.compare_digest(supplied, expected):
        raise MT5H1AuthenticationError("Invalid MT5 payload signature.")


def ingest_h1_payload(
    *,
    raw_body: bytes,
    signature: str,
    secret: str,
    repository: H1Repository,
    now: datetime | None = None,
    max_payload_age: timedelta = timedelta(minutes=10),
) -> H1Candle:
    verify_signature(secret, raw_body, signature)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise MT5H1ValidationError("Malformed JSON payload.") from exc

    if not isinstance(payload, dict):
        raise MT5H1ValidationError("Payload must be a JSON object.")

    current_time = _as_utc(now or datetime.now(timezone.utc))
    received_timestamp = _parse_datetime(payload.get("timestamp_utc"))
    candle_start = _parse_datetime(payload.get("candle_start_utc"))

    if abs(current_time - received_timestamp) > max_payload_age:
        raise MT5H1ValidationError("Stale MT5 payload.")

    timeframe = str(payload.get("timeframe") or "").strip().upper()
    if timeframe != ALLOWED_TIMEFRAME:
        raise MT5H1ValidationError("Only H1 timeframe is accepted.")

    canonical_symbol = str(payload.get("symbol") or "").strip().upper()
    if canonical_symbol != ALLOWED_CANONICAL_SYMBOL:
        raise MT5H1ValidationError("Only XAUUSD is accepted.")

    broker_symbol = str(payload.get("broker_symbol") or "").strip().upper()
    if broker_symbol not in ALLOWED_BROKER_SYMBOLS:
        raise MT5H1ValidationError("Unsupported broker symbol.")

    broker_server = str(payload.get("broker_server") or "").strip()
    if not broker_server or len(broker_server) > 120:
        raise MT5H1ValidationError("Invalid broker server identifier.")

    source_event_id = str(payload.get("source_event_id") or "").strip()
    if not source_event_id or len(source_event_id) > 160:
        raise MT5H1ValidationError("Invalid source event ID.")

    if repository.event_exists(source_event_id):
        raise MT5H1DuplicateError("Duplicate MT5 source event.")

    open_price = _parse_price(payload.get("open"), "open")
    high_price = _parse_price(payload.get("high"), "high")
    low_price = _parse_price(payload.get("low"), "low")
    close_price = _parse_price(payload.get("close"), "close")

    if high_price < max(open_price, low_price, close_price):
        raise MT5H1ValidationError("High price is inconsistent.")

    if low_price > min(open_price, high_price, close_price):
        raise MT5H1ValidationError("Low price is inconsistent.")

    candle = H1Candle(
        symbol=ALLOWED_CANONICAL_SYMBOL,
        broker_symbol=broker_symbol,
        broker_server=broker_server,
        candle_start_utc=candle_start,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        source_event_id=source_event_id,
        received_at_utc=received_timestamp,
    )

    return repository.save_candle(candle)



def sheet_response(candle: H1Candle, *, fresh: bool) -> dict[str, Any]:
    """Return a Google Sheet-safe MT5-only H1 response."""

    return {
        "symbol": candle.symbol,
        "timeframe": "H1",
        "candle_start_utc": candle.candle_start_utc.isoformat(),
        "open": str(candle.open),
        "high": str(candle.high),
        "low": str(candle.low),
        "close": str(candle.close),
        "source": "MT5",
        "fresh": fresh,
        "broker_symbol": candle.broker_symbol,
        "broker_server": candle.broker_server,
        "received_at_utc": candle.received_at_utc.isoformat(),
    }

def _parse_datetime(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise MT5H1ValidationError("Timestamp is required.")

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MT5H1ValidationError("Invalid UTC timestamp.") from exc

    if parsed.tzinfo is None:
        raise MT5H1ValidationError("Timestamp must include timezone.")

    return parsed.astimezone(timezone.utc)


def _parse_price(value: Any, field: str) -> Decimal:
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MT5H1ValidationError(f"Invalid {field} price.") from exc

    if not price.is_finite() or price <= 0:
        raise MT5H1ValidationError(f"Invalid {field} price.")

    return price


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise MT5H1ValidationError("Datetime must include timezone.")

    return value.astimezone(timezone.utc)
