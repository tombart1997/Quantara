"""Weather endpoints — SST world-map grids (NOAA OISST, disk-cached)."""
from __future__ import annotations

import threading
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.services.sst import (
    PRECACHE_STATE,
    SstNotAvailable,
    cached_dates,
    get_sst,
    latest_available_date,
    latest_nrt_date,
    precache,
)

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


@router.get("/sst/latest")
def sst_latest() -> dict:
    """Latest published dates + which days are already cached.

    latest = final product (~2 weeks behind, cached forever).
    latest_nrt = near-real-time preliminary product (~1-2 days behind).
    """
    return {
        "latest": latest_available_date(),
        "latest_nrt": latest_nrt_date(),
        "cached": cached_dates(),
    }


@router.get("/sst")
def sst_grid(day: date = Query(..., description="YYYY-MM-DD")) -> dict:
    """Strided global SST grid for one day.

    First request for a date downloads it from NOAA (~5-20s); every later
    request is served from the disk cache instantly.
    """
    try:
        return get_sst(day)
    except SstNotAvailable as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"SST upstream error: {e}") from e


@router.post("/sst/precache")
def start_precache(days: int = Query(default=90, ge=1, le=1500)) -> dict:
    """Start a background download of recent history (cached days are
    skipped). Poll /sst/precache-status for progress."""
    if PRECACHE_STATE["running"]:
        return {"started": False, "reason": "already running", **PRECACHE_STATE}
    thread = threading.Thread(target=precache, args=(days,), daemon=True)
    thread.start()
    return {"started": True, "days": days}


@router.get("/sst/precache-status")
def precache_status() -> dict:
    """Progress of the background pre-cache."""
    return {**PRECACHE_STATE, "cached_total": len(cached_dates())}
