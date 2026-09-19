"""DB-independent GitHub fallback for four daily WhatsApp session setups."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from supabase import create_client

from services.google_sheets import GoogleSheetsService
from services.session_signal_broadcast import (
    format_session_setup_message,
    load_due_session_setups,
)
from services.whatsapp_service import WhatsAppService


def _recipient() -> str:
    value = str(os.getenv("GREEN_API_CHAT_ID") or "").strip()
    if not value:
        raise RuntimeError("GREEN_API_CHAT_ID is not configured.")
    return value


def _dedupe_key(
    signal_date: str,
    session_name: str,
    direction: str,
    recipient: str,
) -> str:
    recipient_hash = hashlib.sha256(recipient.encode("utf-8")).hexdigest()[:16]
    return (
        "wa_session_setup:"
        f"{signal_date}:{session_name}:{direction}:{recipient_hash}"
    )


def _claim(client: Any, key: str) -> str | None:
    claim_token = f"CLAIMED:{uuid.uuid4()}"
    client.table("site_settings").upsert(
        {
            "setting_key": key,
            "setting_value": claim_token,
            "is_sensitive": True,
        },
        on_conflict="setting_key",
        ignore_duplicates=True,
    ).execute()

    response = (
        client.table("site_settings")
        .select("setting_value")
        .eq("setting_key", key)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    value = str(rows[0].get("setting_value") or "")
    if value.startswith("SENT:"):
        return None
    return claim_token if value == claim_token else None


def _mark(client: Any, key: str, value: str) -> None:
    client.table("site_settings").upsert(
        {
            "setting_key": key,
            "setting_value": value[:1000],
            "is_sensitive": True,
        },
        on_conflict="setting_key",
    ).execute()


def run() -> tuple[int, int]:
    """Send due session setup messages without requiring DATABASE_URL."""
    supabase_url = str(os.getenv("SUPABASE_URL") or "").strip()
    supabase_key = str(os.getenv("SUPABASE_KEY") or "").strip()
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required.")

    sheets = GoogleSheetsService()
    setups = load_due_session_setups(sheets, now=datetime.now(timezone.utc))
    if not setups:
        print("DUE_SESSION_SETUPS=0")
        return 0, 0

    recipient = _recipient()
    client = create_client(supabase_url, supabase_key)
    service = WhatsAppService()

    delivered = 0
    failed = 0
    for setup in setups:
        key = _dedupe_key(
            setup.signal_date,
            setup.session_name,
            setup.direction,
            recipient,
        )
        claim_token = _claim(client, key)
        if claim_token is None:
            continue
        try:
            message_id = service.send_text(
                recipient,
                format_session_setup_message(setup),
            )
            _mark(client, key, f"SENT:{message_id}")
            delivered += 1
        except Exception as exc:
            _mark(client, key, f"FAILED:{exc.__class__.__name__}")
            failed += 1

    print(f"DELIVERED={delivered}")
    print(f"FAILED={failed}")
    return delivered, failed


if __name__ == "__main__":
    delivered, failed = run()
    if failed:
        raise SystemExit(1)
