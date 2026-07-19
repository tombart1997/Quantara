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

Core app is complete: dashboard, asset explorer (36 assets incl. leveraged
ETFs), asset pages (ECharts price history, event timeline, news, journal),
calendar with recurring events, thesis-review journal, and a transparent
rule-based signal engine (7 rules) — all wired end-to-end.

**Automation:** a background scheduler refreshes prices, events, news, and
signals every 30 minutes (`REFRESH_INTERVAL_MINUTES`), with a freshness
indicator and manual "refresh now" in the dashboard header.

**Live data:** prices from Yahoo Finance (yfinance), news from Google News
RSS, earnings events from Yahoo — no API keys needed. Macro events activate
with a free `FINNHUB_API_KEY`. Sentiment is LLM-scored via Kimi when
`KIMI_API_KEY` is set, with a keyword-scorer fallback.

**AI consultant:** global dialog (pink FAB) with asset-consult and
cross-reference modes (14-indicator registry, auto-included calendar events,
3-step narrative analysis). Prompt-only mode without a key; direct Kimi
answers with one.

**Tests:** `cd backend && .venv/Scripts/python -m pytest tests/` (37 tests:
signal rules, recurrence, LLM sentiment parsing, ingestion dedup).
