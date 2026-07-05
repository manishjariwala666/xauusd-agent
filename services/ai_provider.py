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
        provider = self.settings.ai_provider
        if provider == "OPENAI":
            raw = self._openai_text(system_instruction, user_instruction)
        elif provider == "GEMINI":
            raw = self._gemini_text(system_instruction, user_instruction)
        else:
            raise ConfigurationError(
                "AI_PROVIDER must be GEMINI or OPENAI."
            )
        try:
            parsed = json.loads(_extract_json(raw))
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error("AI provider returned invalid JSON")
            raise RuntimeError("AI provider returned invalid JSON.") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("AI provider response must be a JSON object.")
        return parsed

    def generate_image(
        self,
        *,
        prompt: str,
        output_dir: Path,
    ) -> Path:
        """Generate a real image with OpenAI's image endpoint."""
        if not self.settings.openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required for image generation."
            )
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.settings.ai_image_model,
                "prompt": prompt,
                "size": "1536x1024",
                "quality": "medium",
                "output_format": "png",
            },
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()["data"][0]
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / f"{uuid4().hex}.png"
        if data.get("b64_json"):
            destination.write_bytes(base64.b64decode(data["b64_json"]))
        elif data.get("url"):
            image = requests.get(data["url"], timeout=120)
            image.raise_for_status()
            destination.write_bytes(image.content)
        else:
            raise RuntimeError("Image provider returned no image data.")
        return destination

    def _gemini_text(self, system: str, user: str) -> str:
        if not self.settings.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is not configured.")
        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.models.generate_content(
            model=self.settings.ai_text_model,
            contents=f"{system}\n\n{user}\n\nReturn valid JSON only.",
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


def _extract_json(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    return cleaned[start : end + 1] if start >= 0 and end > start else cleaned
