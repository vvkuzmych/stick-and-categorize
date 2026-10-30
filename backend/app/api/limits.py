import os
from pathlib import Path

import av

MAX_AUDIO_BYTES = int(os.environ.get("MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
MAX_AUDIO_SECONDS = float(os.environ.get("MAX_AUDIO_SECONDS", "60"))


class AudioRejected(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def check_size(size: int) -> None:
    if size > MAX_AUDIO_BYTES:
        raise AudioRejected(413, f"Audio is larger than {MAX_AUDIO_BYTES} bytes.")


def check_duration(path: Path) -> None:
    try:
        with av.open(str(path)) as container:
            seconds = (container.duration or 0) / av.time_base
    except av.error.FFmpegError as exc:
        raise AudioRejected(422, "Audio could not be read.") from exc
    if seconds <= 0:
        raise AudioRejected(422, "Audio is empty.")
    if seconds > MAX_AUDIO_SECONDS:
        raise AudioRejected(422, f"Audio is longer than {MAX_AUDIO_SECONDS:g} seconds.")
