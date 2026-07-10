"""Private Google Sheets logbook integration for Master AI operations.

This service uses only a Google service-account JSON document and a private
spreadsheet ID. It intentionally does not support public API keys or published
CSV URLs because the operational log book contains private admin data.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from typing import Any

import gspread
from loguru import logger

from config import parse_google_service_account_json


REQUIRED_TABS = (
    "settings",
    "telegram_master_logs",
    "telegram_public_signals",
    "whatsapp_messages",
    "xauusd_signals",
    "users",
    "content_queue",
    "errors",
)

DEFAULT_HEADERS: dict[str, list[str]] = {
    "settings": ["created_at", "key", "value", "notes"],
    "telegram_master_logs": [
        "created_at",
        "event_type",
        "status",
        "run_id",
        "chat_id",
        "user_id",
        "message",
        "reply",
        "notes",
    ],
    "telegram_public_signals": [
        "created_at",
        "status",
        "message_id",
        "direction",
        "entry",
        "target_1",
        "target_2",
        "target_3",
        "stop_loss",
        "notes",
    ],
    "whatsapp_messages": [
        "created_at",
        "status",
        "phone",
        "message",
        "reply",
        "notes",
    ],
    "xauusd_signals": [
        "created_at",
        "source",
        "status",
        "direction",
        "entry",
        "target_1",
        "target_2",
        "target_3",
        "stop_loss",
        "risk_level",
        "notes",
    ],
    "users": [
        "created_at",
        "user_id",
        "name",
        "telegram_id",
        "whatsapp",
        "status",
        "plan",
        "notes",
    ],
    "content_queue": [
        "created_at",
        "content_type",
        "status",
        "title",
        "slug",
        "topic",
        "platform",
        "notes",
    ],
    "errors": [
        "created_at",
        "source",
        "status",
        "error_type",
        "message",
        "notes",
    ],
}


class GoogleSheetsServiceError(RuntimeError):
    """Raised when the private Google Sheets logbook is unavailable."""


def append_row(tab_name: str, row_dict: dict[str, Any]) -> None:
    """Append one dictionary row to a required Google Sheet tab.

    Missing configured columns are written as blanks. New keys are appended to
    the header row so operational logging can evolve without migrations.
    """
    service = PrivateGoogleSheetsService()
    service.append_row(tab_name, row_dict)


def read_rows(tab_name: str, limit: int = 100) -> list[dict[str, Any]]:
    """Read recent rows from a required tab, newest rows last."""
    service = PrivateGoogleSheetsService()
    return service.read_rows(tab_name, limit=limit)


def ensure_required_tabs() -> None:
    """Create all required tabs and headers if they do not exist."""
    PrivateGoogleSheetsService().ensure_required_tabs()


class PrivateGoogleSheetsService:
    """Small, safe wrapper around a private service-account spreadsheet."""

    def __init__(
        self,
        *,
        sheet_id: str | None = None,
        service_account_json: str | None = None,
        client: gspread.Client | None = None,
    ) -> None:
        self._sheet_id = (sheet_id or _sheet_id()).strip()
        self._client = client or _client(service_account_json)
        self._spreadsheet: Any | None = None

    def ensure_required_tabs(self) -> None:
        for tab_name in REQUIRED_TABS:
            self._worksheet(tab_name)

    def append_row(self, tab_name: str, row_dict: dict[str, Any]) -> None:
        normalized_tab = _normalize_tab_name(tab_name)
        if not isinstance(row_dict, dict):
            raise GoogleSheetsServiceError("row_dict must be a dictionary.")

        worksheet = self._worksheet(normalized_tab)
        headers = _ensure_headers(worksheet, normalized_tab, row_dict)
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            **row_dict,
        }
        values = [_stringify_cell(payload.get(header, "")) for header in headers]
        worksheet.append_row(values, value_input_option="USER_ENTERED")

    def read_rows(self, tab_name: str, limit: int = 100) -> list[dict[str, Any]]:
        normalized_tab = _normalize_tab_name(tab_name)
        safe_limit = max(1, min(int(limit or 100), 1000))
        worksheet = self._worksheet(normalized_tab)
        records = worksheet.get_all_records(
            default_blank="",
            numericise_ignore=["all"],
        )
        return [dict(row) for row in records[-safe_limit:]]

    def _worksheet(self, tab_name: str) -> Any:
        spreadsheet = self._open_spreadsheet()
        try:
            worksheet = spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=tab_name,
                rows=1000,
                cols=max(20, len(DEFAULT_HEADERS[tab_name]) + 5),
            )
        _ensure_headers(worksheet, tab_name, {})
        return worksheet

    def _open_spreadsheet(self) -> Any:
        if self._spreadsheet is None:
            self._spreadsheet = self._client.open_by_key(self._sheet_id)
        return self._spreadsheet


def append_event(row: dict[str, Any], *, worksheet_name: str | None = None) -> None:
    """Backward-compatible append helper used by older Master AI code."""
    append_row(worksheet_name or "telegram_master_logs", row)


def append_master_log(
    *,
    command: str,
    status: str,
    run_id: int | str | None = None,
    chat_id: int | str | None = None,
    user_id: int | str | None = None,
    notes: str = "",
) -> None:
    """Append one Master AI command audit entry."""
    try:
        append_row(
            "telegram_master_logs",
            {
                "event_type": "master_command",
                "status": status,
                "run_id": run_id or "",
                "chat_id": chat_id or "",
                "user_id": user_id or "",
                "message": command,
                "notes": notes,
            },
        )
    except Exception:
        logger.exception("Unable to append Telegram Master AI log to Sheets")


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
    """Append one XAUUSD signal audit entry."""
    try:
        append_row(
            "xauusd_signals",
            {
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
        )
    except Exception:
        logger.exception("Unable to append XAUUSD signal log to Sheets")


def append_content_queue_log(
    *,
    content_type: str,
    status: str,
    title: str,
    slug: str,
    topic: str = "",
    platform: str = "website",
    notes: str = "",
) -> None:
    """Best-effort content queue audit log; never raise to callers."""
    try:
        append_row(
            "content_queue",
            {
                "content_type": content_type,
                "status": status,
                "title": title,
                "slug": slug,
                "topic": topic,
                "platform": platform,
                "notes": notes,
            },
        )
    except Exception:
        logger.exception("Unable to append content queue log to Sheets")


def append_message_log(
    *,
    channel: str,
    status: str,
    user_id: str = "",
    phone: str = "",
    message: str = "",
    reply: str = "",
    notes: str = "",
) -> None:
    """Best-effort Telegram/WhatsApp message log; never raise to callers."""
    normalized = str(channel or "").strip().upper()
    tab_name = (
        "telegram_master_logs"
        if normalized == "TELEGRAM"
        else "whatsapp_messages"
    )
    try:
        if tab_name == "telegram_master_logs":
            append_row(
                tab_name,
                {
                    "event_type": "message",
                    "status": status,
                    "user_id": user_id,
                    "message": message,
                    "reply": reply,
                    "notes": notes,
                },
            )
        else:
            append_row(
                tab_name,
                {
                    "status": status,
                    "phone": phone or user_id,
                    "message": message,
                    "reply": reply,
                    "notes": notes,
                },
            )
    except Exception:
        logger.exception("Unable to append message log to Sheets")


def append_public_signal_log(
    *,
    status: str,
    message_id: str = "",
    direction: str = "",
    entry: str | float = "",
    target_1: str | float = "",
    target_2: str | float = "",
    target_3: str | float = "",
    stop_loss: str | float = "",
    notes: str = "",
) -> None:
    """Best-effort public Telegram signal audit log."""
    try:
        append_row(
            "telegram_public_signals",
            {
                "status": status,
                "message_id": message_id,
                "direction": direction,
                "entry": entry,
                "target_1": target_1,
                "target_2": target_2,
                "target_3": target_3,
                "stop_loss": stop_loss,
                "notes": notes,
            },
        )
    except Exception:
        logger.exception("Unable to append public signal log to Sheets")


def _client(service_account_json: str | None = None) -> gspread.Client:
    raw_json = (
        service_account_json
        or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        or ""
    ).strip()
    if not raw_json:
        raise GoogleSheetsServiceError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is required for private sheet access."
        )
    credentials = parse_google_service_account_json(raw_json)
    return gspread.service_account_from_dict(credentials)


def _sheet_id() -> str:
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if sheet_id:
        return sheet_id
    try:
        from config import get_settings

        value = getattr(get_settings(), "google_sheet_id", "") or ""
        if str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    raise GoogleSheetsServiceError("GOOGLE_SHEET_ID is required.")


def _normalize_tab_name(tab_name: str) -> str:
    normalized = str(tab_name or "").strip()
    if normalized not in REQUIRED_TABS:
        raise GoogleSheetsServiceError(
            "Unsupported Google Sheet tab: " + normalized
        )
    return normalized


def _ensure_headers(
    worksheet: Any,
    tab_name: str,
    row_dict: dict[str, Any],
) -> list[str]:
    configured = list(DEFAULT_HEADERS[tab_name])
    existing = [str(value).strip() for value in worksheet.row_values(1)]
    headers = existing or configured

    changed = False
    for header in configured:
        if header not in headers:
            headers.append(header)
            changed = True
    for key in row_dict:
        header = str(key).strip()
        if header and header not in headers:
            headers.append(header)
            changed = True

    if not existing:
        worksheet.append_row(headers, value_input_option="USER_ENTERED")
    elif changed:
        worksheet.update("1:1", [headers], value_input_option="USER_ENTERED")
    return headers


def _stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)
