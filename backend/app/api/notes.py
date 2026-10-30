import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.models import Note
from app.db.repository import Repository
from app.db.session import get_session
from app.domain.categories import CategoryService
from app.domain.notes import NoteService

router = APIRouter()


class NoteIn(BaseModel):
    id: uuid.UUID
    text: str = Field(min_length=1)
    category: str | None = None

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class NoteOut(BaseModel):
    id: uuid.UUID
    text: str
    category: str | None
    created_at: datetime

    @classmethod
    def of(cls, note: Note) -> "NoteOut":
        return cls(
            id=note.id,
            text=note.text,
            category=note.category.name if note.category else None,
            created_at=note.created_at,
        )


def get_services(session: Annotated[Session, Depends(get_session)]) -> tuple[NoteService, CategoryService]:
    repo = Repository(session)
    categories = CategoryService(repo)
    return NoteService(repo, categories), categories


Services = Annotated[tuple[NoteService, CategoryService], Depends(get_services)]


@router.post("/notes", response_model=NoteOut, status_code=201)
def create_note(body: NoteIn, response: Response, services: Services) -> NoteOut:
    notes, _ = services
    note, created = notes.create(body.id, body.text, body.category)
    if not created:
        response.status_code = 200
    return NoteOut.of(note)


@router.get("/notes", response_model=list[NoteOut])
def list_notes(services: Services) -> list[NoteOut]:
    notes, _ = services
    return [NoteOut.of(n) for n in notes.list()]


@router.get("/categories", response_model=list[str])
def list_categories(services: Services) -> list[str]:
    _, categories = services
    return [c.name for c in categories.list()]
