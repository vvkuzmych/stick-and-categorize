import os

from alembic import context
from sqlalchemy import create_engine

from app.db.models import Base
from app.db.session import to_sqlalchemy_url

target_metadata = Base.metadata


def run_migrations_online() -> None:
    # DATABASE_URL is read at run time, so tests can point at another database.
    engine = create_engine(to_sqlalchemy_url(os.environ["DATABASE_URL"]))
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
