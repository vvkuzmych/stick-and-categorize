"""Microphone recording with AVAudioEngine, started and stopped on demand."""
import tempfile
from collections.abc import Callable
from pathlib import Path

import AVFoundation as AV
from Foundation import NSURL
from PyObjCTools import AppHelper

AUTHORIZED, NOT_ASKED = 3, 0

DENIED_MESSAGE = (
    "Microphone access is off. Turn it on in System Settings > Privacy & Security > Microphone."
)


def ensure_permission(done: Callable[[bool], None]) -> None:
    """Calls `done(granted)` on the main thread."""
    status = AV.AVCaptureDevice.authorizationStatusForMediaType_(AV.AVMediaTypeAudio)
    if status == AUTHORIZED:
        done(True)
    elif status == NOT_ASKED:
        AV.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AV.AVMediaTypeAudio, lambda granted: AppHelper.callAfter(done, bool(granted))
        )
    else:
        done(False)


class Recorder:
    def __init__(self) -> None:
        self._engine = None
        self._file = None
        self._path: Path | None = None

    @property
    def recording(self) -> bool:
        return self._engine is not None

    def start(self) -> None:
        """Raises RuntimeError if the audio engine cannot start."""
        self._path = Path(tempfile.mkdtemp(prefix="stick-")) / "note.wav"
        engine = AV.AVAudioEngine.alloc().init()
        node = engine.inputNode()
        fmt = node.outputFormatForBus_(0)
        audio_file, err = AV.AVAudioFile.alloc().initForWriting_settings_error_(
            NSURL.fileURLWithPath_(str(self._path)), fmt.settings(), None
        )
        if audio_file is None:
            raise RuntimeError(f"Cannot open the recording file: {err}")
        node.installTapOnBus_bufferSize_format_block_(
            0, 4096, fmt, lambda buffer, _when: audio_file.writeFromBuffer_error_(buffer, None)
        )
        ok, err = engine.startAndReturnError_(None)
        if not ok:
            node.removeTapOnBus_(0)
            raise RuntimeError(f"Cannot start the microphone: {err}")
        self._engine, self._file = engine, audio_file

    def stop(self) -> Path:
        assert self._engine is not None and self._path is not None
        self._engine.inputNode().removeTapOnBus_(0)
        self._engine.stop()
        self._engine = self._file = None  # releasing the file closes it
        return self._path
