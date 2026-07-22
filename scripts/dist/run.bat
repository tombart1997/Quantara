@echo off
REM Quantara - start the app. Open http://localhost:8000
cd /d "%~dp0backend"
set DATABASE_URL=sqlite:///./dev.db
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
