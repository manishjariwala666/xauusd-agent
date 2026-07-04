"""Safe configuration pre-flight check for local and Streamlit environments."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent
REQUIRED_SECRETS: Final[tuple[str, ...]] = (
    "DATABASE_URL",
    "JWT_SECRET",
    "SUPABASE_URL",
    "SUPABASE_KEY",
)
TELEGRAM_SECRETS: Final[tuple[str, ...]] = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)
GOOGLE_SECRET: Final[str] = "GOOGLE_SERVICE_ACCOUNT_JSON"


def _is_streamlit_runtime() -> bool:
    """Return True only when an active Streamlit script context exists."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx(suppress_warning=True) is not None
    except (ImportError, RuntimeError):
        return False


def _read_secret(name: str) -> str:
    """Read environment/.env first, then active Streamlit Cloud secrets."""
    environment_value = os.getenv(name)
    if environment_value:
        return str(environment_value).strip()

    if not _is_streamlit_runtime():
        return ""

    try:
        import streamlit as st

        streamlit_value = st.secrets.get(name)
    except Exception:
        return ""
    return str(streamlit_value).strip() if streamlit_value else ""


def _enabled(name: str) -> bool:
    """Read an optional boolean test flag without exposing its value."""
    return _read_secret(name).lower() in {"1", "true", "yes", "on"}


def _print_status(name: str, loaded: bool) -> None:
    """Print only a secret name and its safe availability status."""
    print(f"{name}: {'LOADED' if loaded else 'MISSING'}")


def _load_local_env() -> None:
    """Load .env without leaking parser diagnostics or secret contents."""
    dotenv_logger = logging.getLogger("dotenv.main")
    previous_level = dotenv_logger.level
    dotenv_logger.setLevel(logging.ERROR)
    try:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    finally:
        dotenv_logger.setLevel(previous_level)


def main() -> int:
    """Validate required configuration without making external API calls."""
    _load_local_env()

    missing_required: list[str] = []
    for name in REQUIRED_SECRETS:
        loaded = bool(_read_secret(name))
        _print_status(name, loaded)
        if not loaded:
            missing_required.append(name)

    for name in TELEGRAM_SECRETS:
        _print_status(name, bool(_read_secret(name)))

    google_missing = False
    if _enabled("TEST_GOOGLE_CREDENTIALS"):
        google_loaded = bool(_read_secret(GOOGLE_SECRET))
        _print_status(GOOGLE_SECRET, google_loaded)
        google_missing = not google_loaded

    if missing_required or google_missing:
        missing_names = list(missing_required)
        if google_missing:
            missing_names.append(GOOGLE_SECRET)
        print(
            "FAILURE: Required secrets are MISSING: "
            + ", ".join(missing_names)
        )
        return 1

    print("SUCCESS: All required secrets are LOADED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
