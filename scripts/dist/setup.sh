#!/usr/bin/env bash
# Quantara — one-time setup. Needs only Python 3.12+.
# Git Bash/macOS/Linux:  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for candidate in "py -3.12" "py -3" python3 python; do
  if $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
    PY="$candidate"; break
  fi
done
[ -n "$PY" ] || { echo "Python 3.12+ not found. Install from https://python.org and retry."; exit 1; }
echo "Using $PY"

$PY -m venv .venv
ROOT="$(pwd)"
VENV_PY="$ROOT/.venv/Scripts/python"
[ -f "$VENV_PY" ] || VENV_PY="$ROOT/.venv/bin/python"

echo "Installing dependencies (one time, ~2-3 min)..."
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r backend/requirements.txt

cd backend
export DATABASE_URL="sqlite:///./dev.db"
echo "Setting up the database..."
"$VENV_PY" -m alembic upgrade head
"$VENV_PY" -m app.seed
"$VENV_PY" -m app.import_assets

echo
echo "Setup complete. Start the app with:  bash run.sh"
echo "Then open http://localhost:8000"
