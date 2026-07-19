#!/usr/bin/env bash
# =============================================================================
# Quantara Dashboard — local launcher
#
# HOW TO RUN (from Git Bash on Windows):
#
#   1. Open Git Bash in the project root (the folder containing this file).
#   2. First time only:  chmod +x start.sh
#   3. Start everything: ./start.sh          (or: bash start.sh)
#   4. Stop everything:  press Ctrl+C once — both servers are killed.
#
# WHAT IT DOES:
#   - Creates .env from .env.example if you don't have one yet.
#   - Starts PostgreSQL via Docker Compose (skipped with a warning if
#     Docker isn't installed — then use a SQLite DATABASE_URL in .env).
#   - Creates the backend virtualenv (.venv) and installs requirements.
#   - Applies Alembic migrations and seeds mock data (once those exist).
#   - Starts the FastAPI backend on http://localhost:8000 (docs at /docs).
#   - Starts the Angular dev server on http://localhost:4200, if the
#     frontend/ workspace exists (it is created in a later build step).
#
# USEFUL VARIANTS:
#   ./start.sh --no-frontend    backend + db only
#   ./start.sh --reinstall      force pip install / npm install again
#
# REQUIREMENTS: Python 3.12+, Node 20+, Docker Desktop (optional but
# recommended for the real PostgreSQL database).
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

NO_FRONTEND=false
REINSTALL=false
for arg in "$@"; do
  case "$arg" in
    --no-frontend) NO_FRONTEND=true ;;
    --reinstall)   REINSTALL=true ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

log()  { echo -e "\033[1;34m[start]\033[0m $*"; }
warn() { echo -e "\033[1;33m[start]\033[0m $*"; }
die()  { echo -e "\033[1;31m[start]\033[0m $*" >&2; exit 1; }

# --- 0. Environment file -----------------------------------------------------
if [ ! -f .env ]; then
  log "No .env found — copying .env.example"
  cp .env.example .env
fi

# --- 1. Database (Docker Compose) --------------------------------------------
if command -v docker >/dev/null 2>&1; then
  log "Starting PostgreSQL (docker compose up -d)..."
  docker compose up -d
else
  warn "Docker not found — skipping PostgreSQL container."
  # If .env still points at the (unreachable) Docker Postgres, fall back to
  # the local SQLite file for this run so the backend can start at all.
  if grep -q '^DATABASE_URL=postgresql' .env 2>/dev/null; then
    warn "DATABASE_URL in .env points at PostgreSQL, which isn't running."
    warn "Falling back to SQLite (backend/dev.db) for this session."
    export DATABASE_URL="sqlite:///./dev.db"
  fi
fi

# --- 2. Python interpreter (need 3.9+, targeting 3.12) ------------------------
PY=""
for candidate in "py -3.12" "py -3.13" python3 python; do
  if $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    PY="$candidate"
    break
  fi
done
[ -n "$PY" ] || die "Python 3.9+ not found. Install Python 3.12 from python.org (tick 'Add to PATH')."
log "Using Python: $PY ($($PY --version 2>&1))"

# --- 3. Backend: venv + dependencies ------------------------------------------
cd backend
if [ ! -d .venv ] || [ "$REINSTALL" = true ]; then
  log "Creating virtualenv and installing backend dependencies..."
  $PY -m venv .venv
  VENV_PY=".venv/Scripts/python"   # Git Bash path to the Windows venv interpreter
  [ -f "$VENV_PY" ] || VENV_PY=".venv/bin/python"  # fallback for POSIX-style venvs
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt
else
  VENV_PY=".venv/Scripts/python"
  [ -f "$VENV_PY" ] || VENV_PY=".venv/bin/python"
fi

# Apply migrations / seed once those parts of the backend exist.
if [ -f alembic.ini ]; then
  log "Applying database migrations..."
  "$VENV_PY" -m alembic upgrade head
fi
if [ -f app/seed.py ]; then
  log "Seeding mock data (idempotent)..."
  "$VENV_PY" -m app.seed
fi

# --- 4. Start servers ----------------------------------------------------------
PIDS=()
cleanup() {
  log "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

log "Starting backend on http://localhost:8000 (API docs at /docs)"
"$VENV_PY" -m uvicorn app.main:app --reload --port 8000 &
PIDS+=($!)
cd ..

if [ "$NO_FRONTEND" = false ] && [ -f frontend/package.json ]; then
  cd frontend
  if [ ! -d node_modules ] || [ "$REINSTALL" = true ]; then
    log "Installing frontend dependencies (npm install)..."
    npm install
  fi
  log "Starting frontend on http://localhost:4200"
  npm start &
  PIDS+=($!)
  cd ..
elif [ "$NO_FRONTEND" = false ]; then
  warn "frontend/ not created yet — backend only this time."
fi

log "Everything is up. Press Ctrl+C to stop."
wait
