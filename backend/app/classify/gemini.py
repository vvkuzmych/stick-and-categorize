"""Asks Google's Gemini (Interactions) API which existing category a note belongs to (opt-in, sends text out)."""

import json
import logging
import os
from typing import Self

from app.classify.classifier import PROMPT, pick_existing, post_json, user_message

logger = logging.getLogger("stick.classify")

NONE_OPTION = "none"
API_REVISION = "2026-05-20"


def _output_text(reply: dict) -> str:
    step = next(s for s in reply["steps"] if s["type"] == "model_output")
    return step["content"][0]["text"]


class GeminiClassifier:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    @classmethod
    def from_env(cls) -> Self | None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            logger.info("GEMINI_API_KEY is empty: no category classifier")
            return None
        return cls(
            key,
            os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            float(os.environ.get("GEMINI_TIMEOUT", "8")),
            os.environ.get("GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta"),
        )

    def classify(self, text: str, categories: list[str]) -> str | None:
        if not categories:
            return None
        body = {
            "model": self.model,
            "system_instruction": PROMPT,
            "input": user_message(text, categories),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": [*categories, NONE_OPTION]}
                    },
                    "required": ["category"],
                },
            },
        }
        try:
            reply = post_json(
                f"{self.base_url}/interactions",
                body,
                self.timeout,
                # Key in a header, not the URL: keeps it out of logs.
                {"x-goog-api-key": self.api_key, "Api-Revision": API_REVISION},
            )
            answer = json.loads(_output_text(reply))["category"]
        except Exception as exc:  # noqa: BLE001 - any failure means "no category"
            logger.warning("classifier failed: %s: %s", type(exc).__name__, exc)
            return None
        return pick_existing(answer, categories)

    def status(self) -> str:
        """No network call: /health is polled often and the free tier has a quota."""
        return "configured"
