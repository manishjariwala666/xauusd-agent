"""Google Sheets signal enrichment service."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any

import gspread
from loguru import logger

from config import get_settings


@dataclass(frozen=True)
class SheetSignal:
    """Normalized BUY/SELL instruction read from Google Sheets."""

    direction: str
    target_price: Decimal | None
    stop_loss: Decimal | None
    label: str
    external_key: str


class GoogleSheetsConfigurationError(RuntimeError):
    """Raised when Sheets credentials or sheet settings are unavailable."""


class GoogleSheetsService:
    """Read the latest actionable signal from a configured worksheet."""

    _DIRECTION_HEADERS = ("buy_sell", "signal", "action", "direction")
    _TARGET_HEADERS = ("target", "target_price", "take_profit", "tp")
    _STOP_HEADERS = ("stop_loss", "stoploss", "sl")
    _LABEL_HEADERS = ("label", "note", "message", "remarks")

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.google_service_account_json:
            raise GoogleSheetsConfigurationError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is not configured."
            )
        try:
            credentials = json.loads(settings.google_service_account_json)
        except json.JSONDecodeError as exc:
            raise GoogleSheetsConfigurationError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON."
            ) from exc

        self._client = gspread.service_account_from_dict(credentials)
        self._sheet_name = settings.google_sheet_name
        self._worksheet_name = settings.google_worksheet_name

    def get_latest_signal(self) -> SheetSignal | None:
        """Return the most recent row containing a BUY or SELL direction."""
        try:
            worksheet = (
                self._client.open(self._sheet_name)
                .worksheet(self._worksheet_name)
            )
            rows = worksheet.get_all_records(
                default_blank="",
                numericise_ignore=["all"],
            )
        except Exception:
            logger.exception("Unable to read Google Sheet signal data")
            return None

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

        logger.info("No BUY or SELL row found in the configured worksheet")
        return None

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
