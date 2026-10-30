import uuid

from app.db.models import Note
from app.db.repository import Repository
from app.domain.categories import CategoryService


class NoteService:
    def __init__(self, repo: Repository, categories: CategoryService) -> None:
        self.repo = repo
        self.categories = categories

    def create(self, note_id: uuid.UUID, text: str, category_name: str | None) -> tuple[Note, bool]:
        """Returns (note, created). A repeated id returns the stored note unchanged."""
        existing = self.repo.get_note(note_id)
        if existing is not None:
            return existing, False
        category = self.categories.find_or_create(category_name) if category_name else None
        created = self.repo.save_note(note_id, text, category.id if category else None)
        note = self.repo.get_note(note_id)
        self.repo.session.refresh(note)
        return note, created

    def list(self) -> list[Note]:
        return self.repo.list_notes()
