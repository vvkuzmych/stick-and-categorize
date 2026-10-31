import logging

from app.log import DropHealthChecks


def record(msg: str) -> logging.LogRecord:
    return logging.LogRecord("uvicorn.access", logging.INFO, "", 0, msg, (), None)


def test_health_polls_are_not_logged():
    f = DropHealthChecks()
    assert not f.filter(record('127.0.0.1 - "GET /health HTTP/1.1" 200'))
    assert f.filter(record('127.0.0.1 - "POST /notes/voice HTTP/1.1" 201'))
