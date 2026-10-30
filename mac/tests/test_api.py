import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from stick.api import ApiClient, ApiError, BackendUnreachable, new_note_id

NOTE = {"id": "n1", "text": "Buy milk", "category": "Work", "created_at": "2026-10-30T09:36:37.838727Z"}


class Handler(BaseHTTPRequestHandler):
    seen: ClassVar[list[tuple[str, str, bytes]]] = []
    reply = (200, [NOTE])

    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        Handler.seen.append((self.command, self.path, self.rfile.read(length)))
        status, body = Handler.reply
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = _answer

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    Handler.seen = []
    Handler.reply = (200, [NOTE])
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_list_notes(server):
    notes = ApiClient(server).list_notes()
    assert [(n.id, n.text, n.category) for n in notes] == [("n1", "Buy milk", "Work")]


def test_upload_sends_id_and_audio(server, tmp_path):
    clip = tmp_path / "note.wav"
    clip.write_bytes(b"RIFFdata")
    Handler.reply = (201, NOTE)
    note = ApiClient(server).upload_voice("my-id", clip)
    _method, path, body = Handler.seen[0]
    assert path == "/notes/voice"
    assert b'name="id"\r\n\r\nmy-id' in body
    assert b'name="audio"; filename="note.wav"' in body and b"RIFFdata" in body
    assert note.id == "n1"


def test_backend_error_message_is_passed_on(server, tmp_path):
    clip = tmp_path / "note.wav"
    clip.write_bytes(b"x")
    Handler.reply = (422, {"detail": "No speech was found in the audio."})
    with pytest.raises(ApiError) as exc:
        ApiClient(server).upload_voice("id", clip)
    assert exc.value.message == "No speech was found in the audio."
    assert exc.value.status == 422
    assert len(Handler.seen) == 1  # an answer from the backend is not retried


def test_unreachable_backend_retries_with_the_same_id(tmp_path, monkeypatch):
    clip = tmp_path / "note.wav"
    clip.write_bytes(b"x")
    ids = []
    client = ApiClient("http://127.0.0.1:1")
    original = client._request

    def spy(method, path, body=None, headers=None):
        ids.append(body)
        return original(method, path, body, headers)

    monkeypatch.setattr(client, "_request", spy)
    with pytest.raises(BackendUnreachable):
        client.upload_voice("same-id", clip)
    assert len(ids) == 3 and len(set(ids)) == 1 and b"same-id" in ids[0]


def test_note_ids_are_unique():
    assert new_note_id() != new_note_id()
