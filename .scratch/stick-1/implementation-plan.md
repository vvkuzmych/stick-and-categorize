# STICK-1: Implementation plan by phases

Source: `docs/STICK-1-c4.html`. Tier 1 = phases 0–4. Tier 2 = phase 5.
Rule for every phase: it ends with something that runs and is checked by a test or a manual demo.

## Phase 0. Risk spikes and skeleton
Goal: kill the two biggest unknowns before building on them.

- Language decision: Python is the main language for all code, including the Mac app (PyObjC gives Python access to AppKit). Swift is the fallback only if spike A fails.
- Spike A (Python + PyObjC): an `NSPanel` that is borderless, sits at desktop level (under normal windows), shows on all Spaces, and survives a Space switch. Hard-code the text. Also check in the same spike: a global hotkey, microphone recording, and that the app can be packaged (py2app) and still asks for microphone permission.
- Spike B (Python): run faster-whisper on a 5-second recorded clip on the target Mac. Record model size, speed and accuracy. If it is too slow, try a smaller model or move the Transcriber to a cloud service (the interface stays the same).
- Repo skeleton: `backend/` (`pyproject.toml`, FastAPI, pytest, ruff), `mac/` (Python package for the desktop app, PyObjC, py2app), local PostgreSQL (docker compose or Homebrew), `.env.example`.

- Spike C (memory): run Whisper and a 3B Ollama model together. Measured on the dev Mac (M1 Pro, 16 GB), one synthetic 8.8 s clip made with `say`:
  - Whisper `small`, int8, CPU: about 0.8 GB, 1.3 s to transcribe (about 7x faster than real time).
  - Ollama `llama3.2:3b`: 2.6 GB loaded, 100% GPU. First call 4.6 s (cold load), later calls 0.3–0.5 s. 3 of 3 sample notes got a sensible category.
  - Both loaded: system memory used went from about 6.3 GB to 8.3 GB, 25% free, and Whisper speed did not change.
  - Not yet tested: real microphone audio and accents.
- Python version: use 3.13 for the backend. `av` has no build for 3.15, and `av` 19.0.2 fails with faster-whisper 1.2.1 (`open() got an unexpected keyword argument 'metadata_errors'`). Pin a compatible `av` version; which one is not verified.

Done when: a sticky shows on the desktop from hard-coded text, and a clip is transcribed with a measured time.

## Phase 1. Backend core, text only (no audio)
Components: PostgreSQL, Repository, Note Service, Category Service, Notes Router.

1. Alembic migration: `categories` (id, unique normalized name) and `notes` (id supplied by client, text, nullable `category_id`, `created_at`).
2. Repository: save note, get note, list notes, find or insert category.
3. Category Service: match ignoring case and extra spaces; rely on the unique constraint for races.
4. Note Service: create with client id; a repeated id returns the existing note.
5. Notes Router: `POST /notes` (text, optional category name, note id), `GET /notes`, `GET /categories`.

Tests first (red, green, refactor): duplicate note id, "Work" vs "work", two parallel category creations, empty list.

Done when: all of the above work through `curl` and pass tests against a real PostgreSQL.

## Phase 2. Voice pipeline
Components: Transcriber, Intent Parser, `POST /notes/voice`.

1. Transcriber interface (audio in, text out) plus the faster-whisper implementation from spike B. Load the model once at startup.
2. Intent Parser: pure function, text in, `(clean_text, category_or_none)` out. Cover phrases like "in category Work" and "categorize as Work". Without such a phrase the category stays empty.
3. `POST /notes/voice`: audio and note id, then transcribe, parse, save, and return the note.
4. Limits: maximum audio size and length, clear error if transcription is empty.

Tests: Intent Parser table tests (many phrasings, no false positives). Pipeline test with a fake Transcriber. One slow end-to-end test with a real audio fixture.

Done when: uploading a recorded clip creates a note, and a clip saying "in category Work" creates it under Work.

## Phase 3. Mac app MVP
Component: Sticky Desktop App.

1. Menu-bar app (no Dock icon) with a settings entry for the backend URL.
2. Global hotkey that starts and stops recording (AVAudioEngine). Ask for microphone permission and handle denial with a clear message.
3. API client: generate the note id before upload, so a retry cannot create a duplicate.
4. Sticky view: a PyObjC `NSPanel` with a text view, from spike A. Plain text only for now: no colours, styling or web view. Show text and category label. Place new stickies so they do not overlap.
5. Launch sync: on start, `GET /notes` and redraw every sticky.

Done when: press the hotkey, speak, and a sticky appears. Quit and relaunch, and all stickies return.

## Phase 4. Hardening and packaging
1. Run the backend as a login item or LaunchAgent so it is up when the app starts. The app retries the connection and shows "backend offline" instead of failing silently.
2. Backend logging and a `/health` endpoint.
3. Sign and notarize the app (needed for microphone permission and distribution outside Xcode).
4. A README with setup steps and a short manual test checklist.

Done when: a clean Mac (or fresh user account) goes from install to first voice sticky following only the README.

## Phase 5. Tier 2: LLM Classifier
Only after phases 0–4 ship.

1. Adapter behind an interface. Only provider: Ollama on localhost (free, private, no quota). Cloud providers are out of scope: free tiers are limited and can change.
2. Called only when the user asked for a category but the parser found no clear name.
3. Send the note text and existing category names. Force the reply into a JSON schema (`{"category": "..."}`) so there is nothing to parse.
4. Time out after a few seconds. On any failure, save the note without a category.
5. Pick a small instruct model (about 3B parameters) by testing two or three on sample notes. Document the Ollama install and model pull in the README, and report Ollama reachability in `/health`.

Done when: "put this with my work stuff" is filed under an existing Work category, and an Ollama outage does not block sticky creation.

## Order and why
- Phase 0 first because the desktop window level and the transcription speed decide the stack. A bad answer there changes the design.
- Backend before app (phases 1–2) so the app can be tested against a working API.
- Idempotent note id is built in phase 1 and used in phase 3, so retries are safe from the first demo.

## Not planned yet (needs a decision)
Editing or deleting stickies, sticky position and colour, offline queue in the app, multi-user or multi-device, cloud transcription.
