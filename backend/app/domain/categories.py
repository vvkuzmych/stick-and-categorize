from app.db.models import Category
from app.db.repository import Repository


def normalize(name: str) -> str:
    return " ".join(name.split()).casefold()


class CategoryService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def find_or_create(self, name: str) -> Category | None:
        """Returns None for a blank name."""
        display = " ".join(name.split())
        if not display:
            return None
        return self.repo.find_or_insert_category(display, normalize(display))

    def list(self) -> list[Category]:
        return self.repo.list_categories()
