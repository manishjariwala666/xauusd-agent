from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
from types import SimpleNamespace

from services.sheet_signal_source import load_authoritative_sheet_signal


class FakeSheets:
    _SESSION_HEADER = re.compile(
        r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$",
        re.IGNORECASE,
    )
    _MAX_ANALYSIS_AGE = timedelta(hours=6)

    def __init__(self, values, parsed):
        self.values = values
        self.parsed = parsed
        self.legacy_calls = 0
        self.parse_calls = 0

    def _analysis_values(self):
        return self.values

    def parse_latest_analysis_signal(self, values, *, now, max_age):
        assert values is self.values
        assert max_age == self._MAX_ANALYSIS_AGE
        self.parse_calls += 1
        return self.parsed

    def get_latest_signal(self):
        self.legacy_calls += 1
        return SimpleNamespace(
            direction="SELL",
            target_price=Decimal("4300"),
            stop_loss=Decimal("4500"),
            external_key="legacy-stale",
        )


def test_canonical_session_overrides_stale_legacy_sl_tp():
    canonical = SimpleNamespace(
        direction="BUY",
        reference_price=Decimal("4332.95"),
        target_price=Decimal("4350.00"),
        targets=(Decimal("4350.00"), Decimal("4360.00")),
        stop_loss=Decimal("4318.00"),
        external_key="gsheet-session:2026-08-19:morning:BUY",
    )
    sheets = FakeSheets(
        [["DATE: 2026-08-19"], ["canonical data"]],
        canonical,
    )

    result = load_authoritative_sheet_signal(
        sheets,
        now=datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
    )

    assert result is canonical
    assert result.target_price == Decimal("4350.00")
    assert result.stop_loss == Decimal("4318.00")
    assert sheets.parse_calls == 1
    assert sheets.legacy_calls == 0


def test_canonical_session_without_fresh_signal_fails_closed():
    sheets = FakeSheets(
        [["XAUUSD SESSION 2026-08-19"], ["stale or invalid"]],
        None,
    )

    result = load_authoritative_sheet_signal(
        sheets,
        now=datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
    )

    assert result is None
    assert sheets.parse_calls == 1
    assert sheets.legacy_calls == 0


def test_legacy_source_remains_fallback_only_without_canonical_sessions():
    sheets = FakeSheets([["plain structured worksheet"]], None)

    result = load_authoritative_sheet_signal(
        sheets,
        now=datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
    )

    assert result.external_key == "legacy-stale"
    assert sheets.parse_calls == 0
    assert sheets.legacy_calls == 1
