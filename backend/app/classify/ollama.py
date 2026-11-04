"""Asks a local Ollama model which existing category a note belongs to."""
import json
import logging
import os
import urllib.request
from typing import Self

from app.domain.categories import normalize

logger = logging.getLogger("stick.classify")

PROMPT = (
    "You file short sticky notes into categories. Choose a category from the list only if the "
    "note clearly belongs to it. Otherwise answer with an empty string. Do not guess."
)


class OllamaClassifier:
    def __init__(self, url: str, model: str, timeout: float) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
            float(os.environ.get("OLLAMA_TIMEOUT", "5")),
        )

    def classify(self, text: str, categories: list[str]) -> str | None:
        if not categories:
            return None
        body = {
            "model": self.model,
            "stream": False,
            "keep_alive": "30m",  # a cold load takes seconds; keep the model warm
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"Categories: {json.dumps(categories)}\nNote: {text}"},
            ],
            "format": {
                "type": "object",
                "properties": {"category": {"type": "string", "enum": [*categories, ""]}},
                "required": ["category"],
            },
        }
        try:
            reply = self._post("/api/chat", body, self.timeout)
            answer = json.loads(reply["message"]["content"])["category"]
        except Exception as exc:  # noqa: BLE001 - any failure means "no category"
            logger.warning("classifier failed: %s: %s", type(exc).__name__, exc)
            return None
        wanted = normalize(str(answer))
        return next((c for c in categories if normalize(c) == wanted), None)

    def is_up(self) -> bool:
        """True when Ollama answers and has the model."""
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=1) as response:
                names = [m["name"] for m in json.load(response)["models"]]
        except Exception:  # noqa: BLE001
            return False
        return self.model in names or f"{self.model}:latest" in names

    def warm_up(self) -> None:
        self.classify("warm up", ["a"])

    def _post(self, path: str, body: dict, timeout: float) -> dict:
        request = urllib.request.Request(
            self.url + path, json.dumps(body).encode(), {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
