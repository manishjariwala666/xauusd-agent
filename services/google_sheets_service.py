"""Google Sheets helper for Master AI logs and XAUUSD signal automation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import gspread


DEFAULT_HEADERS = [
    "created_at",
    "event_type",
    "platform",
    "source",
    "run_id",
    "status",
    "chat_id",
    "user_id",
    "message",
    "reply",
    "direction",
    "entry",
    "target_1",
    "target_2",
    "target_3",
    "stop_loss",
    "risk_level",
    "notes",
]


def _client() -> gspread.Client:
    raw_json = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_CREDENTIALS_JSON")
        or ""
    ).strip()

    file_path = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or ""
    ).strip()

    if raw_json:
        creds = json.loads(raw_json)
        return gspread.service_account_from_dict(creds)

    if file_path:
        return gspread.service_account(filename=file_path)

    raise RuntimeError(
        "Google Sheets credentials missing. Set GOOGLE_SERVICE_ACCOUNT_JSON "
        "or GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def _sheet_id() -> str:
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if sheet_id:
        return sheet_id

    # Existing config fallback.
    try:
        from config import get_settings

        value = getattr(get_settings(), "google_sheet_id", "") or ""
        if str(value).strip():
            return str(value).strip()
    except Exception:
        pass

    raise RuntimeError("GOOGLE_SHEET_ID is missing.")


def _worksheet_name(default: str = "Signals") -> str:
    return (
        os.getenv("GOOGLE_WORKSHEET_NAME")
        or os.getenv("GOOGLE_WORKSHEET")
        or default
    ).strip()


def get_worksheet(name: str | None = None) -> Any:
    spreadsheet = _client().open_by_key(_sheet_id())
    worksheet_name = name or _worksheet_name()

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name,
            rows=1000,
            cols=len(DEFAULT_HEADERS) + 5,
        )

    values = worksheet.get_all_values()
    if not values:
        worksheet.append_row(DEFAULT_HEADERS, value_input_option="USER_ENTERED")

    return worksheet


def append_event(row: dict[str, Any], *, worksheet_name: str | None = None) -> None:
    worksheet = get_worksheet(worksheet_name)

    headers = worksheet.row_values(1)
    if not headers:
        headers = DEFAULT_HEADERS
        worksheet.append_row(headers, value_input_option="USER_ENTERED")

    created_at = datetime.now(timezone.utc).isoformat()
    payload = {"created_at": created_at, **row}

    values = [payload.get(header, "") for header in headers]
    worksheet.append_row(values, value_input_option="USER_ENTERED")


def append_master_log(
    *,
    command: str,
    status: str,
    run_id: int | str | None = None,
    chat_id: int | str | None = None,
    user_id: int | str | None = None,
    notes: str = "",
) -> None:
    append_event(
        {
            "event_type": "master_command",
            "platform": "telegram",
            "source": "master_ai",
            "run_id": run_id or "",
            "status": status,
            "chat_id": chat_id or "",
            "user_id": user_id or "",
            "message": command,
            "notes": notes,
        },
        worksheet_name=os.getenv("GOOGLE_MASTER_LOG_WORKSHEET", "MasterLogs"),
    )


def append_signal_log(
    *,
    source: str,
    status: str,
    direction: str = "",
    entry: str | float = "",
    target_1: str | float = "",
    target_2: str | float = "",
    target_3: str | float = "",
    stop_loss: str | float = "",
    risk_level: str = "",
    notes: str = "",
) -> None:
    append_event(
        {
            "event_type": "xauusd_signal",
            "platform": "system",
            "source": source,
            "status": status,
            "direction": direction,
            "entry": entry,
            "target_1": target_1,
            "target_2": target_2,
            "target_3": target_3,
            "stop_loss": stop_loss,
            "risk_level": risk_level,
            "notes": notes,
        },
        worksheet_name=os.getenv("GOOGLE_SIGNAL_LOG_WORKSHEET", "Signals"),
    )
