import uuid
from pathlib import Path

from app.db.models import Note
from app.domain.intent import parse_intent
from app.domain.notes import NoteService
from app.speech.transcriber import Transcriber


class EmptyTranscript(Exception):
    pass


class VoiceNoteService:
    """Runs the voice steps in order: transcribe, parse, save."""

    def __init__(self, transcriber: Transcriber, notes: NoteService) -> None:
        self.transcriber = transcriber
        self.notes = notes

    def create(self, note_id: uuid.UUID, audio: Path) -> tuple[Note, bool]:
        existing = self.notes.get(note_id)
        if existing is not None:  # a retry: skip the slow step
            return existing, False
        text = self.transcriber.transcribe(audio)
        clean_text, category = parse_intent(text)
        if not clean_text:
            raise EmptyTranscript
        return self.notes.create(note_id, clean_text, category)
