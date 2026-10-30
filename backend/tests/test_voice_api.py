import io
import uuid
import wave
from pathlib import Path

import pytest

from app.api import limits
from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "work_note.wav"


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def transcribe(self, audio: Path) -> str:
        self.calls += 1
        return self.text


def wav_bytes(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * seconds))
    return buf.getvalue()


@pytest.fixture
def fake(client):
    transcriber = FakeTranscriber("Buy milk in category Work.")
    app.state.transcriber = transcriber
    yield transcriber
    del app.state.transcriber


def post_voice(client, note_id=None, audio=None):
    return client.post(
        "/notes/voice",
        data={"id": note_id or str(uuid.uuid4())},
        files={"audio": ("clip.wav", audio if audio is not None else wav_bytes(1), "audio/wav")},
    )


def test_voice_note_is_saved_with_category(client, fake):
    r = post_voice(client)
    assert r.status_code == 201
    assert r.json()["text"] == "Buy milk"
    assert r.json()["category"] == "Work"
    assert client.get("/categories").json() == ["Work"]


def test_voice_note_without_phrase_has_no_category(client, fake):
    fake.text = "Buy milk"
    r = post_voice(client)
    assert r.json()["category"] is None


def test_repeated_voice_upload_returns_same_note_without_transcribing_again(client, fake):
    note_id = str(uuid.uuid4())
    first = post_voice(client, note_id)
    second = post_voice(client, note_id)
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == first.json()
    assert fake.calls == 1
    assert len(client.get("/notes").json()) == 1


def test_empty_transcript_is_an_error_and_saves_nothing(client, fake):
    fake.text = "   "
    r = post_voice(client)
    assert r.status_code == 422
    assert "No speech" in r.json()["detail"]
    assert client.get("/notes").json() == []


def test_transcript_with_only_a_category_phrase_is_an_error(client, fake):
    fake.text = "In category Work."
    assert post_voice(client).status_code == 422
    assert client.get("/categories").json() == []


def test_audio_over_size_limit_is_413(client, fake, monkeypatch):
    monkeypatch.setattr(limits, "MAX_AUDIO_BYTES", 100)
    monkeypatch.setattr("app.api.notes.MAX_AUDIO_BYTES", 100)
    r = post_voice(client, audio=wav_bytes(1))
    assert r.status_code == 413
    assert fake.calls == 0


def test_audio_over_length_limit_is_422(client, fake, monkeypatch):
    monkeypatch.setattr(limits, "MAX_AUDIO_SECONDS", 2)
    r = post_voice(client, audio=wav_bytes(3))
    assert r.status_code == 422
    assert "longer than" in r.json()["detail"]
    assert fake.calls == 0


def test_unreadable_audio_is_422(client, fake):
    r = post_voice(client, audio=b"this is not audio")
    assert r.status_code == 422
    assert fake.calls == 0


def test_missing_audio_is_422(client, fake):
    assert client.post("/notes/voice", data={"id": str(uuid.uuid4())}).status_code == 422


@pytest.mark.slow
def test_real_whisper_end_to_end(client):
    from app.speech.faster_whisper import FasterWhisperTranscriber

    app.state.transcriber = FasterWhisperTranscriber("small")
    try:
        r = post_voice(client, audio=FIXTURE.read_bytes())
    finally:
        del app.state.transcriber
    assert r.status_code == 201, r.text
    assert r.json()["category"].lower() == "work"
    assert "milk" in r.json()["text"].lower()
