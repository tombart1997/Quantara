"""Sea surface temperature (SST) grids from NOAA OISST via ERDDAP.

Free, no API key. Daily global product at 0.25° resolution; we pull a
strided grid (every 8th cell -> 90 x 180 points) which is plenty for a
world-map overlay.

Caching discipline (per product decision): each calendar day is fetched
exactly ONCE and stored on disk forever — historical SST never changes.
Cache lives in backend/data/sst/ (gitignored).
"""
from __future__ import annotations

import csv
import io
import logging
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "sst"
STRIDE = 8
LATEST_TTL = 3600  # re-check the latest available date hourly
# v2: cache files now carry both absolute SST and anomaly grids.
CACHE_SUFFIX = ".v2.json"

_latest_cache: tuple[float, str] | None = None


class SstNotAvailable(Exception):
    """Raised when NOAA has no data for the requested date."""


def _cache_path(day: date) -> Path:
    return CACHE_DIR / f"{day.isoformat()}{CACHE_SUFFIX}"


def latest_available_date() -> str:
    """The most recent day NOAA has published (OISST lags real time)."""
    global _latest_cache
    now = time.time()
    if _latest_cache and now - _latest_cache[0] < LATEST_TTL:
        return _latest_cache[1]
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{ERDDAP}.json?sst[(last)][(0.0)][(0)][(0)]")
        resp.raise_for_status()
        rows = resp.json()["table"]["rows"]
    latest = rows[0][0][:10]  # "2026-07-04T12:00:00Z" -> date
    _latest_cache = (now, latest)
    return latest


def _fetch_grid(day: date) -> str:
    """Download one day's strided grid (absolute SST + anomaly) from ERDDAP."""
    constraints = (
        f"[({day.isoformat()}T12:00:00Z)][(0.0)]"
        f"[(-89.875):{STRIDE}:(89.875)][(0.125):{STRIDE}:(359.875)]"
    )
    url = f"{ERDDAP}.csv0?sst{constraints},anom{constraints}"
    with httpx.Client(timeout=90.0) as client:
        resp = client.get(url)
        if resp.status_code == 404:
            raise SstNotAvailable(f"no SST data for {day.isoformat()}")
        resp.raise_for_status()
        return resp.text


def _parse_grid(csv_text: str, day: date) -> dict:
    """CSV -> compact JSON grids (absolute + anomaly). Lon: -180..180."""
    lats: list[float] = []
    lons: list[float] = []
    sst_by_lat: dict[float, dict[float, float]] = {}
    anom_by_lat: dict[float, dict[float, float]] = {}
    for record in csv.reader(io.StringIO(csv_text)):
        if len(record) < 6:
            continue
        lat, lon_raw, sst, anom = float(record[2]), float(record[3]), record[4], record[5]
        lon = lon_raw - 360 if lon_raw > 180 else lon_raw
        if lat not in lats:
            lats.append(lat)
        if lon not in lons:
            lons.append(lon)
        if sst != "NaN":
            sst_by_lat.setdefault(lat, {})[lon] = float(sst)
        if anom != "NaN":
            anom_by_lat.setdefault(lat, {})[lon] = float(anom)
    lats.sort()
    lons.sort()
    # Row-major grids with nulls for land/ice.
    grid = [[sst_by_lat.get(lat, {}).get(lon) for lon in lons] for lat in lats]
    anom = [[anom_by_lat.get(lat, {}).get(lon) for lon in lons] for lat in lats]
    return {"date": day.isoformat(), "lats": lats, "lons": lons,
            "grid": grid, "anom": anom,
            "source": "NOAA OISST v2.1 (daily, 0.25°, strided)"}


def get_sst(day: date) -> dict:
    """SST grid for one day — disk-cached, fetched once ever."""
    path = _cache_path(day)
    if path.exists():
        import json
        return json.loads(path.read_text())
    raw = _fetch_grid(day)
    grid = _parse_grid(raw, day)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    import json
    path.write_text(json.dumps(grid))
    logger.info("Cached SST grid for %s (%d points)", day.isoformat(),
                sum(1 for row in grid["grid"] for v in row if v is not None))
    return grid


def cached_dates() -> list[str]:
    """Which days are already in the disk cache."""
    if not CACHE_DIR.exists():
        return []
    return sorted(p.name[: -len(CACHE_SUFFIX)] for p in CACHE_DIR.glob(f"*{CACHE_SUFFIX}"))


def download_new_days() -> dict:
    """Incremental update: fetch any published days not yet cached.

    Called by the scheduler every refresh cycle — this is what keeps the
    cache current as time passes (OISST publishes daily, ~2 weeks lag).
    """
    latest = date.fromisoformat(latest_available_date())
    cached = set(cached_dates())
    # Only look back a few days beyond the newest cached file — NOAA can
    # publish several days at once after a gap.
    newest_cached = max(cached) if cached else (latest - timedelta(days=14)).isoformat()
    start = date.fromisoformat(newest_cached)
    added = []
    day = start
    while day <= latest:
        if day.isoformat() not in cached:
            try:
                get_sst(day)
                added.append(day.isoformat())
            except Exception as e:
                logger.warning("SST incremental fetch failed for %s: %s", day, e)
        day += timedelta(days=1)
    return {"added": added, "latest_available": latest.isoformat()}


# --- Background pre-cache -----------------------------------------------------
# Downloads recent history in a worker pool so the timeline is instant.
PRECACHE_STATE: dict = {"running": False, "done": 0, "total": 0, "current": None}


def precache(days: int) -> None:
    """Fetch the last `days` days (skipping cached ones). Runs in a thread."""
    from concurrent.futures import ThreadPoolExecutor
    from datetime import timedelta

    latest = date.fromisoformat(latest_available_date())
    wanted = [latest - timedelta(days=i) for i in range(days)]
    missing = [d for d in wanted if not _cache_path(d).exists()]

    PRECACHE_STATE.update(running=True, done=0, total=len(missing), current=None)
    try:
        def fetch_one(day: date) -> None:
            PRECACHE_STATE["current"] = day.isoformat()
            try:
                get_sst(day)
            except Exception as e:  # keep going; a failed day stays uncached
                logger.warning("Precache failed for %s: %s", day, e)
            PRECACHE_STATE["done"] += 1

        # Two workers: polite to ERDDAP, ~2x faster than sequential.
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(fetch_one, missing))
    finally:
        PRECACHE_STATE["running"] = False
        PRECACHE_STATE["current"] = None
