import tempfile
from pathlib import Path

import pytest

from stick.recorder import discard_recording


def test_discard_removes_the_recording_folder():
    folder = Path(tempfile.mkdtemp(prefix="stick-"))
    clip = folder / "note.wav"
    clip.write_bytes(b"x")
    discard_recording(clip)
    assert not folder.exists()


def test_discard_leaves_other_folders_alone(tmp_path):
    clip = tmp_path / "note.wav"
    clip.write_bytes(b"x")
    discard_recording(clip)
    assert clip.exists()


def test_recording_writes_a_wav_file_without_crashing():
    import time

    from stick.recorder import AUTHORIZED, AV, Recorder

    if AV.AVCaptureDevice.authorizationStatusForMediaType_(AV.AVMediaTypeAudio) != AUTHORIZED:
        pytest.skip("microphone access is not granted to this process")
    recorder = Recorder()
    recorder.start()
    time.sleep(1)
    path = recorder.stop()
    try:
        assert path.stat().st_size > 1000
    finally:
        discard_recording(path)
