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
            extracted = _extract_json(raw)
            parsed = json.loads(extracted)
        except (json.JSONDecodeError, TypeError) as exc:
            preview = str(raw or "").replace("\n", " ")[:800]
            logger.error("AI provider returned invalid JSON: {}", preview)
            raise RuntimeError(
                "AI provider returned invalid JSON. Preview: " + preview
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
        """Generate an image with Gemini image generation instead of OpenAI."""
        import base64
        from pathlib import Path
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for image generation.")

        model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / filename

        client = genai.Client(api_key=api_key)
        interaction = client.interactions.create(
            model=model,
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
    """Extract one balanced JSON object from provider text, including markdown code fences."""
    if value is None:
        return ""

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
