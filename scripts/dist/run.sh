#!/usr/bin/env bash
# Quantara — start the app. Open http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/backend"
export DATABASE_URL="sqlite:///./dev.db"
VENV_PY="../.venv/Scripts/python"
[ -f "$VENV_PY" ] || VENV_PY="../.venv/bin/python"
"$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
