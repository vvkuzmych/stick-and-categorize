"""Tests run against a real PostgreSQL: the `stick_test` database next to the dev one."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db.session import get_session, to_sqlalchemy_url

BACKEND = Path(__file__).resolve().parents[1]
DEV_URL = os.environ.get("DATABASE_URL", "postgresql://stick:stick@localhost:5432/stick")
TEST_URL = str(make_url(DEV_URL).set(database="stick_test").render_as_string(hide_password=False))


@pytest.fixture(scope="session", autouse=True)
def database():
    admin = create_engine(to_sqlalchemy_url(DEV_URL), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(text("select 1 from pg_database where datname='stick_test'")).scalar()
        if not exists:
            conn.execute(text("create database stick_test"))
    admin.dispose()
    env = {**os.environ, "DATABASE_URL": TEST_URL}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True
    )
    engine = create_engine(to_sqlalchemy_url(TEST_URL))
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean(database):
    with database.begin() as conn:
        conn.execute(text("truncate notes, categories restart identity cascade"))


@pytest.fixture
def client(database):
    from sqlalchemy.orm import Session

    from app.main import app

    def session_override():
        with Session(database) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_session] = session_override
    yield TestClient(app)
    app.dependency_overrides.clear()
