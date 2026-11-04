from sqlalchemy.exc import OperationalError

from app.db.session import get_session
from app.main import app


def test_health_ok_when_database_answers(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ollama": "disabled"}


def test_health_is_503_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("select 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_session] = lambda: BrokenSession()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "database unavailable"}


def test_health_reports_ollama_without_failing_when_it_is_down(client):
    class Down:
        def is_up(self):
            return False

    app.state.classifier = Down()
    try:
        response = client.get("/health")
    finally:
        del app.state.classifier
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ollama": "unreachable"}
