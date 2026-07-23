"""Safe conversational brain for the private Telegram Master AI bot."""

from __future__ import annotations

import os
from typing import Any

import httpx

SAFE_CHAT_ERROR = "⚠️ Master AI abhi response nahi de pa raha. Thodi der baad try karein."

SYSTEM_INSTRUCTIONS = """
You are VenusRealm Master AI, a private assistant for the authorized administrator.

Reply in clear Hinglish unless the user asks for another language.
Be concise, practical, and honest.

VenusRealm business context:
- VenusRealm is an AI-powered XAUUSD, market-content, automation, and client-service platform.
- Current priorities are website stability, reliable Telegram and WhatsApp delivery, Google Sheets integration, useful admin controls, and safe launch preparation.
- The administrator prefers one focused task at a time, no unnecessary audits, no repeated builds, and no production changes without explicit approval.
- When asked about VenusRealm priorities, give project-specific advice instead of generic startup advice.
- Clearly separate current known status, risks, and the next practical action.
- Do not pretend to have live business data unless it is present in the message or connected system.

Safety rules:
- Never execute trades.
- Never publish signals or content automatically.
- Never modify Railway, DNS, databases, production, secrets, schedulers, or agents.
- Never claim guaranteed profits.
- Never expose credentials or internal secrets.
- For production-changing requests, explain that explicit approval is required.
"""


def _extract_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    parts: list[str] = []

    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue

        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue

            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

    return "\n".join(parts).strip()


def _generate_gemini_reply(message: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"

    if not api_key:
        return ""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=f"{SYSTEM_INSTRUCTIONS.strip()}\n\nUser message:\n{message}",
        )
        answer = str(getattr(response, "text", "") or "").strip()
        return answer
    except Exception as exc:
        print(f"[master-ai-chat] Gemini error type={type(exc).__name__}")
        return ""


def generate_master_ai_reply(message: str) -> str:
    """Generate one safe reply with OpenAI primary and Gemini fallback."""
    clean_message = str(message or "").strip()

    if not clean_message:
        return "Apna message likhiye."

    if len(clean_message) > 4000:
        return "Message bahut lamba hai. Kripya 4000 characters ke andar bhejein."

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5").strip() or "gpt-5"

    if not api_key:
        return "⚠️ Master AI API key configure nahi hai."

    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "instructions": SYSTEM_INSTRUCTIONS.strip(),
                    "input": clean_message,
                    "store": False,
                },
            )

            response.raise_for_status()
            answer = _extract_output_text(response.json())

            return answer or SAFE_CHAT_ERROR
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        request_id = exc.response.headers.get("x-request-id", "unknown")
        print(
            f"[master-ai-chat] OpenAI HTTP error status={status_code} "
            f"request_id={request_id}"
        )
        return _generate_gemini_reply(clean_message) or SAFE_CHAT_ERROR
    except httpx.RequestError as exc:
        print(f"[master-ai-chat] OpenAI network error type={type(exc).__name__}")
        return _generate_gemini_reply(clean_message) or SAFE_CHAT_ERROR
    except Exception as exc:
        print(f"[master-ai-chat] Unexpected error type={type(exc).__name__}")
        return _generate_gemini_reply(clean_message) or SAFE_CHAT_ERROR
