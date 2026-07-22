@echo off
REM Quantara - one-time setup (Windows). Needs only Python 3.12+.
cd /d "%~dp0"

py -3.12 --version >nul 2>&1 && (set PY=py -3.12) || (set PY=python)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" 2>nul || (
  echo Python 3.12+ not found. Install from https://python.org and retry.
  pause & exit /b 1
)

%PY% -m venv .venv
set VENV_PY=%~dp0.venv\Scripts\python.exe

echo Installing dependencies (one time, ~2-3 min)...
%VENV_PY% -m pip install --quiet --upgrade pip
%VENV_PY% -m pip install --quiet -r backend\requirements.txt

cd backend
set DATABASE_URL=sqlite:///./dev.db
echo Setting up the database...
%VENV_PY% -m alembic upgrade head
%VENV_PY% -m app.seed
%VENV_PY% -m app.import_assets

echo.
echo Setup complete. Start the app with: run.bat
echo Then open http://localhost:8000
pause
