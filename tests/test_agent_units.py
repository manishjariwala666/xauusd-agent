"""Offline tests for deterministic production-agent behavior."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import warnings

warnings.filterwarnings(
    "ignore",
    message="'_UnionGenericAlias' is deprecated.*",
    category=DeprecationWarning,
)

from services.google_sheets import GoogleSheetsService
from services.production_agents import (
    _blog_heading_count,
    _fallback_blog_payload,
    _master_optional_agent,
    _seo_issues,
    _slugify,
    run_blog_agent,
    run_image_agent,
)
from services.telegram_service import TelegramService
from backend import _is_telegram_command
from services.conversation_service import (
    _auto_reply_agents_enabled,
    _extract_blog_topic,
    _is_blog_only_command,
    _public_blog_commands_enabled,
    _requests_image,
)


def test_all_production_agent_runners_exist() -> None:
    from services.production_agents import RUNNERS

    assert set(RUNNERS) == {
        "ai_blog_agent",
        "cms_editor_agent",
        "telegram_reply_agent",
        "whatsapp_reply_agent",
        "signal_agent",
        "announcement_agent",
        "seo_agent",
        "image_agent",
    }


def test_slug_is_safe_and_stable() -> None:
    assert _slugify("XAUUSD: Risk & Reward!") == "xauusd-risk-reward"


def test_blog_fallback_payload_is_publish_safe() -> None:
    payload = _fallback_blog_payload("xauusd usa market")

    assert payload["title"]
    assert payload["slug"] == "xauusd-usa-market"
    assert payload["meta_description"]
    assert "Risk disclaimer" in payload["body_markdown"]
    assert isinstance(payload["faq"], list)
    assert len(payload["faq"]) >= 6
    assert isinstance(payload["schema_jsonld"], dict)
    assert 1200 <= len(payload["body_markdown"].split()) <= 1900
    assert _blog_heading_count(payload["body_markdown"], 1) == 1
    assert payload["body_markdown"].count("## ") >= 6
    assert "### " in payload["body_markdown"]
    assert "#### " in payload["body_markdown"]
    assert "##### " in payload["body_markdown"]
    assert "<details>" in payload["body_markdown"]
    assert payload["keyword_volume"] == "Unknown - verification required"


def test_master_ai_blog_publish_default_uses_payload_override(monkeypatch) -> None:
    from services.production_agents import _blog_publish_default

    monkeypatch.setattr(
        "services.production_agents.get_site_setting",
        lambda _: "draft",
    )

    assert _blog_publish_default(
        {"publish": True, "owner_approved_publish": True}
    )
    assert not _blog_publish_default({"publish": True})
    assert not _blog_publish_default({"publish": False})
    assert not _blog_publish_default({})


def test_worker_blog_agent_returns_final_venusrealm_public_url(monkeypatch) -> None:
    class FakeResult:
        def __init__(self, value: object) -> None:
            self.value = value

        def scalar_one_or_none(self) -> object:
            return self.value

        def scalar(self) -> object:
            return None

    class FakeSession:
        def execute(self, statement: object, params: dict | None = None) -> FakeResult:
            sql = str(statement)
            if "to_regclass" in sql:
                return FakeResult("public.content_seo")
            if "content_categories" in sql:
                return FakeResult(11)
            return FakeResult(None)

    class FakeScope:
        def __enter__(self) -> FakeSession:
            return FakeSession()

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setenv("PUBLIC_WEBSITE_URL", "https://venusrealm.net")
    monkeypatch.setattr(
        "services.production_agents.AIProvider",
        lambda: type(
            "FailingProvider",
            (),
            {"generate_json": lambda self, **_: (_ for _ in ()).throw(RuntimeError("offline"))},
        )(),
    )
    monkeypatch.setattr("services.production_agents.session_scope", lambda: FakeScope())
    monkeypatch.setattr(
        "services.production_agents.save_content",
        lambda **_: 321,
    )
    monkeypatch.setattr(
        "services.production_agents._blog_publish_default",
        lambda _: True,
    )

    result = run_blog_agent({"topic": "xauusd usa market"})

    assert "Public URL: https://venusrealm.net/blog?post=xauusd-usa-market" in result
    assert "xauusd-buy-sell-signal.streamlit.app" not in result
    assert "streamlit.app" not in result
    assert "xauusd-agent-web-production.up.railway.app" not in result


def test_image_agent_skips_provider_failure(monkeypatch) -> None:
    class FailingProvider:
        def generate_image(self, **_: object) -> None:
            raise RuntimeError("quota exhausted")

    monkeypatch.setattr(
        "services.production_agents.AIProvider",
        lambda: FailingProvider(),
    )

    assert run_image_agent({"prompt": "gold market chart"}).startswith(
        "Image generation skipped"
    )


def test_natural_blog_command_routes_as_blog_only() -> None:
    command = "xauusd usa market ka seo blog banao"

    assert _is_blog_only_command(command)
    assert _extract_blog_topic(command) == "xauusd usa market"
    assert not _requests_image(command)


def test_blog_command_with_signal_is_not_blog_only() -> None:
    assert not _is_blog_only_command("xauusd buy sell target signal blog banao")
    assert _requests_image("xauusd seo blog banao with image")


def test_scheduled_signal_payload_is_not_skipped() -> None:
    calls: list[dict] = []

    def handler(payload: dict) -> str:
        calls.append(payload)
        return "signal ok"

    wrapped = _master_optional_agent("signal_agent", handler)

    assert wrapped({"scheduled_signal": True}) == "signal ok"
    assert calls == [{"scheduled_signal": True}]


def test_public_auto_reply_and_blog_commands_are_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_AUTO_REPLY_AGENTS", raising=False)
    monkeypatch.delenv("ENABLE_PUBLIC_BLOG_COMMANDS", raising=False)

    assert not _auto_reply_agents_enabled()
    assert not _public_blog_commands_enabled()

    monkeypatch.setenv("ENABLE_AUTO_REPLY_AGENTS", "true")
    monkeypatch.setenv("ENABLE_PUBLIC_BLOG_COMMANDS", "true")

    assert _auto_reply_agents_enabled()
    assert _public_blog_commands_enabled()


def test_seo_issue_detection() -> None:
    issues = _seo_issues(
        {
            "meta_title": "",
            "meta_description": "",
            "focus_keyword": "",
            "slug": "",
        }
    )
    assert len(issues) == 4


def test_telegram_signal_formatter_escapes_html() -> None:
    message = TelegramService.format_message(
        {
            "signal_type": "BUY",
            "price": 2300,
            "target_price": 2320,
            "stop_loss": 2280,
            "sheet_label": "<unsafe>",
            "source": "test",
        }
    )
    assert "&lt;unsafe&gt;" in message
    assert "<unsafe>" not in message


def test_signal_formatting_includes_multi_targets_and_risk_fields() -> None:
    message = TelegramService.format_message(
        {
            "signal_type": "SELL",
            "price": 4120,
            "target_1": 4110,
            "target_2": 4100,
            "target_3": 4090,
            "stop_loss": 4130,
            "risk_level": "Medium",
            "timeframe": "Intraday",
            "note": "Wait for confirmation",
            "source": "admin",
        }
    )

    assert "Targets:" in message
    assert "4,110.00, 4,100.00, 4,090.00" in message
    assert "<b>Risk:</b> Medium" in message
    assert "<b>Timeframe:</b> Intraday" in message


def test_trend_selects_newest_fresh_valid_signal() -> None:
    now = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
    selected = TelegramService.select_latest_valid_signal(
        [
            {
                "id": 1,
                "signal_type": "BUY",
                "price": 4100,
                "signal_time": "2026-07-03T12:00:00+00:00",
            },
            {
                "id": 2,
                "signal_type": "SELL",
                "price": 4150,
                "signal_time": "2026-07-06T10:00:00+00:00",
            },
            {
                "id": 3,
                "signal_type": "BUY",
                "price": 4160,
                "signal_time": "2026-07-06T11:30:00+00:00",
            },
        ],
        now=now,
        max_age=timedelta(hours=6),
    )
    assert selected is not None
    assert selected["id"] == 3


def test_trend_never_returns_stale_or_malformed_signal() -> None:
    now = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
    selected = TelegramService.select_latest_valid_signal(
        [
            {
                "signal_type": "BUY",
                "price": 4100,
                "signal_time": "2026-07-03T12:00:00+00:00",
            },
            {
                "signal_type": "SELL",
                "price": "not-a-number",
                "signal_time": "2026-07-06T11:30:00+00:00",
            },
        ],
        now=now,
        max_age=timedelta(hours=6),
    )
    assert selected is None


def test_telegram_user_error_never_exposes_internal_details() -> None:
    assert TelegramService.SAFE_USER_ERROR == (
        "⚠️ Service temporarily unavailable. Please try again later."
    )
    assert "http" not in TelegramService.SAFE_USER_ERROR
    assert "Traceback" not in TelegramService.SAFE_USER_ERROR


def test_trend_command_matching_is_strict() -> None:
    assert _is_telegram_command("/trend", "trend")
    assert _is_telegram_command("/trend@xauusd_bot now", "trend")
    assert not _is_telegram_command("/trend_old", "trend")
    assert not _is_telegram_command("show trend", "trend")


def test_latest_sheet_analysis_row_produces_fresh_trend() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-06"],
        [],
        ["Time", "High", "Low", "Previous AVG", "AVG", "Live CMP"],
        [],
        [],
        [
            "14:30 - 15:30",
            "4160",
            "4136",
            "4156",
            "4152",
            "4144",
        ],
        [
            "15:30 - 16:30",
            "4155",
            "4132",
            "4152",
            "4149",
            "4154",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 11, 10, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4149")
    assert signal.target_price == Decimal("4155")
    assert signal.stop_loss == Decimal("4136")

def test_sheet_analysis_never_returns_stale_session() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-03"],
        [],
        ["Time", "High", "Low", "Previous AVG", "AVG", "Live CMP"],
        [],
        [],
        ["15:30 - 16:30", "4155", "4142", "4144", "4149", "4154"],
    ]
    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )
    assert signal is None


def test_public_google_sheet_url_is_converted_to_csv() -> None:
    csv_url = GoogleSheetsService.public_csv_url(
        "https://docs.google.com/spreadsheets/d/e/example/pubhtml",
        gid="0",
    )
    assert csv_url == (
        "https://docs.google.com/spreadsheets/d/e/example/"
        "pub?gid=0&single=true&output=csv"
    )


def test_latest_sheet_analysis_sell_uses_low_target_and_high_stop() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-06"],
        [],
        ["Time", "High", "Low", "Previous AVG", "AVG", "Live CMP"],
        [],
        [],
        [
            "14:30 - 15:30",
            "4150",
            "4138",
            "4144",
            "4145",
            "4146",
        ],
        [
            "15:30 - 16:30",
            "4155",
            "4142",
            "4145",
            "4149",
            "4144",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 11, 10, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "SELL"
    assert signal.reference_price == Decimal("4149")
    assert signal.target_price == Decimal("4142")
    assert signal.stop_loss == Decimal("4150")

def test_sheet_analysis_reads_six_directional_targets() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-06"],
        [],
        [
            "Time",
            "High",
            "Low",
            "Previous AVG",
            "AVG",
            "Live CMP",
            "",
            "Target",
            "BUY Level",
            "SELL Level",
            "Label",
            "No.",
            "Step",
        ],
        [
            "03:30 AM TO 04:30 AM",
            "4081",
            "4071",
            "4076",
            "4078",
            "4080",
            "",
            "Target 1",
            "4039.09",
            "4058.98",
            "Target 1",
            "1",
            "17.25",
        ],
        [
            "04:30 AM TO 05:30 AM",
            "4080",
            "4069",
            "4078",
            "4076",
            "4077",
            "",
            "Target 2",
            "4056.34",
            "4041.73",
            "Target 2",
            "2",
            "17.25",
        ],
        [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Target 3",
            "4073.59",
            "4024.48",
            "Target 3",
            "3",
            "17.25",
        ],
        [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Target 4",
            "4090.84",
            "4007.23",
            "Target 4",
            "4",
            "17.25",
        ],
        [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Target 5",
            "4108.09",
            "3989.98",
            "Target 5",
            "5",
            "17.25",
        ],
        [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Target 6",
            "4125.34",
            "3972.73",
            "Target 6",
            "6",
            "17.25",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 4, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4076")
    assert signal.stop_loss == Decimal("4071")
    assert signal.targets == (
        Decimal("4090.84"),
        Decimal("4108.09"),
        Decimal("4125.34"),
    )
    assert signal.target_price == Decimal("4090.84")

def test_sheet_uses_morning_target_table() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-06"],
        ["", "", "", "", "", "", "", "MORNING TARGETS"],
        ["", "", "", "", "", "", "", "Target 1", "4101", "4091"],
        ["", "", "", "", "", "", "", "Target 2", "4102", "4090"],
        ["", "", "", "", "", "", "", "EVENING TARGETS"],
        ["", "", "", "", "", "", "", "Target 1", "4201", "4191"],
        ["", "", "", "", "", "", "", "Target 2", "4202", "4190"],
        [
            "08:30 AM TO 09:30 AM",
            "4102", "4085", "4090", "4095", "4094",
        ],
        [
            "09:30 AM TO 10:30 AM",
            "4100", "4080", "4095", "4092", "4095",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 4, 30, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4092")
    assert signal.stop_loss == Decimal("4085")
    assert signal.targets == (Decimal("4101"), Decimal("4102"))


def test_sheet_uses_evening_target_table() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-06"],
        ["", "", "", "", "", "", "", "MORNING TARGETS"],
        ["", "", "", "", "", "", "", "Target 1", "4101", "4091"],
        ["", "", "", "", "", "", "", "EVENING TARGETS"],
        ["", "", "", "", "", "", "", "Target 1", "4201", "4191"],
        ["", "", "", "", "", "", "", "Target 2", "4202", "4190"],
        [
            "03:30 PM TO 04:30 PM",
            "4195", "4180", "4185", "4188", "4190",
        ],
        [
            "04:30 PM TO 05:30 PM",
            "4200", "4182", "4188", "4192", "4195",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "SELL"
    assert signal.reference_price == Decimal("4192")
    assert signal.stop_loss == Decimal("4195")
    assert signal.targets == (Decimal("4191"), Decimal("4190"))


def test_sheet_transition_gap_creates_no_signal() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-06"],
        ["", "", "", "", "", "", "", "MORNING TARGETS"],
        ["", "", "", "", "", "", "", "Target 1", "4101", "4091"],
        ["03:00 PM TO 03:30 PM", "4100", "4080", "4090", "4092", "4095"],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 9, 35, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is None



def test_lower_low_lower_average_creates_buy_at_average() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-29"],
        [
            "Time", "High", "Low", "Previous AVG",
            "AVG", "Live CMP", "", "Target",
            "BUY Level", "SELL Level",
        ],
        [
            "05:30 AM TO 06:30 AM",
            "4027.55", "4018.00", "4020.90",
            "4022.78", "4021.77", "",
            "Target 1", "4029.21", "4034.84",
        ],
        [
            "06:30 AM TO 07:30 AM",
            "4029.66", "4009.79", "4022.78",
            "4019.73", "4025.38", "",
            "Target 2", "4038.70", "4025.35",
        ],
        ["", "", "", "", "", "", "", "Target 3", "4048.19", "4015.86"],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 29, 2, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4019.73")
    assert signal.stop_loss == Decimal("4018.00")
    assert signal.targets == (
        Decimal("4029.21"),
        Decimal("4038.70"),
        Decimal("4048.19"),
    )


def test_higher_high_higher_average_creates_sell_at_average() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-29"],
        [
            "Time", "High", "Low", "Previous AVG",
            "AVG", "Live CMP", "", "Target",
            "BUY Level", "SELL Level",
        ],
        [
            "10:30 AM TO 11:30 AM",
            "4039.10", "4026.39", "4024.67",
            "4032.75", "4035.74", "",
            "Target 1", "4050", "4025",
        ],
        [
            "11:30 AM TO 12:30 PM",
            "4044.16", "4033.02", "4032.75",
            "4038.59", "4041.94", "",
            "Target 2", "4060", "4015",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 29, 6, 40, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "SELL"
    assert signal.reference_price == Decimal("4038.59")
    assert signal.stop_loss == Decimal("4039.10")
    assert signal.targets == (
        Decimal("4025"),
        Decimal("4015"),
    )


def test_unlabelled_first_target_block_is_morning_table() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-29"],
        [
            "Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP", "",
            "Target", "BUY Level", "SELL Level", "Label", "No.", "Step",
        ],
        [
            "03:30 AM TO 04:30 AM",
            "4029.33", "4013.94", "", "4021.64", "4019.85", "",
            "Target 1", "4029.21", "4034.84", "Target 1", "1", "9.49",
        ],
        [
            "04:30 AM TO 05:30 AM",
            "4026.25", "4015.54", "4021.64", "4020.90", "4026.10", "",
            "Target 2", "4038.70", "4025.35", "Target 2", "2", "9.49",
        ],
        [
            "05:30 AM TO 06:30 AM",
            "4027.55", "4018.00", "4020.90", "4022.78", "4021.77", "",
            "Target 3", "4048.19", "4015.86", "Target 3", "3", "9.49",
        ],
        [
            "06:30 AM TO 07:30 AM",
            "4029.66", "4009.79", "4022.78", "4019.73", "4025.38", "",
            "Target 4", "4057.68", "4006.37", "Target 4", "4", "9.49",
        ],
        ["", "", "", "", "", "", "", "Target 5", "4067.17", "3996.88"],
        ["", "", "", "", "", "", "", "Target 6", "4076.66", "3987.39"],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 29, 2, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4019.73")
    assert signal.targets == (
        Decimal("4029.21"),
        Decimal("4038.70"),
        Decimal("4048.19"),
        Decimal("4057.68"),
        Decimal("4067.17"),
        Decimal("4076.66"),
    )


def test_unlabelled_second_target_block_is_evening_table() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-29"],
        [
            "Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP", "",
            "Target", "BUY Level", "SELL Level", "Label", "No.", "Step",
        ],
        ["", "", "", "", "", "", "", "Target 1", "4029.21", "4034.84"],
        ["", "", "", "", "", "", "", "Target 2", "4038.70", "4025.35"],
        ["", "", "", "", "", "", "", "Target 3", "4048.19", "4015.86"],
        ["", "", "", "", "", "", "", "Target 4", "4057.68", "4006.37"],
        ["", "", "", "", "", "", "", "Target 5", "4067.17", "3996.88"],
        ["", "", "", "", "", "", "", "Target 6", "4076.66", "3987.39"],
        [],
        [
            "", "", "", "", "", "", "",
            "Target", "BUY Level", "SELL Level", "Label", "No.", "Step",
        ],
        ["", "", "", "", "", "", "", "Target 1", "4060", "4040"],
        ["", "", "", "", "", "", "", "Target 2", "4070", "4030"],
        ["", "", "", "", "", "", "", "Target 3", "4080", "4020"],
        ["", "", "", "", "", "", "", "Target 4", "4090", "4010"],
        ["", "", "", "", "", "", "", "Target 5", "4100", "4000"],
        ["", "", "", "", "", "", "", "Target 6", "4110", "3990"],
        [
            "03:30 PM TO 04:30 PM",
            "4050", "4038", "4042", "4045", "4046",
        ],
        [
            "04:30 PM TO 05:30 PM",
            "4055", "4040", "4045", "4048", "4049",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 29, 11, 30, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "SELL"
    assert signal.reference_price == Decimal("4048")
    assert signal.stop_loss == Decimal("4050")
    assert signal.targets == (
        Decimal("4040"),
        Decimal("4030"),
        Decimal("4020"),
        Decimal("4010"),
        Decimal("4000"),
        Decimal("3990"),
    )


def test_unlabelled_double_table_keeps_first_block_for_morning() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-29"],
        [
            "Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP", "",
            "Target", "BUY Level", "SELL Level", "Label", "No.", "Step",
        ],
        ["", "", "", "", "", "", "", "Target 1", "4029.21", "4034.84"],
        ["", "", "", "", "", "", "", "Target 2", "4038.70", "4025.35"],
        ["", "", "", "", "", "", "", "Target 3", "4048.19", "4015.86"],
        ["", "", "", "", "", "", "", "Target 4", "4057.68", "4006.37"],
        ["", "", "", "", "", "", "", "Target 5", "4067.17", "3996.88"],
        ["", "", "", "", "", "", "", "Target 6", "4076.66", "3987.39"],
        [],
        [
            "", "", "", "", "", "", "",
            "Target", "BUY Level", "SELL Level", "Label", "No.", "Step",
        ],
        ["", "", "", "", "", "", "", "Target 1", "4160", "4140"],
        ["", "", "", "", "", "", "", "Target 2", "4170", "4130"],
        ["", "", "", "", "", "", "", "Target 3", "4180", "4120"],
        ["", "", "", "", "", "", "", "Target 4", "4190", "4110"],
        ["", "", "", "", "", "", "", "Target 5", "4200", "4100"],
        ["", "", "", "", "", "", "", "Target 6", "4210", "4090"],
        [
            "05:30 AM TO 06:30 AM",
            "4027.55", "4018.00", "4020.90", "4022.78", "4021.77",
        ],
        [
            "06:30 AM TO 07:30 AM",
            "4029.66", "4009.79", "4022.78", "4019.73", "4025.38",
        ],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 29, 2, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == Decimal("4019.73")
    assert signal.targets == (
        Decimal("4029.21"),
        Decimal("4038.70"),
        Decimal("4048.19"),
        Decimal("4057.68"),
        Decimal("4067.17"),
        Decimal("4076.66"),
    )


def test_real_evening_rows_do_not_sell_the_lower_low_row() -> None:
    values = [
        ["XAUUSD SESSION 2026-07-29"],
        [
            "Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP", "",
            "Target", "BUY Level", "SELL Level",
        ],
        [
            "01:30 PM TO 02:30 PM",
            "4044.23", "4035.79", "4044.33", "4040.01", "4037.92", "",
            "Target 1", "4029.21", "4034.84",
        ],
        [
            "02:30 PM TO 03:30 PM",
            "4038.27", "4031.24", "4040.01", "4034.76", "4033.11", "",
            "Target 2", "4038.70", "4025.35",
        ],
        [
            "03:30 PM TO 04:30 PM",
            "4034.21", "4025.93", "4034.76", "4030.07", "4027.02", "",
            "Target 3", "4048.19", "4015.86",
        ],
        [
            "04:30 PM TO 05:30 PM",
            "4035.80", "4025.44", "4030.07", "4030.62", "4031.44", "",
            "Target 4", "4057.68", "4006.37",
        ],
        ["", "", "", "", "", "", "", "Target 5", "4067.17", "3996.88"],
        ["", "", "", "", "", "", "", "Target 6", "4076.66", "3987.39"],
    ]

    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert signal is not None
    assert signal.direction == "SELL"
    assert signal.reference_price == Decimal("4030.62")
    assert signal.stop_loss == Decimal("4034.21")
    assert "higher high + higher average" in signal.label
    assert signal.reference_price != Decimal("4026.10")


def test_same_session_direction_uses_one_stable_external_key() -> None:
    base = [
        ["XAUUSD SESSION 2026-07-29"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["03:30 AM TO 04:30 AM", "4040", "4030", "4035", "4034", "4033"],
        ["04:30 AM TO 05:30 AM", "4041", "4028", "4034", "4032", "4031"],
    ]

    first = GoogleSheetsService.parse_latest_analysis_signal(
        base,
        now=datetime(2026, 7, 29, 0, 15, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    changed_row = [
        *base,
        ["05:30 AM TO 06:30 AM", "4042", "4025", "4032", "4030", "4029"],
    ]

    second = GoogleSheetsService.parse_latest_analysis_signal(
        changed_row,
        now=datetime(2026, 7, 29, 1, 15, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert first is not None
    assert second is not None
    assert first.direction == "BUY"
    assert second.direction == "BUY"
    assert first.external_key == "gsheet-session:2026-07-29:morning:BUY"
    assert second.external_key == first.external_key


def test_morning_and_evening_use_different_signal_lock_keys() -> None:
    morning_values = [
        ["XAUUSD SESSION 2026-07-29"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["03:30 AM TO 04:30 AM", "4040", "4030", "4035", "4034", "4033"],
        ["04:30 AM TO 05:30 AM", "4041", "4028", "4034", "4032", "4031"],
    ]
    evening_values = [
        ["XAUUSD SESSION 2026-07-29"],
        ["Time", "High", "Low", "Prev AVG", "AVG", "LIVE CMP"],
        ["03:30 PM TO 04:30 PM", "4040", "4030", "4035", "4034", "4033"],
        ["04:30 PM TO 05:30 PM", "4041", "4028", "4034", "4032", "4031"],
    ]

    morning = GoogleSheetsService.parse_latest_analysis_signal(
        morning_values,
        now=datetime(2026, 7, 29, 0, 15, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )
    evening = GoogleSheetsService.parse_latest_analysis_signal(
        evening_values,
        now=datetime(2026, 7, 29, 12, 15, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )

    assert morning is not None
    assert evening is not None
    assert morning.external_key == "gsheet-session:2026-07-29:morning:BUY"
    assert evening.external_key == "gsheet-session:2026-07-29:evening:BUY"
    assert morning.external_key != evening.external_key
