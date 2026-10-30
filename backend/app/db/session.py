import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


def to_sqlalchemy_url(url: str) -> str:
    """`postgresql://` in .env means the psycopg 3 driver here."""
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def get_engine() -> Engine:
    return create_engine(to_sqlalchemy_url(os.environ["DATABASE_URL"]))


def get_session() -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on error."""
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
