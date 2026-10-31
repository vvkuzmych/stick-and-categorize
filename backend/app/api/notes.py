import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.limits import MAX_AUDIO_BYTES, AudioRejected, check_duration, check_size
from app.db.models import Note
from app.db.repository import Repository
from app.db.session import get_session
from app.domain.categories import CategoryService
from app.domain.notes import NoteService
from app.domain.voice import EmptyTranscript, VoiceNoteService
from app.log import Timer
from app.speech.transcriber import Transcriber

router = APIRouter()
logger = logging.getLogger("stick.voice")


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


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


@router.post("/notes/voice", response_model=NoteOut, status_code=201)
def create_voice_note(
    id: Annotated[uuid.UUID, Form()],
    audio: Annotated[UploadFile, File()],
    response: Response,
    services: Services,
    transcriber: Annotated[Transcriber, Depends(get_transcriber)],
) -> NoteOut:
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    timer = Timer()
    try:
        check_size(len(data))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clip"
            path.write_bytes(data)
            check_duration(path)
            with timer:
                note, created = VoiceNoteService(transcriber, services[0]).create(id, path)
    except AudioRejected as exc:
        logger.warning("voice note %s rejected: %s", id, exc.detail)
        raise HTTPException(exc.status_code, exc.detail) from exc
    except EmptyTranscript as exc:
        logger.warning("voice note %s: no speech found", id)
        raise HTTPException(422, "No speech was found in the audio.") from exc
    logger.info(
        "voice note %s %s in %.1f s, category=%s",
        id, "created" if created else "already existed", timer.seconds, note.category and note.category.name,
    )
    if not created:
        response.status_code = 200
    return NoteOut.of(note)


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
