import logging
import uuid
from pathlib import Path

from app.classify.classifier import CategoryClassifier
from app.db.models import Note
from app.domain.intent import asks_for_category, parse_intent
from app.domain.notes import NoteService
from app.speech.transcriber import Transcriber

logger = logging.getLogger("stick.voice")


class EmptyTranscript(Exception):
    pass


class VoiceNoteService:
    """Runs the voice steps in order: transcribe, parse, save."""

    def __init__(
        self,
        transcriber: Transcriber,
        notes: NoteService,
        classifier: CategoryClassifier | None = None,
    ) -> None:
        self.transcriber = transcriber
        self.notes = notes
        self.classifier = classifier

    def create(self, note_id: uuid.UUID, audio: Path) -> tuple[Note, bool]:
        existing = self.notes.get(note_id)
        if existing is not None:  # a retry: skip the slow step
            return existing, False
        text = self.transcriber.transcribe(audio)
        clean_text, category = parse_intent(text)
        if not clean_text:
            raise EmptyTranscript
        if category is None and self.classifier and asks_for_category(clean_text):
            category = self._classify(clean_text)
        return self.notes.create(note_id, clean_text, category)

    def _classify(self, text: str) -> str | None:
        names = [c.name for c in self.notes.categories.list()]
        try:
            return self.classifier.classify(text, names) if names else None
        except Exception:
            logger.exception("classifier raised")
            return None
