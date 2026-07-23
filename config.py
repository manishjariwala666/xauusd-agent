"""Application configuration loaded exclusively from environment/secrets."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import streamlit as st


_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)
LOGGER = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when required production configuration is unavailable."""


_GOOGLE_REQUIRED_FIELDS = {
    "type",
    "project_id",
    "private_key",
    "client_email",
    "token_uri",
}


def _is_streamlit_runtime() -> bool:
    """Return whether code is executing inside a Streamlit script context."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx(suppress_warning=True) is not None
    except (ImportError, RuntimeError):
        return False


def _read_secret(name: str, default: str = "") -> str:
    """Read system/.env values first, then Streamlit Secrets on Cloud."""
    environment_value = os.getenv(name)
    if environment_value:
        return str(environment_value).strip()

    if _is_streamlit_runtime():
        try:
            streamlit_value = st.secrets.get(name)
        except Exception:
            streamlit_value = None
        if streamlit_value:
            return str(streamlit_value).strip()

    return str(default).strip()


def _read_bool_secret(name: str, default: bool = False) -> bool:
    """Read one feature flag from environment/secrets using common truthy values."""
    fallback = "true" if default else "false"
    return _read_secret(name, fallback).lower() in {"1", "true", "yes", "on"}


def _compact_secret_token(value: str) -> str:
    """Remove accidental pasted whitespace from opaque API/bot tokens."""
    return "".join(str(value or "").split())


def parse_google_service_account_json(raw_value: str) -> dict[str, Any]:
    """Parse and validate Google credentials without exposing their contents."""
    if not raw_value.strip():
        raise ConfigurationError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not configured."
        )

    try:
        credentials: Any = json.loads(raw_value)
        # Some deployment systems store the complete JSON document as a
        # JSON-encoded string. Decode that representation one additional time.
        if isinstance(credentials, str):
            credentials = json.loads(credentials)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ConfigurationError(
            "Invalid JSON format in .env, please check your credentials"
        ) from exc

    if not isinstance(credentials, dict):
        raise ConfigurationError(
            "Invalid JSON format in .env, please check your credentials"
        )

    missing_fields = sorted(
        field
        for field in _GOOGLE_REQUIRED_FIELDS
        if not credentials.get(field)
    )
    if missing_fields:
        raise ConfigurationError(
            "Google service account JSON is missing required field(s): "
            + ", ".join(missing_fields)
        )

    private_key = str(credentials["private_key"]).replace("\\n", "\n").strip()
    if not (
        private_key.startswith("-----BEGIN PRIVATE KEY-----")
        and private_key.endswith("-----END PRIVATE KEY-----")
    ):
        raise ConfigurationError(
            "Google service account private_key is not valid PEM data."
        )

    credentials["private_key"] = private_key + "\n"
    return credentials


def normalize_google_service_account_json(raw_value: str) -> str:
    """Return one-line canonical JSON suitable for downstream libraries."""
    credentials = parse_google_service_account_json(raw_value)
    return json.dumps(credentials, separators=(",", ":"))


def validate_google_service_account_credentials(raw_value: str) -> None:
    """Validate that the service-account private key can be loaded."""
    credentials = parse_google_service_account_json(raw_value)
    try:
        from google.oauth2.service_account import Credentials

        Credentials.from_service_account_info(
            credentials,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            "Google service account private_key could not be loaded. "
            "Keep the JSON on one line and preserve escaped \\n characters."
        ) from exc


@dataclass(frozen=True)
class Settings:
    """Validated runtime settings for database, authentication, and email."""

    database_url: str
    supabase_url: str
    supabase_key: str
    jwt_secret: str
    jwt_issuer: str
    jwt_ttl_minutes: int
    app_base_url: str
    backend_base_url: str
    public_api_url: str
    public_website_url: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    email_from: str
    smtp_use_tls: bool
    google_oauth_login_url: str
    telegram_invite_url: str
    support_whatsapp_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    master_ai_telegram_bot_token: str
    telegram_admin_user_id: str
    telegram_admin_user_ids: str
    master_ai_allow_natural_commands: bool
    google_service_account_json: str
    google_sheet_id: str
    google_sheet_name: str
    google_worksheet_name: str
    google_sheet_public_url: str
    goldapi_key: str
    xauusd_symbol: str
    signal_poll_seconds: int
    usdt_wallet_address: str
    usdt_network: str
    subscription_price_usdt: str
    profit_proof_telegram_url: str
    support_email: str
    brand_name: str
    ai_provider: str
    gemini_api_key: str
    openai_api_key: str
    ai_text_model: str
    ai_image_model: str
    telegram_webhook_secret: str
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_verify_token: str
    meta_app_secret: str
    green_api_instance_id: str
    green_api_token: str
    green_api_chat_id: str
    human_takeover_minutes: int
    worker_poll_seconds: int
    block_search_indexing: bool
    admin_bff_shared_secret: str
    admin_session_ttl_minutes: int
    admin_login_window_seconds: int
    admin_login_max_attempts: int

    @classmethod
    def load(cls) -> "Settings":
        database_url = _read_secret("DATABASE_URL")
        supabase_url = _read_secret("SUPABASE_URL")
        supabase_key = _read_secret("SUPABASE_KEY")
        jwt_secret = _read_secret("JWT_SECRET")

        missing = [
            name
            for name, value in (
                ("DATABASE_URL", database_url),
                ("SUPABASE_URL", supabase_url),
                ("SUPABASE_KEY", supabase_key),
                ("JWT_SECRET", jwt_secret),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "Missing required configuration: " + ", ".join(missing)
            )
        if len(jwt_secret) < 32:
            raise ConfigurationError(
                "JWT_SECRET must contain at least 32 characters."
            )

        raw_google_credentials = _read_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
        google_credentials = ""
        if raw_google_credentials:
            try:
                google_credentials = normalize_google_service_account_json(
                    raw_google_credentials
                )
            except ConfigurationError:
                LOGGER.warning(
                    "Google Sheets integration disabled: "
                    "GOOGLE_SERVICE_ACCOUNT_JSON is missing required fields "
                    "or is not valid service-account JSON."
                )

        app_base_url = _read_secret("APP_BASE_URL")
        backend_base_url = _read_secret("BACKEND_BASE_URL")
        public_api_url = _read_secret("PUBLIC_API_URL") or backend_base_url
        public_website_url = (
            _read_secret("PUBLIC_WEBSITE_URL")
            or _read_secret("PUBLIC_SITE_URL")
            or _read_secret("STREAMLIT_PUBLIC_URL")
            or app_base_url
        )

        return cls(
            database_url=database_url,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            jwt_secret=jwt_secret,
            jwt_issuer=_read_secret("JWT_ISSUER", "ai-market-analytics-pro"),
            jwt_ttl_minutes=int(_read_secret("JWT_TTL_MINUTES", "60")),
            app_base_url=app_base_url,
            backend_base_url=backend_base_url,
            public_api_url=public_api_url,
            public_website_url=public_website_url,
            smtp_host=_read_secret("SMTP_HOST"),
            smtp_port=int(_read_secret("SMTP_PORT", "587")),
            smtp_username=_read_secret("SMTP_USERNAME"),
            smtp_password=_read_secret("SMTP_PASSWORD"),
            email_from=_read_secret("EMAIL_FROM"),
            smtp_use_tls=_read_secret("SMTP_USE_TLS", "true").lower()
            in {"1", "true", "yes", "on"},
            google_oauth_login_url=_read_secret("GOOGLE_OAUTH_LOGIN_URL"),
            telegram_invite_url=_read_secret("TELEGRAM_INVITE_URL"),
            support_whatsapp_url=_read_secret("SUPPORT_WHATSAPP_URL"),
            telegram_bot_token=_compact_secret_token(
                _read_secret("TELEGRAM_BOT_TOKEN")
            ),
            telegram_chat_id=_read_secret("TELEGRAM_CHAT_ID"),
            master_ai_telegram_bot_token=_compact_secret_token(
                _read_secret("MASTER_AI_TELEGRAM_BOT_TOKEN")
            ),
            telegram_admin_user_id=_read_secret("TELEGRAM_ADMIN_USER_ID"),
            telegram_admin_user_ids=_read_secret("TELEGRAM_ADMIN_USER_IDS"),
            master_ai_allow_natural_commands=_read_secret(
                "MASTER_AI_ALLOW_NATURAL_COMMANDS",
                "false",
            ).lower()
            in {"1", "true", "yes", "on"},
            google_service_account_json=google_credentials,
            google_sheet_id=_read_secret("GOOGLE_SHEET_ID"),
            google_sheet_name=_read_secret(
                "GOOGLE_SHEET_NAME",
                "xauusd_automation",
            ),
            google_worksheet_name=_read_secret(
                "GOOGLE_WORKSHEET_NAME",
                "Sheet1",
            ),
            google_sheet_public_url=_read_secret(
                "GOOGLE_SHEET_PUBLIC_URL"
            ),
            goldapi_key=_read_secret("GOLDAPI_KEY"),
            xauusd_symbol=_read_secret("XAUUSD_SYMBOL", "GC=F"),
            signal_poll_seconds=max(
                10,
                int(_read_secret("SIGNAL_POLL_SECONDS", "60")),
            ),
            usdt_wallet_address=_read_secret("USDT_WALLET_ADDRESS"),
            usdt_network=_read_secret("USDT_NETWORK"),
            subscription_price_usdt=_read_secret(
                "SUBSCRIPTION_PRICE_USDT"
            ),
            profit_proof_telegram_url=_read_secret(
                "PROFIT_PROOF_TELEGRAM_URL"
            ),
            support_email=_read_secret("SUPPORT_EMAIL"),
            brand_name=_read_secret(
                "BRAND_NAME",
                "AI Market Analytics Pro",
            ),
            ai_provider=_read_secret("AI_PROVIDER", "GEMINI").upper(),
            gemini_api_key=_read_secret("GEMINI_API_KEY"),
            openai_api_key=_read_secret("OPENAI_API_KEY"),
            ai_text_model=_read_secret(
                "AI_TEXT_MODEL",
                "gemini-2.5-flash",
            ),
            ai_image_model=_read_secret(
                "AI_IMAGE_MODEL",
                "gpt-image-1",
            ),
            telegram_webhook_secret=_read_secret(
                "TELEGRAM_WEBHOOK_SECRET"
            ),
            whatsapp_access_token=_read_secret(
                "WHATSAPP_ACCESS_TOKEN"
            ),
            whatsapp_phone_number_id=_read_secret(
                "WHATSAPP_PHONE_NUMBER_ID"
            ),
            whatsapp_business_account_id=_read_secret(
                "WHATSAPP_BUSINESS_ACCOUNT_ID"
            ),
            whatsapp_verify_token=_read_secret("WHATSAPP_VERIFY_TOKEN"),
            meta_app_secret=_read_secret("META_APP_SECRET"),
            green_api_instance_id=_read_secret("GREEN_API_INSTANCE_ID"),
            green_api_token=_read_secret("GREEN_API_TOKEN"),
            green_api_chat_id=_read_secret("GREEN_API_CHAT_ID"),
            human_takeover_minutes=max(
                1,
                int(_read_secret("HUMAN_TAKEOVER_MINUTES", "30")),
            ),
            worker_poll_seconds=max(
                1,
                int(_read_secret("WORKER_POLL_SECONDS", "5")),
            ),
            block_search_indexing=_read_bool_secret(
                "BLOCK_SEARCH_INDEXING",
                False,
            ),
            admin_bff_shared_secret=_read_secret("ADMIN_BFF_SHARED_SECRET"),
            admin_session_ttl_minutes=max(
                5,
                min(30, int(_read_secret("ADMIN_SESSION_TTL_MINUTES", "15"))),
            ),
            admin_login_window_seconds=max(
                60,
                int(_read_secret("ADMIN_LOGIN_WINDOW_SECONDS", "900")),
            ),
            admin_login_max_attempts=max(
                3,
                min(20, int(_read_secret("ADMIN_LOGIN_MAX_ATTEMPTS", "5"))),
            ),
        )


def _load_settings() -> Settings:
    """Load and validate settings without framework-specific caching."""
    return Settings.load()


if _is_streamlit_runtime():
    _settings_provider = st.cache_resource(_load_settings)
else:
    _settings_provider = _load_settings


def get_settings() -> Settings:
    """Return cached Cloud settings or direct terminal settings."""
    return _settings_provider()
