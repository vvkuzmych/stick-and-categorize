import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from app.classify.ollama import OllamaClassifier


class Handler(BaseHTTPRequestHandler):
    reply: ClassVar[dict] = {"category": "Work"}
    delay = 0.0
    requests: ClassVar[list[dict]] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.requests.append(body)
        time.sleep(Handler.delay)
        self._send({"message": {"content": json.dumps(Handler.reply)}})

    def do_GET(self):
        self._send({"models": [{"name": "m:latest"}]})

    def _send(self, payload):
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    Handler.reply, Handler.delay, Handler.requests = {"category": "Work"}, 0.0, []
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_returns_existing_category_and_sends_schema(server):
    c = OllamaClassifier(server, "m", 2)
    assert c.classify("send report", ["Home", "Work"]) == "Work"
    sent = Handler.requests[0]
    assert sent["format"]["properties"]["category"]["enum"] == ["Home", "Work", ""]
    assert "send report" in sent["messages"][1]["content"]


def test_matches_ignoring_case(server):
    Handler.reply = {"category": "work"}
    assert OllamaClassifier(server, "m", 2).classify("x", ["Work"]) == "Work"


@pytest.mark.parametrize("reply", [{"category": ""}, {"category": "Invented"}, {"other": 1}])
def test_unusable_answers_are_none(server, reply):
    Handler.reply = reply
    assert OllamaClassifier(server, "m", 2).classify("x", ["Work"]) is None


def test_no_categories_means_no_call(server):
    assert OllamaClassifier(server, "m", 2).classify("x", []) is None
    assert Handler.requests == []


def test_timeout_is_none(server):
    Handler.delay = 1.0
    assert OllamaClassifier(server, "m", 0.2).classify("x", ["Work"]) is None


def test_unreachable_is_none_and_not_up():
    c = OllamaClassifier("http://127.0.0.1:1", "m", 1)
    assert c.classify("x", ["Work"]) is None
    assert not c.is_up()


def test_is_up_checks_model_present(server):
    assert OllamaClassifier(server, "m", 1).is_up()
    assert not OllamaClassifier(server, "other", 1).is_up()
