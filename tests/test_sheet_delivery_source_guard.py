import re

import services.production_agents as production_agents


class CanonicalSheets:
    _SESSION_HEADER = re.compile(
        r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$",
        re.IGNORECASE,
    )

    def _analysis_values(self):
        return [["DATE: 2026-08-19"], ["canonical session"]]


class LegacyOnlySheets(CanonicalSheets):
    def _analysis_values(self):
        return [["legacy structured sheet only"]]


def test_legacy_sheet_row_is_blocked_when_canonical_sessions_exist(monkeypatch):
    monkeypatch.setattr(
        production_agents,
        "GoogleSheetsService",
        CanonicalSheets,
    )

    blocked, reason = production_agents._legacy_sheet_signal_is_superseded(
        {"external_key": "gsheet:old-hash"}
    )

    assert blocked is True
    assert "superseded" in reason


def test_manual_signal_is_not_affected_by_sheet_source_guard():
    blocked, reason = production_agents._legacy_sheet_signal_is_superseded(
        {"external_key": "admin:123"}
    )

    assert blocked is False
    assert reason == ""


def test_legacy_sheet_row_remains_allowed_without_canonical_sessions(monkeypatch):
    monkeypatch.setattr(
        production_agents,
        "GoogleSheetsService",
        LegacyOnlySheets,
    )

    blocked, reason = production_agents._legacy_sheet_signal_is_superseded(
        {"external_key": "gsheet:legacy-only"}
    )

    assert blocked is False
    assert reason == ""
