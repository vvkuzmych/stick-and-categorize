import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Category, Note


class Repository:
    """The only code that talks SQL."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_note(self, note_id: uuid.UUID) -> Note | None:
        return self.session.get(Note, note_id)

    def list_notes(self) -> list[Note]:
        return list(self.session.scalars(select(Note).order_by(Note.created_at, Note.id)))

    def save_note(self, note_id: uuid.UUID, text: str, category_id: int | None) -> bool:
        """Insert unless the id exists. Returns True if a row was inserted."""
        stmt = (
            insert(Note)
            .values(id=note_id, text=text, category_id=category_id)
            .on_conflict_do_nothing(index_elements=[Note.id])
            .returning(Note.id)
        )
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def list_categories(self) -> list[Category]:
        return list(self.session.scalars(select(Category).order_by(Category.normalized_name)))

    def find_or_insert_category(self, name: str, normalized_name: str) -> Category:
        """Relies on the unique constraint, so parallel callers end up with one row."""
        self.session.execute(
            insert(Category)
            .values(name=name, normalized_name=normalized_name)
            .on_conflict_do_nothing(index_elements=[Category.normalized_name])
        )
        return self.session.execute(
            select(Category).where(Category.normalized_name == normalized_name)
        ).scalar_one()
