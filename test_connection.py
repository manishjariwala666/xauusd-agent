"""Verify Google Sheets, market pricing, Supabase, and Telegram connectivity."""

from __future__ import annotations

from supabase import create_client

from config import (
    ConfigurationError,
    Settings,
    get_settings,
    parse_google_service_account_json,
    validate_google_service_account_credentials,
)
from services.google_sheets import GoogleSheetsService
from services.market_data import MarketDataService
from services.telegram_service import TelegramService


def preflight_check(settings: Settings) -> bool:
    """Validate required configuration before opening network connections."""
    print(
        "Pre-flight: DATABASE_URL loaded: "
        + ("YES" if settings.database_url else "NO")
    )
    print(
        "Pre-flight: SUPABASE_URL loaded: "
        + ("YES" if settings.supabase_url else "NO")
    )

    missing = [
        name
        for name, value in (
            ("DATABASE_URL", settings.database_url),
            ("SUPABASE_URL", settings.supabase_url),
            ("SUPABASE_KEY", settings.supabase_key),
            ("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token),
            ("TELEGRAM_CHAT_ID", settings.telegram_chat_id),
            (
                "GOOGLE_SERVICE_ACCOUNT_JSON",
                settings.google_service_account_json,
            ),
        )
        if not value
    ]
    if missing:
        print(
            "FAILURE: Missing required variable(s): "
            + ", ".join(missing)
        )
        return False

    try:
        parse_google_service_account_json(
            settings.google_service_account_json
        )
        validate_google_service_account_credentials(
            settings.google_service_account_json
        )
    except ConfigurationError as exc:
        if "Invalid JSON format" in str(exc):
            print(
                "FAILURE: Invalid JSON format in .env, "
                "please check your credentials"
            )
        else:
            print(f"FAILURE: {exc}")
        return False

    print("Pre-flight: Google service account JSON: VALID")
    return True


def main() -> int:
    """Send one real TEST SIGNAL enriched from the configured Google Sheet."""
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        if "Invalid JSON format" in str(exc):
            print(
                "FAILURE: Invalid JSON format in .env, "
                "please check your credentials"
            )
        else:
            print(f"FAILURE: Configuration error — {exc}")
        return 1
    except Exception as exc:
        print(f"FAILURE: Unable to load configuration — {exc}")
        return 1

    if not preflight_check(settings):
        return 1

    try:
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_key,
        )

        sheet_signal = GoogleSheetsService().get_latest_signal()
        if sheet_signal is None:
            print(
                "FAILURE: Google Sheets connection succeeded, but no BUY or "
                "SELL row was found."
            )
            return 1

        market_price = MarketDataService(supabase).fetch_current_price()
        if market_price is None:
            print("FAILURE: Current XAUUSD price could not be fetched.")
            return 1

        test_signal = {
            "signal_type": sheet_signal.direction,
            "price": float(market_price.price),
            "target_price": (
                float(sheet_signal.target_price)
                if sheet_signal.target_price is not None
                else None
            ),
            "stop_loss": (
                float(sheet_signal.stop_loss)
                if sheet_signal.stop_loss is not None
                else None
            ),
            "sheet_label": f"TEST SIGNAL · {sheet_signal.label}",
            "source": market_price.source,
            "signal_time": market_price.observed_at.isoformat(),
        }

        delivered = TelegramService(supabase).send_test_signal(test_signal)
        if not delivered:
            print(
                "FAILURE: Telegram rejected the test signal. Verify "
                "TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and bot channel "
                "permissions."
            )
            return 1
    except Exception as exc:
        print(
            f"FAILURE: {type(exc).__name__} — {exc}. "
            "Check the related credential and service configuration."
        )
        return 1

    print(
        "SUCCESS: Google Sheets data and current market price were loaded, "
        "and the TEST SIGNAL was delivered to Telegram."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
