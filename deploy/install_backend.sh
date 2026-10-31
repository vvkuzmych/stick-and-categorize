#!/bin/bash
# Installs (or removes) the backend LaunchAgent for the current user.
#   deploy/install_backend.sh            install, migrate, start
#   deploy/install_backend.sh uninstall  stop and remove
set -euo pipefail

LABEL=dev.stick.backend
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
LOG_DIR="$HOME/Library/Logs/stick"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

if [ "${1:-}" = "uninstall" ]; then
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$TARGET"
  echo "Removed $LABEL."
  exit 0
fi

[ -f "$ROOT/.env" ] || { echo "Missing $ROOT/.env (copy .env.example)." >&2; exit 1; }
[ -x "$BACKEND_DIR/.venv/bin/python" ] || { echo "Missing $BACKEND_DIR/.venv (see README)." >&2; exit 1; }

set -a; . "$ROOT/.env"; set +a
[ -n "${DATABASE_URL:-}" ] || { echo "DATABASE_URL is not set in .env." >&2; exit 1; }

mkdir -p "$LOG_DIR" "$(dirname "$TARGET")"
(cd "$BACKEND_DIR" && .venv/bin/alembic upgrade head)

sed -e "s|__BACKEND_DIR__|$BACKEND_DIR|g" \
    -e "s|__DATABASE_URL__|$DATABASE_URL|g" \
    -e "s|__LOG_DIR__|$LOG_DIR|g" \
    "$ROOT/deploy/dev.stick.backend.plist" > "$TARGET"
plutil -lint "$TARGET" >/dev/null

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$TARGET"
echo "Installed $LABEL. Log: $LOG_DIR/backend.log"
