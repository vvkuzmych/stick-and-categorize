import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.notes import router as notes_router
from app.classify.ollama import OllamaClassifier
from app.db.session import get_session
from app.log import Timer, setup_logging

logger = logging.getLogger("stick")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model once. Tests set app.state.transcriber themselves and skip this.
    from app.speech.faster_whisper import FasterWhisperTranscriber

    setup_logging()
    model = os.environ.get("WHISPER_MODEL", "small")
    logger.info("loading Whisper model %r", model)
    with Timer() as t:
        app.state.transcriber = FasterWhisperTranscriber(model)
    logger.info("Whisper model loaded in %.1f s", t.seconds)
    app.state.classifier = OllamaClassifier.from_env()
    threading.Thread(target=app.state.classifier.warm_up, daemon=True).start()
    yield
    logger.info("shutting down")


app = FastAPI(title="stick-and-categorize", lifespan=lifespan)
app.include_router(notes_router)


@app.get("/health")
def health(
    request: Request, response: Response, session: Annotated[Session, Depends(get_session)]
) -> dict[str, str]:
    """Up means the database answers too, so "backend offline" in the app is honest."""
    try:
        session.execute(text("select 1"))
    except SQLAlchemyError:
        logger.exception("health check: database unreachable")
        response.status_code = 503
        return {"status": "database unavailable"}
    classifier = getattr(request.app.state, "classifier", None)
    ollama = "disabled" if classifier is None else "ok" if classifier.is_up() else "unreachable"
    return {"status": "ok", "ollama": ollama}  # Ollama down is not "backend down"
