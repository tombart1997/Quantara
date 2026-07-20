"""Automatic data refresh — keeps prices, events, news, and signals current.

Design:
  - `refresh_all()` orchestrates one full pass in the right order (signals
    LAST, since they consume prices/news/events).
  - An asyncio loop started with the FastAPI lifespan calls it every
    REFRESH_INTERVAL_MINUTES. All ingestion is sync SQLAlchemy, so the loop
    offloads to a thread to avoid blocking the event loop.
  - STATE tracks the last run for the /refresh-status endpoint, so the UI
    can show data freshness instead of letting data go silently stale.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.event_ingestion import ingest_events
from app.services.news_ingestion import ingest_news
from app.services.price_ingestion import refresh_prices
from app.services.signals import run as run_signal_engine
from app.services.sst import download_new_days

logger = logging.getLogger(__name__)

# Observable refresh state (single-process app -> module state is fine).
STATE: dict = {"last_run": None, "last_result": None, "running": False}

# Incremental refreshes only pull recent days; the initial 365-day backfill
# was done once by seed/import. Keeps the periodic pass fast.
INCREMENTAL_PRICE_DAYS = 10


def refresh_all(price_days: int = INCREMENTAL_PRICE_DAYS) -> dict:
    """One full refresh pass. Safe to call concurrently with requests:
    every ingestion step is idempotent (dedup by URL / date / title)."""
    if STATE["running"]:
        return {"skipped": "refresh already running"}
    STATE["running"] = True
    started = datetime.now()
    try:
        with SessionLocal() as db:
            result = {
                "prices": refresh_prices(db, days=price_days),
                "events": ingest_events(db),
                "news": ingest_news(db),
                "signals": len(run_signal_engine(db)),
            }
        # Keep the SST cache current as new days get published (usually 0-1
        # files per cycle; skips everything already cached).
        try:
            result["sst"] = download_new_days()
        except Exception:
            logger.exception("SST incremental update failed")
        STATE["last_run"] = started.isoformat(timespec="seconds")
        STATE["last_result"] = result
        logger.info("Refresh complete in %.1fs: %s",
                    (datetime.now() - started).total_seconds(), result)
        return result
    except Exception:
        logger.exception("Refresh failed")
        STATE["last_result"] = {"error": "refresh failed — see server log"}
        raise
    finally:
        STATE["running"] = False


async def refresh_loop() -> None:
    """Periodically refresh in the background until cancelled."""
    interval = get_settings().refresh_interval_minutes * 60
    while True:
        try:
            await asyncio.to_thread(refresh_all)
        except Exception:
            logger.exception("Scheduled refresh iteration failed")
        await asyncio.sleep(interval)
