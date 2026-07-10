"""Offline tests for private Google Sheets logbook service."""

from __future__ import annotations

import pytest

from services.google_sheets_service import (
    DEFAULT_HEADERS,
    GoogleSheetsServiceError,
    PrivateGoogleSheetsService,
    REQUIRED_TABS,
)


class FakeWorksheet:
    def __init__(self, title: str) -> None:
        self.title = title
        self.rows: list[list[str]] = []

    def row_values(self, row: int) -> list[str]:
        if row != 1 or not self.rows:
            return []
        return list(self.rows[0])

    def append_row(self, values: list[str], **_: object) -> None:
        self.rows.append(list(values))

    def update(self, _: str, values: list[list[str]], **__: object) -> None:
        if self.rows:
            self.rows[0] = list(values[0])
        else:
            self.rows.append(list(values[0]))

    def get_all_records(self, **_: object) -> list[dict[str, str]]:
        if not self.rows:
            return []
        headers = self.rows[0]
        return [
            {
                header: row[index] if index < len(row) else ""
                for index, header in enumerate(headers)
            }
            for row in self.rows[1:]
        ]


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.worksheets: dict[str, FakeWorksheet] = {}

    def worksheet(self, name: str) -> FakeWorksheet:
        if name not in self.worksheets:
            import gspread

            raise gspread.WorksheetNotFound(name)
        return self.worksheets[name]

    def add_worksheet(self, title: str, **_: object) -> FakeWorksheet:
        worksheet = FakeWorksheet(title)
        self.worksheets[title] = worksheet
        return worksheet


class FakeClient:
    def __init__(self) -> None:
        self.spreadsheet = FakeSpreadsheet()

    def open_by_key(self, _: str) -> FakeSpreadsheet:
        return self.spreadsheet


def test_required_tabs_are_exact_phase_two_tabs() -> None:
    assert REQUIRED_TABS == (
        "settings",
        "telegram_master_logs",
        "telegram_public_signals",
        "whatsapp_messages",
        "xauusd_signals",
        "users",
        "content_queue",
        "errors",
    )


def test_append_row_creates_tab_headers_and_extends_new_keys() -> None:
    client = FakeClient()
    service = PrivateGoogleSheetsService(sheet_id="sheet-id", client=client)

    service.append_row(
        "telegram_master_logs",
        {"status": "SUCCESS", "message": "/master status", "extra": "ok"},
    )

    worksheet = client.spreadsheet.worksheets["telegram_master_logs"]
    headers = worksheet.rows[0]
    assert headers[: len(DEFAULT_HEADERS["telegram_master_logs"])] == (
        DEFAULT_HEADERS["telegram_master_logs"]
    )
    assert "extra" in headers
    assert worksheet.rows[1][headers.index("status")] == "SUCCESS"
    assert worksheet.rows[1][headers.index("message")] == "/master status"


def test_read_rows_returns_recent_limited_records() -> None:
    client = FakeClient()
    service = PrivateGoogleSheetsService(sheet_id="sheet-id", client=client)

    for index in range(3):
        service.append_row(
            "errors",
            {"source": "test", "status": f"E{index}", "message": "safe"},
        )

    rows = service.read_rows("errors", limit=2)

    assert [row["status"] for row in rows] == ["E1", "E2"]


def test_unknown_tab_is_rejected() -> None:
    service = PrivateGoogleSheetsService(sheet_id="sheet-id", client=FakeClient())

    with pytest.raises(GoogleSheetsServiceError):
        service.append_row("unknown", {"status": "bad"})
