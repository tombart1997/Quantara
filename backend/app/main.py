"""FastAPI application entry point.

Run from the backend/ directory:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, assets, dashboard, events, fx, journal, news, refresh, ripple, signals, weather
from app.core.config import get_settings
from app.services.scheduler import refresh_loop
from app.services.sst import PRECACHE_STATE, precache

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start the auto-refresh loop with the app; cancel it on shutdown."""
    task = None
    if settings.refresh_enabled:
        task = asyncio.create_task(refresh_loop())
    # Bulk SST history download in the background — cached days are skipped,
    # so this is expensive only the first time the app ever runs.
    if settings.sst_precache_on_startup and not PRECACHE_STATE["running"]:
        threading.Thread(target=precache, args=(settings.sst_precache_days,), daemon=True).start()
    yield
    if task:
        task.cancel()


app = FastAPI(
    title="Quantara Dashboard API",
    version="0.1.0",
    description="Research and decision-support tool — not a trading bot.",
    lifespan=lifespan,
)

app.include_router(ai.router)
app.include_router(assets.router)
app.include_router(events.router)
app.include_router(news.router)
app.include_router(journal.router)
app.include_router(signals.router)
app.include_router(dashboard.router)
app.include_router(refresh.router)
app.include_router(fx.router)
app.include_router(ripple.router)
app.include_router(weather.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
