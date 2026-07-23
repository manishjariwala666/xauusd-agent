"""Read-only XAUUSD signal intelligence for VenusRealm Master AI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any
from zoneinfo import ZoneInfo

from services.google_sheets import GoogleSheetsService


INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")

_DATE_HEADER = re.compile(
    r"^DATE:\s*(\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
)

_TIME_SLOT = re.compile(
    r"^(\d{1,2}:\d{2}\s*(?:AM|PM))\s+TO\s+"
    r"(\d{1,2}:\d{2}\s*(?:AM|PM))$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MasterAISignalSnapshot:
    signal_date: date
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal | None
    day_high: Decimal | None
    day_low: Decimal | None
    step: Decimal | None
    range_value: Decimal | None
    buy_base: Decimal | None
    sell_base: Decimal | None
    mode: str
    latest_slot: str | None
    live_cmp: Decimal | None
    buy_targets: tuple[Decimal, ...]
    sell_targets: tuple[Decimal, ...]
    source: str = "GOOGLE_SHEET"


def _decimal(value: Any) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _cell(row: list[Any], index: int) -> str:
    if index >= len(row):
        return ""
    return str(row[index] or "").strip()


def _find_date_blocks(
    values: list[list[Any]],
) -> list[tuple[int, date]]:
    blocks: list[tuple[int, date]] = []

    for index, row in enumerate(values):
        first_cell = _cell(row, 0)
        match = _DATE_HEADER.match(first_cell)
        if not match:
            continue

        try:
            block_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue

        blocks.append((index, block_date))

    return blocks


def parse_signal_snapshot(
    values: list[list[Any]],
    *,
    target_date: date,
) -> MasterAISignalSnapshot | None:
    """Parse one exact DATE block without creating or publishing a signal."""

    blocks = _find_date_blocks(values)
    matching_positions = [
        position
        for position, (_, block_date) in enumerate(blocks)
        if block_date == target_date
    ]

    if not matching_positions:
        return None

    # Same date ke multiple blocks hon to sheet ka last block authoritative hoga.
    selected_position = matching_positions[-1]
    start_index, signal_date = blocks[selected_position]
    end_index = (
        blocks[selected_position + 1][0]
        if selected_position + 1 < len(blocks)
        else len(values)
    )
    block = values[start_index:end_index]

    summary_row: list[Any] | None = None
    hourly_header_index: int | None = None

    for relative_index, row in enumerate(block):
        normalized = [_cell(row, index).lower() for index in range(len(row))]

        if (
            "open" in normalized
            and "high" in normalized
            and "low" in normalized
            and "close" in normalized
            and "buy base" in normalized
            and "sell base" in normalized
        ):
            if relative_index + 1 < len(block):
                summary_row = block[relative_index + 1]

        if normalized and normalized[0] == "time":
            hourly_header_index = relative_index

    if summary_row is None:
        return None

    open_price = _decimal(_cell(summary_row, 0))
    high_price = _decimal(_cell(summary_row, 1))
    low_price = _decimal(_cell(summary_row, 2))
    close_price = _decimal(_cell(summary_row, 3))

    day_high = _decimal(_cell(summary_row, 8))
    day_low = _decimal(_cell(summary_row, 9))
    step = _decimal(_cell(summary_row, 10))
    range_value = _decimal(_cell(summary_row, 11))
    buy_base = _decimal(_cell(summary_row, 12))
    sell_base = _decimal(_cell(summary_row, 13))
    mode = _cell(summary_row, 14)

    latest_slot: str | None = None
    live_cmp: Decimal | None = None
    buy_targets: list[Decimal] = []
    sell_targets: list[Decimal] = []

    if hourly_header_index is not None:
        for row in block[hourly_header_index + 1 :]:
            slot = _cell(row, 0)
            if not _TIME_SLOT.match(slot):
                continue

            row_live_cmp = _decimal(_cell(row, 5))
            if row_live_cmp is not None:
                latest_slot = slot
                live_cmp = row_live_cmp

            buy_target = _decimal(_cell(row, 8))
            sell_target = _decimal(_cell(row, 9))

            if buy_target is not None:
                buy_targets.append(buy_target)
            if sell_target is not None:
                sell_targets.append(sell_target)

    return MasterAISignalSnapshot(
        signal_date=signal_date,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        day_high=day_high,
        day_low=day_low,
        step=step,
        range_value=range_value,
        buy_base=buy_base,
        sell_base=sell_base,
        mode=mode,
        latest_slot=latest_slot,
        live_cmp=live_cmp,
        buy_targets=tuple(buy_targets[:6]),
        sell_targets=tuple(sell_targets[:6]),
    )


def get_signal_snapshot_for_date(
    target_date: date,
) -> MasterAISignalSnapshot | None:
    """Load Sheet1 and return the requested date's calculated values."""

    service = GoogleSheetsService()
    values = service._analysis_values()
    return parse_signal_snapshot(values, target_date=target_date)


def get_today_signal_snapshot(
    *,
    now: datetime | None = None,
) -> MasterAISignalSnapshot | None:
    current = now or datetime.now(INDIA_TIMEZONE)

    if current.tzinfo is None:
        current = current.replace(tzinfo=INDIA_TIMEZONE)
    else:
        current = current.astimezone(INDIA_TIMEZONE)

    return get_signal_snapshot_for_date(current.date())
