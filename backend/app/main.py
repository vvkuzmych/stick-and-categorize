from fastapi import FastAPI

from app.api.notes import router as notes_router

app = FastAPI(title="stick-and-categorize")
app.include_router(notes_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
