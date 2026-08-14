"""Safe conversational brain for the private Telegram Master AI bot."""

from __future__ import annotations

import os
from typing import Any

import httpx

from services.ai_agents.macro_ai.provider import load_macro_assessment
from services.master_ai_router import route_master_ai_request
from services.master_ai_intelligence_orchestrator import (
    IntelligenceDecision,
    MarketReference,
    format_intelligence_response,
    synthesize_intelligence,
)
from services.master_ai_signal_reader import (
    MasterAISignalSnapshot,
    get_today_signal_snapshot,
)

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

Safety and operating rules:
- Never execute trades.
- Never invent signal values or claim guaranteed profits.
- Never expose credentials, secrets, private tokens, or raw tracebacks.
- You may explain and diagnose registered VenusRealm agent actions using the exact
  action status, run ID, safe error reason, and context supplied in the message.
- Registered safe tools may be executed only by the Telegram action controller,
  not by pretending that a conversational reply performed an action.
- Read-only diagnostics and safe retries of registered agents are allowed when
  the administrator explicitly asks.
- Publishing, Railway changes, DNS changes, database migrations, secret changes,
  destructive operations, and real external delivery require the applicable
  approval gate.
- When an action failed, do not ask the administrator to repeat information that
  is already present. Explain the exact safe failure reason and the next repair.
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


def _format_market_snapshot(
    snapshot: MasterAISignalSnapshot | None,
) -> str:
    """Format verified read-only Sheet1 market data for admin chat."""
    if snapshot is None:
        return (
            "Aaj ka XAUUSD Google Sheet snapshot available nahi hai. "
            "Main current price guess nahi karunga. Sheet1 ka DATE block "
            "aur LIVE CMP value verify kijiye."
        )

    if snapshot.live_cmp is None:
        return (
            f"XAUUSD Sheet snapshot {snapshot.signal_date.isoformat()} ke "
            "liye mila, lekin LIVE CMP available nahi hai. Main missing "
            "price invent nahi karunga."
        )

    def value(item: object) -> str:
        return str(item) if item is not None else "N/A"

    return "\n".join(
        (
            "📊 XAUUSD — Google Sheet Reference",
            f"Current Price: {snapshot.live_cmp}",
            f"Date: {snapshot.signal_date.isoformat()}",
            f"Latest Slot: {snapshot.latest_slot or 'N/A'}",
            f"Day High: {value(snapshot.day_high)}",
            f"Day Low: {value(snapshot.day_low)}",
            f"Source: {snapshot.source} / Sheet1",
            "",
            "Read-only reference data.",
            "Koi buy/sell signal, trade recommendation ya execution nahi hua.",
        )
    )


def _market_data_reply() -> str:
    """Read today's verified Sheet1 snapshot with safe stale fallback."""
    try:
        snapshot = get_today_signal_snapshot()
    except Exception as exc:
        print(
            "[master-ai-chat] Market snapshot error "
            f"type={type(exc).__name__}"
        )
        return (
            "Google Sheet market-data reader temporarily unavailable hai. "
            "Main XAUUSD price guess nahi karunga. Sheet configuration aur "
            "Sheet1 access verify kijiye."
        )

    if snapshot is not None and snapshot.live_cmp is not None:
        return _format_market_snapshot(snapshot)

    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        from services.master_ai_signal_reader import (
            get_signal_snapshot_for_date,
        )

        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

        for days_back in range(1, 4):
            candidate_date = today - timedelta(days=days_back)
            candidate = get_signal_snapshot_for_date(candidate_date)

            if candidate is None or candidate.live_cmp is None:
                continue

            return "\n".join(
                [
                    "Latest available XAUUSD Sheet reference:",
                    f"Reference Price: {candidate.live_cmp}",
                    f"Sheet Date: {candidate.signal_date.isoformat()}",
                    f"Latest Slot: {candidate.latest_slot or 'N/A'}",
                    "Status: STALE REFERENCE — this is not current live price.",
                    "No signal or trading recommendation was generated.",
                ]
            )
    except Exception as exc:
        print(
            "[master-ai-chat] Stale snapshot fallback error "
            f"type={type(exc).__name__}"
        )

    return _format_market_snapshot(snapshot)


def _intelligence_reply(intent: str) -> str:
    """Return a safe read-only intelligence response."""

    try:
        snapshot = get_today_signal_snapshot()
    except Exception as exc:
        print(
            "[master-ai-chat] Intelligence market snapshot error "
            f"type={type(exc).__name__}"
        )
        snapshot = None

    market = MarketReference(
        price=(
            str(snapshot.live_cmp)
            if snapshot is not None and snapshot.live_cmp is not None
            else None
        ),
        observed_at=None,
        source=(
            snapshot.source
            if snapshot is not None
            else "UNAVAILABLE"
        ),
        fresh=bool(
            snapshot is not None
            and snapshot.live_cmp is not None
        ),
        label=(
            "Verified current Sheet reference"
            if snapshot is not None and snapshot.live_cmp is not None
            else "Market reference unavailable"
        ),
    )

    macro = None

    if intent in {
        "MARKET_OUTLOOK",
        "MACRO_OUTLOOK",
        "WAIT_OR_TRADE",
    }:
        try:
            macro = load_macro_assessment()
        except Exception as exc:
            print(
                "[master-ai-chat] Macro provider error "
                f"type={type(exc).__name__}"
            )

    assessment = synthesize_intelligence(
        market=market,
        macro=macro,
        economic_assessments=(),
        news_lock=None,
    )

    base = format_intelligence_response(assessment)

    if intent == "MACRO_OUTLOOK":
        if macro is None:
            return (
                base
                + "\nMacro provider is temporarily unavailable; "
                "no macro bias was guessed. "
                "No market bias was guessed."
            )

        return (
            "Venus Macro AI\n"
            f"Bias: {macro.bias.value}\n"
            f"Confidence: {int(macro.confidence)}%\n"
            "Mode: READ-ONLY\n"
            "No trade, signal, publishing, or external delivery was executed.\n\n"
            + base
        )

    if intent == "NEWS_RISK":
        return (
            base
            + "\nEconomic calendar provider is not connected yet; "
              "no news event was invented."
        )

    if intent == "WAIT_OR_TRADE":
        return (
            base
            + "\nDecision support only: current data is incomplete, "
              "so Master AI cannot say trading is safe."
        )

    return (
        base
        + "\nUnified intelligence is incomplete until macro and "
          "economic providers are connected."
    )


def generate_master_ai_reply(message: str) -> str:
    """Generate one safe reply with OpenAI primary and Gemini fallback."""
    clean_message = str(message or "").strip()

    if not clean_message:
        return "Apna message likhiye."

    if len(clean_message) > 4000:
        return "Message bahut lamba hai. Kripya 4000 characters ke andar bhejein."

    route = route_master_ai_request(clean_message)

    if route.intent == "MARKET_DATA":
        return _market_data_reply()

    if route.intent in {
        "MARKET_OUTLOOK",
        "MACRO_OUTLOOK",
        "NEWS_RISK",
        "WAIT_OR_TRADE",
    }:
        return _intelligence_reply(route.intent)

    if route.intent == "PUBLISH":
        return (
            "Publish request detect hui hai, lekin publishing approval-locked "
            "hai. Master AI review aur explicit owner approval ke bina draft "
            "publish nahi hoga."
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5").strip() or "gpt-5"

    if not api_key:
        return (
            _generate_gemini_reply(clean_message)
            or "⚠️ Master AI API key configure nahi hai."
        )

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
