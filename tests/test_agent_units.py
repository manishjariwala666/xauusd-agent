"""Offline tests for deterministic production-agent behavior."""

from datetime import datetime, timedelta, timezone
import warnings

warnings.filterwarnings(
    "ignore",
    message="'_UnionGenericAlias' is deprecated.*",
    category=DeprecationWarning,
)

from services.google_sheets import GoogleSheetsService
from services.production_agents import (
    _fallback_blog_payload,
    _seo_issues,
    _slugify,
    run_image_agent,
)
from services.telegram_service import TelegramService
from backend import _is_telegram_command
from services.conversation_service import (
    _extract_blog_topic,
    _is_blog_only_command,
    _requests_image,
)


def test_all_production_agent_runners_exist() -> None:
    from services.production_agents import RUNNERS

    assert set(RUNNERS) == {
        "ai_blog_agent",
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
    assert isinstance(payload["schema_jsonld"], dict)


def test_master_ai_blog_publish_default_uses_payload_override(monkeypatch) -> None:
    from services.production_agents import _blog_publish_default

    monkeypatch.setattr(
        "services.production_agents.get_site_setting",
        lambda _: "draft",
    )

    assert _blog_publish_default({"publish": True})
    assert not _blog_publish_default({"publish": False})
    assert not _blog_publish_default({})


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
        ["14:30 - 15:30", "4160", "4136", "4156", "4148", "4144"],
        ["15:30 - 16:30", "4155", "4142", "4144", "4149", "4154"],
    ]
    signal = GoogleSheetsService.parse_latest_analysis_signal(
        values,
        now=datetime(2026, 7, 6, 11, 10, tzinfo=timezone.utc),
        max_age=timedelta(hours=6),
    )
    assert signal is not None
    assert signal.direction == "BUY"
    assert signal.reference_price == 4154
    assert signal.target_price == 4155
    assert signal.stop_loss == 4142


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
