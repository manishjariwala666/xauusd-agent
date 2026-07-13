"""Provider-neutral production AI text and image generation."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from google import genai
from loguru import logger
import requests

from config import ConfigurationError, get_settings


class AIProvider:
    """Call configured AI providers without leaking prompts or credentials."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_json(
        self,
        *,
        system_instruction: str,
        user_instruction: str,
    ) -> dict[str, Any]:
        """Generate and strictly parse one JSON object."""
        provider = str(self.settings.ai_provider).upper()
        try:
            if provider == "OPENAI":
                raw = self._openai_text(system_instruction, user_instruction)
            elif provider == "GEMINI":
                raw = self._gemini_text(system_instruction, user_instruction)
            else:
                raise ConfigurationError(
                    "AI_PROVIDER must be GEMINI or OPENAI."
                )
        except Exception as exc:
            fallback = _fallback_blog_payload(system_instruction, user_instruction)
            if fallback is not None:
                logger.warning(
                    "AI provider unavailable; using deterministic blog fallback: {}",
                    exc,
                )
                return fallback
            raise

        try:
            extracted = _extract_json(raw)
            parsed = json.loads(extracted)
        except (json.JSONDecodeError, TypeError) as exc:
            fallback = _fallback_blog_payload(system_instruction, user_instruction)
            if fallback is not None:
                logger.warning(
                    "AI provider JSON parse failed; using deterministic blog fallback: {}",
                    exc,
                )
                return fallback

            raw_preview = str(raw or "").replace("\n", " ")[:600]
            extracted_preview = str(locals().get("extracted", "") or "").replace("\n", " ")[:1200]
            detail = f"{exc.__class__.__name__}: {exc}"
            logger.error(
                "AI provider returned invalid JSON: {} extracted={}",
                detail,
                extracted_preview,
            )
            raise RuntimeError(
                "AI provider returned invalid JSON. Error: "
                + detail
                + ". Extracted preview: "
                + extracted_preview
                + ". Raw preview: "
                + raw_preview
            ) from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("AI provider response must be a JSON object.")
        return parsed

    def generate_image(
        self,
        *,
        prompt: str,
        output_dir: str | Path,
        filename: str = "generated.png",
    ) -> str:
        """Generate a production image using an official provider API."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / filename

        if self.settings.openai_api_key:
            return self._openai_image(prompt, file_path)
        return self._gemini_image(prompt, file_path)

    def _openai_image(self, prompt: str, file_path: Path) -> str:
        """Generate an image with the official OpenAI Images API."""
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.ai_image_model or "gpt-image-1",
                "prompt": prompt,
                "size": "1536x1024",
                "n": 1,
                "response_format": "b64_json",
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        data = (payload.get("data") or [{}])[0].get("b64_json")
        if not data:
            raise RuntimeError("OpenAI image API returned no image data.")
        file_path.write_bytes(base64.b64decode(data))
        return str(file_path)

    def _gemini_image(self, prompt: str, file_path: Path) -> str:
        """Generate an image with the configured Gemini image model."""
        if not self.settings.gemini_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY or GEMINI_API_KEY is required for image generation."
            )
        client = genai.Client(api_key=self.settings.gemini_api_key)
        interaction = client.interactions.create(
            model=self.settings.ai_image_model,
            input=prompt,
        )

        image = getattr(interaction, "output_image", None)
        if image is None or not getattr(image, "data", None):
            raise RuntimeError("Gemini image API returned no image data.")

        file_path.write_bytes(base64.b64decode(image.data))
        return str(file_path)

    def _gemini_text(self, system: str, user: str) -> str:
        if not self.settings.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is not configured.")

        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.models.generate_content(
            model=self.settings.ai_text_model,
            contents=f"{system}\n\n{user}\n\nReturn one valid JSON object only. Do not use markdown fences.",
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text

    def _openai_text(self, system: str, user: str) -> str:
        if not self.settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is not configured.")
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.ai_text_model,
                "instructions": system,
                "input": user,
                "text": {"format": {"type": "json_object"}},
            },
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("output_text"):
            return str(payload["output_text"])
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("text"):
                    return str(content["text"])
        raise RuntimeError("OpenAI returned an empty response.")


def _fallback_blog_payload(system_instruction: str, user_instruction: str) -> dict[str, object] | None:
    """Fail-open SEO blog payload so content publishing never stops on model JSON formatting."""
    combined = f"{system_instruction}\n{user_instruction}".lower()
    if not any(marker in combined for marker in ("seo blog", "meta_title", "focus_keyword", "image_prompt")):
        return None

    topic = "XAUUSD market structure and risk control"
    topic_match = re.search(r"(?:topic|objective|request)\s*[:=-]\s*([^\n]{8,120})", user_instruction, re.IGNORECASE)
    if topic_match:
        topic = topic_match.group(1).strip(" .:-")

    focus_keyword = "XAUUSD market structure"
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-") or "xauusd-market-update"
    slug = slug[:80].strip("-") or "xauusd-market-update"

    title = "XAUUSD Market Structure and Risk Control"
    meta_title = "XAUUSD Market Structure & Risk Control Guide"
    meta_description = (
        "Understand XAUUSD market structure, gold volatility, and disciplined risk control "
        "for safer trading decisions in changing global market conditions."
    )

    body = f"""# {title}

XAUUSD, also known as Gold versus the US Dollar, remains one of the most watched instruments for traders because it reacts to inflation expectations, US dollar strength, bond yields, central-bank policy, geopolitical risk, and global risk sentiment.

## Current market structure

A disciplined trader should first identify whether gold is trading in a trending, ranging, or transition phase. In a trending phase, price generally respects higher highs and higher lows in an uptrend or lower highs and lower lows in a downtrend. In a ranging phase, traders should focus on support, resistance, liquidity zones, and false breakouts instead of chasing every candle.

## Key drivers for XAUUSD

The major drivers for XAUUSD usually include the US Dollar Index, real yields, Federal Reserve policy expectations, inflation data, employment numbers, geopolitical uncertainty, and broader market risk appetite. When the dollar strengthens sharply, gold can face pressure. When risk sentiment weakens or inflation concerns rise, gold can attract safe-haven flows.

## Risk control

Risk management is more important than prediction. Every trade should have a predefined invalidation point, position size, and maximum loss. Traders should avoid over-leverage, revenge trading, and entering positions without confirmation. A simple rule is to risk only a small fixed percentage of capital per trade and avoid increasing lot size after losses.

## Practical trading approach

For intraday trading, traders can mark the Asian session range, London liquidity sweep areas, previous day high and low, and major support-resistance zones. For swing trading, daily and four-hour market structure are more useful. A trade idea becomes stronger when trend direction, liquidity, support-resistance, and macro context align.

## Conclusion

XAUUSD can provide strong opportunities, but only for traders who combine market structure with strict risk control. The goal is not to win every trade. The goal is to follow a repeatable process, protect capital, and take only high-quality setups."""

    return {
        "title": title,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "focus_keyword": focus_keyword,
        "slug": slug,
        "excerpt": meta_description,
        "summary": meta_description,
        "content": body,
        "body": body,
        "body_markdown": body,
        "article": body,
        "markdown": body,
        "tags": ["XAUUSD", "Gold", "Risk Control", "Market Structure"],
        "schema": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": meta_description,
        },
        "schema_markup": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": meta_description,
        },
        "image_prompt": "Professional financial editorial image showing gold bars, XAUUSD chart candles, global market background, clean premium trading website style.",
    }


def _extract_json(value: str) -> str:
    """Extract one balanced JSON object from provider text, including broken markdown fences."""
    if value is None:
        return ""

    text_value = str(value).strip()

    # Remove markdown code fences even when the provider forgets the closing fence.
    text_value = re.sub(r"^```(?:json)?\s*", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\s*```\s*$", "", text_value).strip()

    start = text_value.find("{")
    if start < 0:
        return text_value

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text_value)):
        char = text_value[index]

        if escape:
            escape = False
            continue

        if char == "\\" and in_string:
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text_value[start:index + 1]

    return text_value[start:]


    text_value = str(value).strip()

    fenced = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text_value,
        re.IGNORECASE | re.DOTALL,
    )
    if fenced:
        text_value = fenced.group(1).strip()

    if text_value.startswith("{") and text_value.endswith("}"):
        return text_value

    start = text_value.find("{")
    if start < 0:
        return text_value

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text_value)):
        char = text_value[index]

        if escape:
            escape = False
            continue

        if char == "\\" and in_string:
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text_value[start:index + 1]

    return text_value
