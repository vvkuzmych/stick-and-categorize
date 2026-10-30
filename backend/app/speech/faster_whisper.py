import threading
from pathlib import Path

from faster_whisper import WhisperModel


class FasterWhisperTranscriber:
    """Runs faster-whisper on the CPU. Settings measured in Phase 0: `small`, int8."""

    def __init__(self, model_size: str = "small") -> None:
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self._lock = threading.Lock()  # one model instance: one clip at a time

    def transcribe(self, audio: Path) -> str:
        with self._lock:
            segments, _info = self._model.transcribe(str(audio))
            return " ".join(s.text.strip() for s in segments).strip()
