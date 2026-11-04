import json
import urllib.request
from typing import Protocol

from app.domain.categories import normalize

PROMPT = (
    "You file short sticky notes into categories. Choose a category from the list only if the "
    "note clearly belongs to it. Otherwise answer with the 'none' option. Do not guess."
)


class CategoryClassifier(Protocol):
    """Note text and existing category names in, one of those names (or None) out.

    Must not raise: any failure means None, so a note is never lost to the classifier.
    `name` and `status()` feed GET /health; status() must be cheap and never raise.
    """

    name: str

    def classify(self, text: str, categories: list[str]) -> str | None: ...

    def status(self) -> str: ...


def user_message(text: str, categories: list[str]) -> str:
    return f"Categories: {json.dumps(categories)}\nNote: {text}"


def pick_existing(answer: object, categories: list[str]) -> str | None:
    """Maps a model answer to an existing name (ignoring case and spaces), else None."""
    wanted = normalize(str(answer))
    return next((c for c in categories if normalize(c) == wanted), None)


def post_json(url: str, body: dict, timeout: float, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)
