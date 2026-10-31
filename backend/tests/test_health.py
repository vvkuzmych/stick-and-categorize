from sqlalchemy.exc import OperationalError

from app.db.session import get_session
from app.main import app


def test_health_ok_when_database_answers(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_503_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("select 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_session] = lambda: BrokenSession()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "database unavailable"}
