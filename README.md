# Quantara Dashboard

A locally hosted research and decision-support tool for stocks, commodities,
and market events. **Not a trading bot** — it organizes watchlists, prices,
events, news, journal notes, and transparent rule-based signals.

## Stack

- **Frontend:** Angular, TypeScript, Angular Material, ECharts
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic
- **Database:** PostgreSQL 16 (Docker Compose)

## Layout

```
backend/    FastAPI app (app/), requirements.txt
frontend/   Angular workspace (created in a later step)
docker-compose.yml   PostgreSQL for local dev
.env.example         Copy to .env and adjust
```

## Quick start

```bash
./start.sh        # Git Bash, from the project root
```

Starts the database, backend (:8000), and frontend (:4200) together;
Ctrl+C stops everything. See the header comments in `start.sh` for options
(`--no-frontend`, `--reinstall`).

## Manual setup

Prerequisites: Python 3.12+, Node 20+, Docker Desktop.

```bash
cp .env.example .env          # adjust credentials if you like
docker compose up -d          # start PostgreSQL

cd backend
python -m venv .venv
.venv/Scripts/activate        # Git Bash on Windows; .venv\Scripts\activate.bat in cmd
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### No Docker yet?

Point `DATABASE_URL` in `.env` at SQLite temporarily —
`DATABASE_URL=sqlite:///./dev.db` — and switch back once Docker Desktop
is installed. No code changes needed.

## Development status

Core app is complete: dashboard, asset pages (ECharts price history, event
timeline, news, journal), calendar, journal, and a transparent rule-based
signal engine — all wired end-to-end.

**Live data:** news is fetched from Google News RSS (no API key) per asset
via `POST /api/v1/news/refresh`; sentiment is a documented keyword-scoring
placeholder until an AI/NLP step is added. Prices come from Yahoo Finance
(yfinance, no API key) via `POST /api/v1/assets/refresh-prices`; set
`MARKET_DATA_PROVIDER=mock` to go back to synthetic data. Real providers
plug into `app/services/providers/`.
