"""Required-input contracts for deterministic Master AI specialist actions."""

from __future__ import annotations

from typing import Any


def _text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def validate_master_ai_action_input(
    action: str,
    payload: dict[str, Any] | None,
) -> str | None:
    """Return a safe missing/invalid input explanation, otherwise ``None``."""
    clean_action = str(action or "").strip().lower()
    data = dict(payload or {})

    if clean_action == "run_market_data_agent":
        missing: list[str] = []
        if not _text(data, "source"):
            missing.append("source")
        if not _text(data, "updated_at", "timestamp"):
            missing.append("timestamp")
        if not _text(data, "price", "last_price"):
            missing.append("price")
        if missing:
            return "Market Data Agent needs verified " + ", ".join(missing) + "."

    elif clean_action == "run_customer_support_agent":
        if not _text(data, "message", "customer_message"):
            return "Customer Support Agent needs the customer message."

    elif clean_action in {"run_marketing_strategy_agent", "run_social_media_agent"}:
        missing = []
        if not _text(data, "article_title", "title"):
            missing.append("published article title")
        if not _text(data, "public_url"):
            missing.append("HTTPS public_url")
        publish_status = _text(data, "publish_status", "status").upper()
        if publish_status != "PUBLISHED":
            missing.append("publish_status=PUBLISHED")
        if missing:
            label = "Marketing Strategy Agent" if clean_action == "run_marketing_strategy_agent" else "Social Media Agent"
            return label + " needs " + ", ".join(missing) + "."

    elif clean_action == "run_cms_editor_agent":
        if not _text(data, "title"):
            return "CMS Editor Agent needs a draft title and optional body_markdown/body content."

    elif clean_action == "run_master_ai_content_review_agent":
        document = data.get("document")
        body = _text(data, "body")
        if not isinstance(document, dict) and not body:
            return "Content Review Agent needs a CMS V2 document or encoded draft body."

    return None
