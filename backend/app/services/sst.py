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
ERDDAP_NRT = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg_LonPM180"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "sst"
STRIDE = 8
LATEST_TTL = 3600  # re-check the latest available date hourly
# v2: cache files now carry both absolute SST and anomaly grids.
CACHE_SUFFIX = ".v2.json"
# NRT (near-real-time, preliminary): same format, ~1-2 day lag, but files
# get REVISED by NOAA -> short cache TTL instead of cache-forever.
NRT_SUFFIX = ".nrt.v2.json"
NRT_CACHE_TTL = 24 * 3600

_latest_cache: tuple[float, str] | None = None
_latest_nrt_cache: tuple[float, str] | None = None


class SstNotAvailable(Exception):
    """Raised when NOAA has no data for the requested date."""


def _cache_path(day: date) -> Path:
    return CACHE_DIR / f"{day.isoformat()}{CACHE_SUFFIX}"


def _nrt_path(day: date) -> Path:
    return CACHE_DIR / f"{day.isoformat()}{NRT_SUFFIX}"


def _latest_from(base_url: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{base_url}.json?sst[(last)][(0.0)][(0)][(0)]")
        resp.raise_for_status()
        return resp.json()["table"]["rows"][0][0][:10]


def latest_available_date() -> str:
    """The most recent day NOAA has published (final OISST lags ~2 weeks)."""
    global _latest_cache
    now = time.time()
    if _latest_cache and now - _latest_cache[0] < LATEST_TTL:
        return _latest_cache[1]
    _latest_cache = (now, _latest_from(ERDDAP))
    return _latest_cache[1]


def latest_nrt_date() -> str:
    """The most recent NRT (preliminary) day — usually yesterday."""
    global _latest_nrt_cache
    now = time.time()
    if _latest_nrt_cache and now - _latest_nrt_cache[0] < LATEST_TTL:
        return _latest_nrt_cache[1]
    _latest_nrt_cache = (now, _latest_from(ERDDAP_NRT))
    return _latest_nrt_cache[1]


def _fetch_grid(day: date, base_url: str = ERDDAP) -> str:
    """Download one day's strided grid (absolute SST + anomaly) from ERDDAP.

    The final product indexes longitude 0..360, the NRT product -180..180.
    """
    lon_range = "(-179.875):%d:(179.875)" % STRIDE if base_url == ERDDAP_NRT else f"(0.125):{STRIDE}:(359.875)"
    constraints = (
        f"[({day.isoformat()}T12:00:00Z)][(0.0)]"
        f"[(-89.875):{STRIDE}:(89.875)][{lon_range}]"
    )
    url = f"{base_url}.csv0?sst{constraints},anom{constraints}"
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
    """SST grid for one day — final product cached forever; days newer than
    the final product's latest fall back to the NRT (preliminary) product
    with a short cache TTL since NOAA revises those files."""
    import json

    path = _cache_path(day)
    if path.exists():
        return json.loads(path.read_text())

    final_latest = date.fromisoformat(latest_available_date())
    if day <= final_latest:
        grid = _parse_grid(_fetch_grid(day), day)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(grid))
        logger.info("Cached SST grid for %s (final)", day.isoformat())
        return grid

    # --- NRT fallback for the freshest days --------------------------------
    if day > date.fromisoformat(latest_nrt_date()):
        raise SstNotAvailable(f"no SST data for {day.isoformat()} "
                              f"(final latest: {final_latest}, NRT latest: {latest_nrt_date()})")
    nrt_path = _nrt_path(day)
    if nrt_path.exists() and time.time() - nrt_path.stat().st_mtime < NRT_CACHE_TTL:
        return json.loads(nrt_path.read_text())
    grid = _parse_grid(_fetch_grid(day, ERDDAP_NRT), day)
    grid["preliminary"] = True
    grid["source"] = "NOAA OISST v2.1 NRT (preliminary, ~1-2 day lag)"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    nrt_path.write_text(json.dumps(grid))
    logger.info("Cached SST grid for %s (NRT)", day.isoformat())
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
# Bulk downloads use ONE REQUEST PER MONTH-CHUNK instead of one per day —
# ~30x fewer requests, which is the difference between hours and minutes.
PRECACHE_STATE: dict = {"running": False, "done": 0, "total": 0, "current": None}
PRECACHE_WORKERS = 4
CHUNK_DAYS = 31


def _fetch_range_and_cache(days: list[date]) -> None:
    """Fetch a contiguous span in ONE ERDDAP request, write per-day files."""
    import json

    d0, d1 = min(days), max(days)
    constraints = (
        f"[({d0.isoformat()}T12:00:00Z):1:({d1.isoformat()}T12:00:00Z)][(0.0)]"
        f"[(-89.875):{STRIDE}:(89.875)][(0.125):{STRIDE}:(359.875)]"
    )
    url = f"{ERDDAP}.csv0?sst{constraints},anom{constraints}"
    with httpx.Client(timeout=300.0) as client:
        resp = client.get(url)
        resp.raise_for_status()

    # Split rows by day, then reuse the single-day parser per day.
    per_day: dict[str, list[str]] = {}
    for line in resp.text.splitlines():
        if line:
            per_day.setdefault(line[:10], []).append(line)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for day_iso, rows in per_day.items():
        day = date.fromisoformat(day_iso)
        if _cache_path(day).exists():
            continue
        grid = _parse_grid("\n".join(rows), day)
        _cache_path(day).write_text(json.dumps(grid))


def precache(days: int) -> None:
    """Fetch the last `days` days (skipping cached ones). Runs in a thread."""
    from concurrent.futures import ThreadPoolExecutor

    latest = date.fromisoformat(latest_available_date())
    wanted = [latest - timedelta(days=i) for i in range(days)]
    missing = sorted(d for d in wanted if not _cache_path(d).exists())

    # Group consecutive missing days into chunks of up to CHUNK_DAYS days.
    chunks: list[list[date]] = []
    for d in missing:
        if chunks and (d - chunks[-1][-1]).days == 1 and len(chunks[-1]) < CHUNK_DAYS:
            chunks[-1].append(d)
        else:
            chunks.append([d])

    PRECACHE_STATE.update(running=True, done=0, total=len(missing), current=None)
    try:
        def fetch_chunk(chunk: list[date]) -> None:
            PRECACHE_STATE["current"] = f"{chunk[0].isoformat()}..{chunk[-1].isoformat()}"
            try:
                _fetch_range_and_cache(chunk)
            except Exception as e:
                logger.warning("Precache chunk failed for %s: %s",
                               PRECACHE_STATE["current"], e)
            PRECACHE_STATE["done"] += len(chunk)

        with ThreadPoolExecutor(max_workers=PRECACHE_WORKERS) as pool:
            list(pool.map(fetch_chunk, chunks))
    finally:
        PRECACHE_STATE["running"] = False
        PRECACHE_STATE["current"] = None
