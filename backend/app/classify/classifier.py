from typing import Protocol


class CategoryClassifier(Protocol):
    """Note text and existing category names in, one of those names (or None) out.

    Must not raise: any failure means None, so a note is never lost to the classifier.
    """

    def classify(self, text: str, categories: list[str]) -> str | None: ...
