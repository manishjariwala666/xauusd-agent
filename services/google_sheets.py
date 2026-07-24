"""Google Sheets signal enrichment service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import csv
import hashlib
from io import StringIO
import json
import re
from typing import Any
from zoneinfo import ZoneInfo

import gspread
from loguru import logger
import requests

from config import get_settings


@dataclass(frozen=True)
class SheetSignal:
    """Normalized BUY/SELL instruction read from Google Sheets."""

    direction: str
    target_price: Decimal | None
    stop_loss: Decimal | None
    label: str
    external_key: str
    reference_price: Decimal | None = None
    observed_at: datetime | None = None
    source: str = "GOOGLE_SHEET"


class GoogleSheetsConfigurationError(RuntimeError):
    """Raised when Sheets credentials or sheet settings are unavailable."""


class GoogleSheetsService:
    """Read the latest actionable signal from a configured worksheet."""

    _DIRECTION_HEADERS = ("buy_sell", "signal", "action", "direction")
    _TARGET_HEADERS = ("target", "target_price", "take_profit", "tp")
    _STOP_HEADERS = ("stop_loss", "stoploss", "sl")
    _LABEL_HEADERS = ("label", "note", "message", "remarks")
    _ANALYSIS_WORKSHEET = "Sheet1"
    _MAX_ANALYSIS_AGE = timedelta(hours=6)
    _SESSION_HEADER = re.compile(
        r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$",
        re.IGNORECASE,
    )
    _SLOT_LABEL = re.compile(
        r"^(\d{1,2}):(\d{2})(?:\s*(AM|PM))?\s*"
        r"(?:-|TO)\s*(\d{1,2}):(\d{2})(?:\s*(AM|PM))?$",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        settings = get_settings()
        self._public_url = settings.google_sheet_public_url
        if (
            not settings.google_service_account_json
            and not self._public_url
        ):
            raise GoogleSheetsConfigurationError(
                "Google Sheets credentials or public URL are not configured."
            )
        self._client: Any | None = None
        if settings.google_service_account_json:
            try:
                credentials = json.loads(
                    settings.google_service_account_json
                )
            except json.JSONDecodeError as exc:
                raise GoogleSheetsConfigurationError(
                    "GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON."
                ) from exc
            self._client = gspread.service_account_from_dict(credentials)
        self._sheet_id = settings.google_sheet_id
        self._sheet_name = settings.google_sheet_name
        self._worksheet_name = settings.google_worksheet_name

    def get_latest_signal(self) -> SheetSignal | None:
        """Return the most recent row containing a BUY or SELL direction."""
        rows: list[dict[str, Any]] = []
        if self._client is not None:
            try:
                configured_worksheet = (
                    (
                        self._client.open_by_key(self._sheet_id)
                        if self._sheet_id
                        else self._client.open(self._sheet_name)
                    )
                    .worksheet(self._worksheet_name)
                )
                rows = configured_worksheet.get_all_records(
                    default_blank="",
                    numericise_ignore=["all"],
                )
            except Exception:
                logger.exception("Unable to read Google Sheet signal data")

        for row_number, raw_row in reversed(
            list(enumerate(rows, start=2))
        ):
            row = {
                self._normalize_header(key): value
                for key, value in raw_row.items()
            }
            direction_value = self._first_value(
                row,
                self._DIRECTION_HEADERS,
            )
            direction = str(direction_value).strip().upper()
            if direction not in {"BUY", "SELL"}:
                continue

            target = self._decimal_or_none(
                self._first_value(row, self._TARGET_HEADERS)
            )
            stop_loss = self._decimal_or_none(
                self._first_value(row, self._STOP_HEADERS)
            )
            label_value = self._first_value(row, self._LABEL_HEADERS)
            label = str(label_value).strip() or direction
            external_key = self._build_external_key(
                row_number,
                direction,
                target,
                stop_loss,
                label,
            )
            logger.info(
                "Google Sheet signal loaded: row={} direction={}",
                row_number,
                direction,
            )
            return SheetSignal(
                direction=direction,
                target_price=target,
                stop_loss=stop_loss,
                label=label,
                external_key=external_key,
            )

        logger.info(
            "No structured BUY or SELL row found; checking latest analysis "
            "session"
        )
        try:
            analysis_values = self._analysis_values()
        except Exception:
            logger.exception("Unable to read Google Sheet analysis data")
            return None
        return self.parse_latest_analysis_signal(
            analysis_values,
            now=datetime.now(timezone.utc),
            max_age=self._MAX_ANALYSIS_AGE,
        )

    def _analysis_values(self) -> list[list[str]]:
        if self._client is not None:
            return (
                (
                    self._client.open_by_key(self._sheet_id)
                    if self._sheet_id
                    else self._client.open(self._sheet_name)
                )
                .worksheet(self._ANALYSIS_WORKSHEET)
                .get_all_values()
            )
        csv_url = self.public_csv_url(self._public_url, gid="0")
        response = requests.get(csv_url, timeout=20)
        response.raise_for_status()
        return list(csv.reader(StringIO(response.text)))

    @staticmethod
    def public_csv_url(public_url: str, *, gid: str) -> str:
        """Convert a published Google Sheet URL to a CSV export endpoint."""
        cleaned = str(public_url or "").strip()
        if "/spreadsheets/d/e/" not in cleaned:
            raise GoogleSheetsConfigurationError(
                "GOOGLE_SHEET_PUBLIC_URL is invalid."
            )
        base = cleaned.split("/pubhtml", maxsplit=1)[0]
        base = base.split("/pub", maxsplit=1)[0]
        return f"{base}/pub?gid={gid}&single=true&output=csv"

    @classmethod
    def parse_latest_analysis_signal(
        cls,
        values: list[list[Any]],
        *,
        now: datetime,
        max_age: timedelta,
    ) -> SheetSignal | None:
        """Derive a fresh trend from the newest valid analysis session row."""
        normalized_now = (
            now.replace(tzinfo=timezone.utc)
            if now.tzinfo is None
            else now.astimezone(timezone.utc)
        )
        session_indexes: list[tuple[int, str]] = []
        for index, row in enumerate(values):
            first_cell = str(row[0] if row else "").strip()
            match = cls._SESSION_HEADER.match(first_cell)
            if match:
                session_indexes.append((index, match.group(1)))
        candidates: list[tuple[datetime, SheetSignal]] = []
        india = ZoneInfo("Asia/Kolkata")
        for position, (start_index, session_date) in enumerate(
            session_indexes
        ):
            end_index = (
                session_indexes[position + 1][0]
                if position + 1 < len(session_indexes)
                else len(values)
            )
            for row in values[start_index + 1 : end_index]:
                normalized = [str(cell).strip() for cell in row]
                if len(normalized) < 6:
                    continue
                slot_match = cls._SLOT_LABEL.match(normalized[0])
                if not slot_match:
                    continue
                high = cls._decimal_or_none(normalized[1])
                low = cls._decimal_or_none(normalized[2])
                previous_average = cls._decimal_or_none(normalized[3])
                live_price = cls._decimal_or_none(normalized[5])
                if None in (high, low, previous_average, live_price):
                    continue
                start_hour = int(slot_match.group(1))
                start_minute = int(slot_match.group(2))
                start_meridiem = str(slot_match.group(3) or "").upper()
                if start_meridiem:
                    start_hour %= 12
                    if start_meridiem == "PM":
                        start_hour += 12
                observed_local = datetime.strptime(
                    f"{session_date} {start_hour:02d}:{start_minute:02d}",
                    "%Y-%m-%d %H:%M",
                ).replace(tzinfo=india)
                observed_at = observed_local.astimezone(timezone.utc)
                age = normalized_now - observed_at
                if age < timedelta(minutes=-5) or age > max_age:
                    continue
                direction = (
                    "BUY" if live_price >= previous_average else "SELL"
                )
                target = high if direction == "BUY" else low
                stop_loss = previous_average
                if (
                    direction == "BUY" and stop_loss >= live_price
                ) or (
                    direction == "SELL" and stop_loss <= live_price
                ):
                    continue
                relation = (
                    "above" if direction == "BUY" else "below"
                )
                label = (
                    f"{session_date} {normalized[0]} · CMP {relation} "
                    "previous average"
                )
                candidates.append(
                    (
                        observed_at,
                        SheetSignal(
                            direction=direction,
                            target_price=target,
                            stop_loss=stop_loss,
                            label=label,
                            external_key=cls._build_external_key(
                                start_index,
                                direction,
                                target,
                                stop_loss,
                                label,
                            ),
                            reference_price=live_price,
                            observed_at=observed_at,
                            source=(
                                f"GOOGLE_SHEET:{cls._ANALYSIS_WORKSHEET}"
                            ),
                        ),
                    )
                )
        if not candidates:
            logger.warning("No fresh valid Google Sheet analysis row found")
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        signal = candidates[0][1]
        logger.info(
            "Fresh Google Sheet trend loaded: direction={} observed_at={}",
            signal.direction,
            signal.observed_at,
        )
        return signal

    @staticmethod
    def _normalize_header(value: Any) -> str:
        return (
            str(value)
            .strip()
            .lower()
            .replace("/", "_")
            .replace(" ", "_")
            .replace("-", "_")
        )

    @staticmethod
    def _first_value(
        row: dict[str, Any],
        candidates: tuple[str, ...],
    ) -> Any:
        for key in candidates:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return ""

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        cleaned = str(value).strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            logger.warning("Ignoring non-numeric Sheet price value: {}", value)
            return None

    @staticmethod
    def _build_external_key(
        row_number: int,
        direction: str,
        target: Decimal | None,
        stop_loss: Decimal | None,
        label: str,
    ) -> str:
        canonical = "|".join(
            (
                str(row_number),
                direction,
                str(target or ""),
                str(stop_loss or ""),
                label,
            )
        )
        return "gsheet:" + hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
