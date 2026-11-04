import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from app.classify.gemini import GeminiClassifier


class Handler(BaseHTTPRequestHandler):
    reply: ClassVar[dict] = {"category": "Work"}
    delay = 0.0
    status = 200
    seen: ClassVar[list[tuple[str, str | None, dict]]] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.seen.append((self.path, self.headers["x-goog-api-key"], body))
        time.sleep(Handler.delay)
        text = json.dumps(Handler.reply)
        steps = [{"type": "thought"}, {"type": "model_output", "content": [{"text": text}]}]
        data = json.dumps({"status": "completed", "steps": steps}).encode()
        self.send_response(Handler.status)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    Handler.reply, Handler.delay, Handler.status, Handler.seen = {"category": "Work"}, 0.0, 200, []
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_sends_key_in_header_and_enum_schema(server):
    c = GeminiClassifier("secret", "gm", 2, server)
    assert c.classify("send report", ["Home", "Work"]) == "Work"
    path, key, body = Handler.seen[0]
    assert path == "/interactions"
    assert "secret" not in path
    assert key == "secret"
    assert body["model"] == "gm"
    assert body["response_format"]["mime_type"] == "application/json"
    assert body["response_format"]["schema"]["properties"]["category"]["enum"] == [
        "Home",
        "Work",
        "none",
    ]
    assert "send report" in body["input"]


def test_matches_ignoring_case(server):
    Handler.reply = {"category": "work"}
    assert GeminiClassifier("k", "gm", 2, server).classify("x", ["Work"]) == "Work"


@pytest.mark.parametrize("reply", [{"category": "none"}, {"category": "Invented"}, {"other": 1}])
def test_unusable_answers_are_none(server, reply):
    Handler.reply = reply
    assert GeminiClassifier("k", "gm", 2, server).classify("x", ["Work"]) is None


def test_no_categories_means_no_call(server):
    assert GeminiClassifier("k", "gm", 2, server).classify("x", []) is None
    assert Handler.seen == []


def test_http_error_and_timeout_are_none(server):
    Handler.status = 429
    assert GeminiClassifier("k", "gm", 2, server).classify("x", ["Work"]) is None
    Handler.status, Handler.delay = 200, 1.0
    assert GeminiClassifier("k", "gm", 0.2, server).classify("x", ["Work"]) is None


def test_status_makes_no_network_call():
    assert GeminiClassifier("k", "gm", 1, "http://127.0.0.1:1").status() == "configured"


def test_from_env_needs_a_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "  ")
    assert GeminiClassifier.from_env() is None
    monkeypatch.setenv("GEMINI_API_KEY", "abc")
    assert isinstance(GeminiClassifier.from_env(), GeminiClassifier)
