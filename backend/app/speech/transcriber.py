from pathlib import Path
from typing import Protocol


class Transcriber(Protocol):
    """Audio file in, text out. The engine behind it can be swapped."""

    def transcribe(self, audio: Path) -> str: ...
