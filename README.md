# stick-and-categorize
Make sticks and categorize them

Say a note, and it appears as a sticky on your Mac desktop. Say "in category Work" to file it.

## Install (Mac)

You need: a Mac (tested on Apple silicon), [Docker Desktop](https://www.docker.com/products/docker-desktop/),
Python 3.13 (`brew install python@3.13`) and an internet connection for the first run (the Whisper
speech model is downloaded once, about 0.5 GB).

Run these from the repo root:

    cp .env.example .env                  # optional: put GEMINI_API_KEY in it (see "Phase 5")
    docker compose up -d db               # PostgreSQL in Docker
    (cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]")
    deploy/install_backend.sh             # migrates the database, starts the backend at every login
    (cd mac && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]")
    mac/packaging/build_dev.sh            # builds and signs mac/packaging/dist/Stick.app
    open mac/packaging/dist/Stick.app

Then:

1. Check the backend: `curl localhost:8000/health` returns `{"status":"ok",...}`. The first start
   takes up to a minute while the speech model loads.
2. Look for the note icon in the menu bar. Its first menu line should say "Ready".
3. Press **Ctrl+Option+R**, say "buy milk in category shopping", press **Ctrl+Option+R** again.
   macOS asks for Microphone access the first time: allow it. A sticky `[shopping] buy milk` appears
   on the desktop (hide other windows with Cmd+Option+H to see it).

Using it: drag a sticky to move it (the position is not saved), click the ✕ on it to delete it.

To start the app at login: System Settings > General > Login Items > add `Stick.app`.
Docker Desktop must also start at login (Docker Desktop > Settings > General), or the database is down.

Update after a code change: `deploy/install_backend.sh` (backend) and `mac/packaging/build_dev.sh`
(app), then reopen the app. Always build the app with `build_dev.sh`: an unsigned build asks for the
microphone again every time.

Uninstall: `deploy/install_backend.sh uninstall`, quit and delete `Stick.app`, and
`docker compose down -v` to delete the database.

If something does not work: `tail -f ~/Library/Logs/stick/backend.log`. Details are in Phase 4 below.

## Setup (Phase 0)

Python 3.13 everywhere.

    cp .env.example .env
    docker compose up -d db                      # or: brew install postgresql@16

    cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/pytest && .venv/bin/ruff check .
    .venv/bin/python spikes/transcribe_spike.py CLIP.wav small     # spike B

    cd ../mac && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"
    .venv/bin/python spikes/panel_spike.py 60                      # spike A: sticky panel
    .venv/bin/python spikes/hotkey_spike.py 60                     # spike A: Ctrl+Option+Space (the app uses Ctrl+Option+R)
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

Speech is transcribed as English by default. Set `WHISPER_LANGUAGE` to another code (for example `uk`), or empty to auto-detect.

Limits: `MAX_AUDIO_BYTES` (default 10 MB) and `MAX_AUDIO_SECONDS` (default 60).

## Phase 3: Mac app

    # backend running on :8000 (see Phase 1/2), then:
    cd mac && .venv/bin/pip install -e ".[dev]" && .venv/bin/python -m stick
    .venv/bin/pytest                                  # placement and API client tests
    cd packaging && PYTHONPATH=.. ../.venv/bin/python setup.py py2app   # builds dist/Stick.app

Press Ctrl+Option+R to start recording and again to stop. Click the ✕ in the corner of a sticky to delete it (`DELETE /notes/{id}`). The menu-bar icon (📝) shows the status
and has "Backend URL…". macOS asks for Microphone permission on first use (the hotkey needs no permission).

## Phase 4: install on a Mac

One-time setup, from the repo root:

    cp .env.example .env
    docker compose up -d db          # restarts with Docker Desktop; set Docker Desktop to start at login
    (cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]")
    deploy/install_backend.sh        # migrates, installs the LaunchAgent, starts the backend
    (cd mac && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]")
    mac/packaging/build_dev.sh       # dist/Stick.app, signed with a local certificate

`build_dev.sh` makes a local signing certificate once (login keychain) and signs every build with it. An unsigned build gets a new identity each time, so macOS asks for the microphone again after every rebuild.

The first run downloads the Whisper model (internet needed once). Open `mac/packaging/dist/Stick.app`,
allow Microphone when asked. Remove the backend with `deploy/install_backend.sh uninstall`.
`install_backend.sh` copies `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TIMEOUT`, `WHISPER_MODEL`, `WHISPER_LANGUAGE` and `LOG_LEVEL` from `.env` into the LaunchAgent when set (the agent does not read `.env`), so re-run it after changing them.

Backend log: `~/Library/Logs/stick/backend.log` (`LOG_LEVEL=DEBUG` in the LaunchAgent environment for more).
`GET /health` returns 200 only when PostgreSQL answers, otherwise 503.

Signed release (needs an Apple Developer ID certificate and a `notarytool` keychain profile):

    SIGN_IDENTITY="Developer ID Application: Name (TEAMID)" NOTARY_PROFILE=stick mac/packaging/release.sh

### Manual test checklist

1. Log out and in. `curl localhost:8000/health` returns `{"status":"ok"}` without starting anything.
2. Stop the backend (`launchctl kill TERM gui/$(id -u)/dev.stick.backend`). It comes back by itself within seconds.
3. Quit the app, stop the backend, open the app: the menu shows "Backend offline", the icon shows ⚠️.
   Start the backend: the status changes to "Ready" and the stickies appear without relaunching.
4. Press Ctrl+Option+R, say "buy milk in category shopping", press again: a sticky "[shopping] buy milk" appears.
5. Say nothing and stop: the menu shows "No speech was found in the audio." and no sticky appears.
6. Deny the microphone in System Settings, press the hotkey: a clear message appears, no crash.
7. Quit and reopen the app: all stickies return. Switch Spaces: they stay on the desktop.
8. Menu > Backend URL… with a wrong address: "Backend offline". Back to the right one: stickies return.

## Phase 5: category classifier (optional, Gemini)

When you ask for a category in other words ("put this with my work stuff") and the parser finds no name,
the backend asks Google's Gemini API to pick one of your existing categories. Without a key everything
else works; the note is just saved without a category.

Set `GEMINI_API_KEY=...` (a key from Google AI Studio) in the backend environment (`.env`; for the
LaunchAgent, its `EnvironmentVariables`, never the repo). Optional: `GEMINI_MODEL` (default
`gemini-3.5-flash-lite`), `GEMINI_TIMEOUT` (seconds, default 8; a call takes about 2 to 3 s, but 13 to 24 s were seen when Google was busy; a failed DNS lookup is not covered by the timeout and can take about 30 s), `GEMINI_URL`.

**The note text and your category names are sent to Google.** On the free (unpaid) tier Google's terms say submitted content may be used to improve its products and read by human reviewers (checked 2026-11-04; the terms say not to send sensitive or personal information, and paid-tier terms differ). Do not dictate private notes with a category request on the free tier, or leave the key unset. Only notes where
you asked for a category in words are sent, and only when at least one category exists. The model cannot
create a new category. On any error or timeout the note is saved without a category.

`GET /health` shows `"classifier": {"provider": "gemini", "status": "configured"}` (or `"none"`/`"disabled"`
without a key). It makes no network call, to save quota, and a classifier problem never makes `/health` fail.

Manual check: create a category (say "buy milk in category Work"), then say "send the report, put this
with my work stuff": the sticky shows `[Work]`. Unset the key and repeat: the sticky still appears, without a category.
