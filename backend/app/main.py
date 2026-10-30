import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.notes import router as notes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model once. Tests set app.state.transcriber themselves and skip this.
    from app.speech.faster_whisper import FasterWhisperTranscriber

    app.state.transcriber = FasterWhisperTranscriber(os.environ.get("WHISPER_MODEL", "small"))
    yield


app = FastAPI(title="stick-and-categorize", lifespan=lifespan)
app.include_router(notes_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
