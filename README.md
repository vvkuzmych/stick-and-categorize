# stick-and-categorize
Make sticks and categorize them

## Setup (Phase 0)

Python 3.13 everywhere.

    cp .env.example .env
    docker compose up -d db                      # or: brew install postgresql@16

    cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev,spikes]"
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
