"""FastAPI application entry point.

Run from the backend/ directory:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import ai, assets, dashboard, events, journal, news, signals

settings = get_settings()

app = FastAPI(
    title="Quantara Dashboard API",
    version="0.1.0",
    description="Research and decision-support tool — not a trading bot.",
)

app.include_router(ai.router)

app.include_router(assets.router)
app.include_router(events.router)
app.include_router(news.router)
app.include_router(journal.router)
app.include_router(signals.router)
app.include_router(dashboard.router)

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
