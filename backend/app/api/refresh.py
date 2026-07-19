"""Refresh endpoints: manual full refresh + status for the freshness UI."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.scheduler import STATE, refresh_all

router = APIRouter(prefix="/api/v1", tags=["refresh"])


@router.post("/refresh-all")
def trigger_refresh(price_days: int = 10) -> dict:
    """Run one full refresh pass (prices -> events -> news -> signals).

    price_days controls how much price history is pulled (10 = incremental,
    365 = full backfill). The periodic scheduler does this automatically;
    this endpoint backs the UI's 'refresh now' button.
    """
    return refresh_all(price_days=price_days)


@router.get("/refresh-status")
def refresh_status() -> dict:
    """When the last refresh ran and what it did (null = never ran)."""
    return {
        "last_run": STATE["last_run"],
        "last_result": STATE["last_result"],
        "running": STATE["running"],
    }
