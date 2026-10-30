# stick-and-categorize
Make sticks and categorize them

## Setup (Phase 0)

Python 3.13 everywhere.

    cp .env.example .env
    docker compose up -d db                      # or: brew install postgresql@16

    cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/pytest && .venv/bin/ruff check .
    .venv/bin/python spikes/transcribe_spike.py CLIP.wav small     # spike B

    cd ../mac && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/python spikes/panel_spike.py 60                      # spike A: sticky panel
    .venv/bin/python spikes/hotkey_spike.py 60                     # spike A: Ctrl+Option+Space
    .venv/bin/python spikes/record_spike.py 5 clip.wav             # spike A: microphone
    cd packaging && ../.venv/bin/python setup.py py2app            # spike A: packaged app

## Phase 1: backend

    cd backend && set -a && . ../.env && set +a
    .venv/bin/alembic upgrade head
    .venv/bin/uvicorn app.main:app
    .venv/bin/pytest          # uses a separate `stick_test` database

The project database listens on host port 5433, because 5432 is often taken by a local PostgreSQL.

## Phase 2: voice

    # uvicorn loads the Whisper model at startup (WHISPER_MODEL, default `small`)
    curl -F id=$(uuidgen) -F audio=@backend/tests/fixtures/work_note.wav localhost:8000/notes/voice
    .venv/bin/pytest -m slow  # real-model end-to-end test

Limits: `MAX_AUDIO_BYTES` (default 10 MB) and `MAX_AUDIO_SECONDS` (default 60).

## Phase 3: Mac app

    # backend running on :8000 (see Phase 1/2), then:
    cd mac && .venv/bin/pip install -e ".[dev]" && .venv/bin/python -m stick
    .venv/bin/pytest                                  # placement and API client tests
    cd packaging && PYTHONPATH=.. ../.venv/bin/python setup.py py2app   # builds dist/Stick.app

Press Ctrl+Option+Space to start recording and again to stop. The menu-bar icon (📝) shows the status
and has "Backend URL…". macOS asks for Microphone and Input Monitoring permission on first use.
