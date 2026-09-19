from datetime import datetime
from decimal import Decimal
import re
from zoneinfo import ZoneInfo

from services.session_signal_broadcast import (
    SessionSetup,
    format_session_setup_message,
    load_due_session_setups,
)


INDIA = ZoneInfo("Asia/Kolkata")


class FakeSheets:
    _SESSION_HEADER = re.compile(
        r"^(?:XAUUSD SESSION\s+|DATE:\s*)(\d{4}-\d{2}-\d{2})$",
        re.IGNORECASE,
    )
    _SLOT_LABEL = re.compile(
        r"^(\d{1,2}):(\d{2})(?:\s*(AM|PM))?\s*"
        r"(?:-|TO)\s*(\d{1,2}):(\d{2})(?:\s*(AM|PM))?$",
        re.IGNORECASE,
    )

    def __init__(self, values):
        self._values = values

    def _analysis_values(self):
        return self._values

    def _select_analysis_targets(
        self,
        *,
        direction,
        entry_price,
        raw_targets,
        fallback_high,
        fallback_low,
    ):
        del fallback_high, fallback_low
        previous = entry_price
        selected = []
        slots = []
        for value in raw_targets[:6]:
            valid = (
                value > previous if direction == "BUY" else value < previous
            )
            slots.append(value if valid else None)
            if valid:
                selected.append(value)
                previous = value
        if not selected:
            return None
        return selected[0], tuple(selected), tuple(slots)


def _target_row(slot, buy, sell, session):
    row = [slot, "", "", "", "", "", "", "", buy, sell]
    row.extend(["", "", "", session])
    return row


def _values():
    rows = [
        ["DATE: 2026-09-21"],
        [
            "MORNING SESSION",
            "Session High",
            "Session Low",
            "Buy Base",
            "Sell Base",
            "Mode",
        ],
        ["", "4382", "4360", "4366", "4376", "Aggressive"],
        [
            "EVENING SESSION",
            "Session High",
            "Session Low",
            "Buy Base",
            "Sell Base",
            "Mode",
        ],
        ["", "4400", "4370", "4380", "4390", "Aggressive"],
    ]
    morning_buy = ["4370", "4374", "4378", "4382", "4386", "4390"]
    morning_sell = ["4372", "4368", "4364", "4360", "4356", "4352"]
    evening_buy = ["4384", "4388", "4392", "4396", "4400", "4404"]
    evening_sell = ["4386", "4382", "4378", "4374", "4370", "4366"]

    morning_slots = [
        "03:30 AM TO 04:30 AM",
        "04:30 AM TO 05:30 AM",
        "05:30 AM TO 06:30 AM",
        "06:30 AM TO 07:30 AM",
        "07:30 AM TO 08:30 AM",
        "08:30 AM TO 09:30 AM",
    ]
    evening_slots = [
        "02:30 PM TO 03:30 PM",
        "03:30 PM TO 04:30 PM",
        "04:30 PM TO 05:30 PM",
        "05:30 PM TO 06:30 PM",
        "06:30 PM TO 07:30 PM",
        "07:30 PM TO 08:30 PM",
    ]
    for slot, buy, sell in zip(morning_slots, morning_buy, morning_sell):
        rows.append(_target_row(slot, buy, sell, "MORNING SESSION"))
    for slot, buy, sell in zip(evening_slots, evening_buy, evening_sell):
        rows.append(_target_row(slot, buy, sell, "EVENING SESSION"))
    return rows


def test_morning_start_exposes_buy_and_sell_only():
    setups = load_due_session_setups(
        FakeSheets(_values()),
        now=datetime(2026, 9, 21, 3, 35, tzinfo=INDIA),
    )

    assert [(item.session_name, item.direction) for item in setups] == [
        ("morning", "BUY"),
        ("morning", "SELL"),
    ]
    assert setups[0].targets[-1] == Decimal("4390")
    assert setups[1].targets[-1] == Decimal("4352")


def test_evening_start_exposes_all_four_daily_setups():
    setups = load_due_session_setups(
        FakeSheets(_values()),
        now=datetime(2026, 9, 21, 14, 35, tzinfo=INDIA),
    )

    assert [(item.session_name, item.direction) for item in setups] == [
        ("morning", "BUY"),
        ("morning", "SELL"),
        ("evening", "BUY"),
        ("evening", "SELL"),
    ]


def test_weekend_is_off():
    weekend_values = _values()
    weekend_values[0] = ["DATE: 2026-09-19"]

    setups = load_due_session_setups(
        FakeSheets(weekend_values),
        now=datetime(2026, 9, 19, 15, 0, tzinfo=INDIA),
    )

    assert setups == []


def test_four_professional_message_styles_include_t1_t6_and_profit_footer():
    samples = [
        SessionSetup(
            signal_date="2026-09-21",
            session_name=session,
            direction=direction,
            entry=Decimal("4380"),
            stop_loss=Decimal("4360") if direction == "BUY" else Decimal("4400"),
            targets=(
                Decimal("4382"),
                Decimal("4384"),
                Decimal("4386"),
                Decimal("4388"),
                Decimal("4390"),
                Decimal("4392"),
            ),
        )
        for session, direction in (
            ("morning", "BUY"),
            ("morning", "SELL"),
            ("evening", "BUY"),
            ("evening", "SELL"),
        )
    ]

    messages = [format_session_setup_message(sample) for sample in samples]

    assert "🌅🟢 XAUUSD MORNING BUY SIGNAL" in messages[0]
    assert "🌅🔴 XAUUSD MORNING SELL SIGNAL" in messages[1]
    assert "🌆🟢 XAUUSD EVENING BUY SIGNAL" in messages[2]
    assert "🌆🔴 XAUUSD EVENING SELL SIGNAL" in messages[3]

    for message in messages:
        assert "1️⃣ Target 1:" in message
        assert "6️⃣ Target 6:" in message
        assert "💰 Profit Book:" in message
        assert "🎉💚 Enjoy Profit from VenusRealm 💚🎉" in message
        assert "returns are not guaranteed" in message
