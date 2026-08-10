"""Google Sheets signal enrichment service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import csv
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

import gspread
from loguru import logger
import requests

from config import (
    get_settings,
    parse_google_service_account_json,
)


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
    targets: tuple[Decimal, ...] = ()
    target_slots: tuple[Decimal | None, ...] = ()


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
    _MIN_STOP_DISTANCE = Decimal("0.01")
    _SESSION_HEADER = re.compile(
        r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$",
        re.IGNORECASE,
    )
    _SLOT_LABEL = re.compile(
        r"^(\d{1,2}):(\d{2})(?:\s*(AM|PM))?\s*"
        r"(?:-|TO)\s*(\d{1,2}):(\d{2})(?:\s*(AM|PM))?$",
        re.IGNORECASE,
    )

    @classmethod
    def _select_analysis_stop_loss(
        cls,
        *,
        direction: str,
        entry_price: Decimal,
        explicit_stop: Decimal | None,
        current_high: Decimal,
        current_low: Decimal,
        previous_high: Decimal,
        previous_low: Decimal,
        session_high: Decimal | None,
        session_low: Decimal | None,
    ) -> tuple[Decimal | None, str]:
        """Select risk after direction is fixed, preferring local structure."""

        def is_valid(value: Decimal | None) -> bool:
            if value is None:
                return False
            distance = (
                entry_price - value
                if direction == "BUY"
                else value - entry_price
            )
            return distance >= cls._MIN_STOP_DISTANCE

        if is_valid(explicit_stop):
            return explicit_stop, f"sheet {direction} SL"

        structural_candidates = (
            (current_low, previous_low)
            if direction == "BUY"
            else (current_high, previous_high)
        )
        valid_structural = [
            value for value in structural_candidates if is_valid(value)
        ]
        if valid_structural:
            stop_loss = (
                max(valid_structural)
                if direction == "BUY"
                else min(valid_structural)
            )
            structure_name = (
                "recent candle low"
                if direction == "BUY"
                else "recent candle high"
            )
            return stop_loss, structure_name

        session_stop = session_low if direction == "BUY" else session_high
        if is_valid(session_stop):
            fallback_name = (
                "session low stop fallback"
                if direction == "BUY"
                else "session high stop fallback"
            )
            return session_stop, fallback_name

        return None, "no valid stop"

    def __init__(self) -> None:
        settings = get_settings()
        self._public_url = settings.google_sheet_public_url
        raw_credentials = str(
            settings.google_service_account_json or ""
        ).strip()

        credentials_path = str(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "")
            or ""
        ).strip()

        if not raw_credentials and credentials_path:
            path = Path(credentials_path).expanduser()

            if not path.is_file():
                raise GoogleSheetsConfigurationError(
                    "GOOGLE_SERVICE_ACCOUNT_JSON_PATH does not exist."
                )

            try:
                raw_credentials = path.read_text(
                    encoding="utf-8"
                ).strip()
            except OSError as exc:
                raise GoogleSheetsConfigurationError(
                    "Unable to read Google service-account file."
                ) from exc

        if not raw_credentials and not self._public_url:
            raise GoogleSheetsConfigurationError(
                "Google Sheets credentials or public URL are not configured."
            )

        self._client: Any | None = None

        if raw_credentials:
            try:
                credentials = parse_google_service_account_json(
                    raw_credentials
                )
                self._client = gspread.service_account_from_dict(
                    credentials
                )
            except Exception as exc:
                raise GoogleSheetsConfigurationError(
                    "Google service-account credentials could not be loaded."
                ) from exc

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

        # Track complete-session extremes. Initial risk must use the
        # active session high/low, not only the immediately previous row.
        # Keep extrema isolated by trading date and session.
        # Historical rows from older Sheet blocks must never affect
        # today's BUY/SELL stop loss.
        session_extremes: dict[
            tuple[str, str],
            dict[str, Decimal | None],
        ] = {}
        india = ZoneInfo("Asia/Kolkata")
        for position, (start_index, session_date) in enumerate(
            session_indexes
        ):
            end_index = (
                session_indexes[position + 1][0]
                if position + 1 < len(session_indexes)
                else len(values)
            )
            session_rows = values[start_index + 1 : end_index]
            target_tables: dict[
                str,
                dict[str, list[Decimal]],
            ] = {
                "default": {"BUY": [], "SELL": []},
                "morning": {"BUY": [], "SELL": []},
                "evening": {"BUY": [], "SELL": []},
            }

            explicit_stop_losses: dict[
                str,
                dict[str, Decimal | None],
            ] = {
                "morning": {"BUY": None, "SELL": None},
                "evening": {"BUY": None, "SELL": None},
            }
            target_section = "default"
            explicit_target_labels = False
            unlabeled_block_count = 0

            for target_index, target_row in enumerate(session_rows):
                cells = [str(cell).strip() for cell in target_row]
                joined = " ".join(cells).strip().lower()

                if len(cells) >= 16:
                    session_label = cells[7].strip().lower()
                    buy_sl_header = cells[14].strip().lower()
                    sell_sl_header = cells[15].strip().lower()

                    if (
                        session_label in {
                            "morning session",
                            "evening session",
                        }
                        and buy_sl_header == "buy sl"
                        and sell_sl_header == "sell sl"
                    ):
                        sl_session = (
                            "morning"
                            if session_label == "morning session"
                            else "evening"
                        )

                        if target_index + 1 < len(session_rows):
                            value_row = [
                                str(cell).strip()
                                for cell in session_rows[target_index + 1]
                            ]

                            if len(value_row) >= 16:
                                explicit_stop_losses[sl_session]["BUY"] = (
                                    cls._decimal_or_none(value_row[14])
                                )
                                explicit_stop_losses[sl_session]["SELL"] = (
                                    cls._decimal_or_none(value_row[15])
                                )

                if "morning targets" in joined:
                    target_section = "morning"
                    explicit_target_labels = True
                    continue
                if "evening targets" in joined:
                    target_section = "evening"
                    explicit_target_labels = True
                    continue

                if len(cells) < 10:
                    continue

                is_target_header = (
                    cells[7].strip().lower() == "target"
                    and cells[8].strip().lower() == "buy level"
                    and cells[9].strip().lower() == "sell level"
                )
                if is_target_header:
                    if not explicit_target_labels:
                        unlabeled_block_count += 1
                        target_section = (
                            "morning"
                            if unlabeled_block_count == 1
                            else "evening"
                        )
                    continue

                target_match = re.fullmatch(
                    r"target\s*([1-6])",
                    cells[7],
                    re.IGNORECASE,
                )
                if not target_match:
                    continue

                target_number = int(target_match.group(1))
                buy_level = cls._decimal_or_none(cells[8])
                sell_level = cls._decimal_or_none(cells[9])

                for direction, value in (
                    ("BUY", buy_level),
                    ("SELL", sell_level),
                ):
                    targets = target_tables[target_section][direction]
                    while len(targets) < target_number:
                        targets.append(Decimal("0"))
                    if value is not None:
                        targets[target_number - 1] = value

            # Preserve Target 1..6 positional identity.
            # Zero placeholders stay in-place until direction validation.
            for table in target_tables.values():
                for direction in ("BUY", "SELL"):
                    while len(table[direction]) < 6:
                        table[direction].append(Decimal("0"))
                    table[direction] = table[direction][:6]

            # Preserve compatibility when only one unlabelled table exists.
            for direction in ("BUY", "SELL"):
                if (
                    not target_tables["default"][direction]
                    and target_tables["morning"][direction]
                ):
                    target_tables["default"][direction] = list(
                        target_tables["morning"][direction]
                    )

            previous_row: tuple[
                Decimal,
                Decimal,
                Decimal,
            ] | None = None

            for row in session_rows:
                normalized = [str(cell).strip() for cell in row]
                if len(normalized) < 6:
                    continue

                slot_match = cls._SLOT_LABEL.match(normalized[0])
                if not slot_match:
                    continue

                high = cls._decimal_or_none(normalized[1])
                low = cls._decimal_or_none(normalized[2])
                sheet_previous_average = cls._decimal_or_none(normalized[3])
                current_average = cls._decimal_or_none(normalized[4])
                live_price = cls._decimal_or_none(normalized[5])

                if None in (
                    high,
                    low,
                    current_average,
                    live_price,
                ):
                    continue

                start_hour = int(slot_match.group(1))
                start_minute = int(slot_match.group(2))
                start_meridiem = str(
                    slot_match.group(3) or ""
                ).upper()

                if start_meridiem:
                    start_hour %= 12
                    if start_meridiem == "PM":
                        start_hour += 12

                observed_local = datetime.strptime(
                    (
                        f"{session_date} "
                        f"{start_hour:02d}:{start_minute:02d}"
                    ),
                    "%Y-%m-%d %H:%M",
                ).replace(tzinfo=india)

                observed_at = observed_local.astimezone(timezone.utc)
                end_hour = int(slot_match.group(4))
                end_minute = int(slot_match.group(5))
                end_meridiem = str(slot_match.group(6) or "").upper()

                if end_meridiem:
                    end_hour %= 12
                    if end_meridiem == "PM":
                        end_hour += 12

                closed_local = observed_local.replace(
                    hour=end_hour,
                    minute=end_minute,
                )
                if closed_local <= observed_local:
                    closed_local += timedelta(days=1)
                closed_at = closed_local.astimezone(timezone.utc)
                local_minutes = (
                    observed_local.hour * 60
                    + observed_local.minute
                )

                # Morning rows start at 03:30 and end with
                # 01:30 PM TO 02:30 PM.
                # 02:30 PM TO 03:30 PM is the first evening row.
                if 210 <= local_minutes < 870:
                    target_session = "morning"
                elif local_minutes >= 870 or local_minutes <= 150:
                    target_session = "evening"
                else:
                    previous_row = (
                        high,
                        low,
                        current_average,
                    )
                    continue

                session_key = (session_date, target_session)
                extremes = session_extremes.setdefault(
                    session_key,
                    {"high": None, "low": None},
                )

                session_high = extremes["high"]
                session_low = extremes["low"]

                extremes["high"] = (
                    high
                    if session_high is None
                    else max(session_high, high)
                )
                extremes["low"] = (
                    low
                    if session_low is None
                    else min(session_low, low)
                )

                age = normalized_now - observed_at
                if age < timedelta(minutes=-5) or age > max_age:
                    previous_row = (
                        high,
                        low,
                        current_average,
                    )
                    continue

                if previous_row is None:
                    previous_row = (
                        high,
                        low,
                        current_average,
                    )
                    continue

                previous_high, previous_low, previous_avg = (
                    previous_row
                )

                comparison_average = (
                    sheet_previous_average
                    if sheet_previous_average is not None
                    else previous_avg
                )

                # Direction is determined only by confirmed price structure.
                # Stop-loss sources are selected later and must never reverse
                # or otherwise influence the direction decision.
                bullish_setup = (
                    high > previous_high
                    and current_average > comparison_average
                    and live_price > current_average
                )
                bearish_setup = (
                    low < previous_low
                    and current_average < comparison_average
                    and live_price < current_average
                )

                previous_row = (
                    high,
                    low,
                    current_average,
                )

                # A row becomes actionable only after its configured bar has
                # closed, preventing an intrabar reversal from being emitted.
                if normalized_now < closed_at:
                    continue

                if bullish_setup:
                    direction = "BUY"
                    entry_price = current_average

                    explicit_sl = explicit_stop_losses[
                        target_session
                    ]["BUY"]

                    stop_loss, stop_source = (
                        cls._select_analysis_stop_loss(
                            direction=direction,
                            entry_price=entry_price,
                            explicit_stop=explicit_sl,
                            current_high=high,
                            current_low=low,
                            previous_high=previous_high,
                            previous_low=previous_low,
                            session_high=extremes["high"],
                            session_low=extremes["low"],
                        )
                    )

                    setup_name = (
                        "higher high + higher average + CMP above average + "
                        + stop_source
                    )
                elif bearish_setup:
                    direction = "SELL"
                    entry_price = current_average

                    explicit_sl = explicit_stop_losses[
                        target_session
                    ]["SELL"]

                    stop_loss, stop_source = (
                        cls._select_analysis_stop_loss(
                            direction=direction,
                            entry_price=entry_price,
                            explicit_stop=explicit_sl,
                            current_high=high,
                            current_low=low,
                            previous_high=previous_high,
                            previous_low=previous_low,
                            session_high=extremes["high"],
                            session_low=extremes["low"],
                        )
                    )

                    setup_name = (
                        "lower low + lower average + CMP below average + "
                        + stop_source
                    )
                else:
                    continue

                if stop_loss is None:
                    continue

                if (
                    direction == "BUY"
                    and stop_loss >= entry_price
                ) or (
                    direction == "SELL"
                    and stop_loss <= entry_price
                ):
                    continue

                selected_table = target_tables[target_session]
                if not selected_table[direction]:
                    selected_table = target_tables["default"]

                raw_targets = selected_table[direction]

                if direction == "BUY":
                    target_slots = tuple(
                        (
                            value
                            if value > 0 and value > entry_price
                            else None
                        )
                        for value in raw_targets[:6]
                    )
                else:
                    target_slots = tuple(
                        (
                            value
                            if value > 0 and value < entry_price
                            else None
                        )
                        for value in raw_targets[:6]
                    )

                directional_targets = tuple(
                    value
                    for value in target_slots
                    if value is not None
                )

                target = (
                    directional_targets[0]
                    if directional_targets
                    else (
                        high
                        if direction == "BUY"
                        else low
                    )
                )

                if (
                    direction == "BUY"
                    and target <= entry_price
                ) or (
                    direction == "SELL"
                    and target >= entry_price
                ):
                    continue

                label = (
                    f"{session_date} {normalized[0]} · "
                    f"{setup_name}"
                )

                candidates.append(
                    (
                        observed_at,
                        SheetSignal(
                            direction=direction,
                            target_price=target,
                            stop_loss=stop_loss,
                            label=label,
                            external_key=(
                                f"gsheet-session:{session_date}:"
                                f"{target_session}:{direction}"
                            ),
                            reference_price=entry_price,
                            observed_at=observed_at,
                            source=(
                                f"GOOGLE_SHEET:"
                                f"{cls._ANALYSIS_WORKSHEET}"
                            ),
                            targets=directional_targets,
                            target_slots=target_slots,
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
