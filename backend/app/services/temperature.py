"""Temperature analysis per location — Open-Meteo, free, no API key.

Three data layers, merged into one analysis payload:
  history      ERA5 archive, daily mean/min/max (one call covers 5 years,
               which also feeds climatology)
  forecast     16-day ensemble (per-member series -> mean ± std = CI)
  climatology  5-year same-calendar-day stats for days 17-35, where the
               ensemble can't reach — honest "normal range" instead of
               pretending to forecast a month out

Cache: archive responses are disk-cached per location (24h TTL — ERA5
updates daily); ensemble forecasts in-memory 1h.
"""
from __future__ import annotations

import json
import logging
import statistics
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "temperature"
ARCHIVE_TTL = 24 * 3600
ENSEMBLE_TTL = 3600
HISTORY_YEARS = 5
FORECAST_DAYS = 16
CLIMATOLOGY_DAYS = 35

_ensemble_cache: dict[tuple, tuple[float, dict]] = {}


def _coord_key(lat: float, lon: float) -> str:
    # Round to ~1 km so cache hits are location-meaningful.
    return f"{lat:.2f}_{lon:.2f}"


def _archive(lat: float, lon: float) -> dict:
    """5 years of daily temps in one call (cached 24h on disk)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_coord_key(lat, lon)}.json"
    if path.exists() and time.time() - path.stat().st_mtime < ARCHIVE_TTL:
        return json.loads(path.read_text())

    end = date.today() - timedelta(days=5)  # ERA5 lags ~5 days
    start = date(end.year - HISTORY_YEARS, 1, 1)
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min",
        "timezone": "UTC",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(ARCHIVE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    path.write_text(json.dumps(data))
    return data


def _ensemble(lat: float, lon: float) -> dict:
    key = (round(lat, 2), round(lon, 2))
    now = time.time()
    if key in _ensemble_cache and now - _ensemble_cache[key][0] < ENSEMBLE_TTL:
        return _ensemble_cache[key][1]
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_mean",
        "forecast_days": FORECAST_DAYS, "timezone": "UTC",
        # Two independent model families = more honest spread than one.
        "models": "icon_seamless,gfs_seamless",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(ENSEMBLE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    _ensemble_cache[key] = (now, data)
    return data


def geocode(query: str, count: int = 6) -> list[dict]:
    """City/place search via Open-Meteo geocoding."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(GEOCODE_URL, params={"name": query, "count": count,
                                               "language": "en", "format": "json"})
        resp.raise_for_status()
    results = resp.json().get("results", []) or []
    return [{
        "name": r.get("name"),
        "country": r.get("country"),
        "admin1": r.get("admin1"),
        "lat": r.get("latitude"),
        "lon": r.get("longitude"),
    } for r in results]


def get_analysis(lat: float, lon: float) -> dict:
    """Full temperature analysis for one location."""
    # --- History (from the 5-year archive call) ----------------------------
    archive = _archive(lat, lon)
    times = archive["daily"]["time"]
    means = archive["daily"]["temperature_2m_mean"]
    tmax = archive["daily"]["temperature_2m_max"]
    tmin = archive["daily"]["temperature_2m_min"]

    history_days = 90
    history = [
        {"date": t, "mean": m, "max": x, "min": n}
        for t, m, x, n in zip(times, means, tmax, tmin, strict=True)
        if m is not None
    ][-history_days:]

    # --- Ensemble forecast: mean + spread across members -------------------
    ens = _ensemble(lat, lon)
    ens_daily = ens["daily"]
    member_keys = [k for k in ens_daily if k.startswith("temperature_2m_mean")]
    forecast = []
    for i, day in enumerate(ens_daily["time"]):
        members = [ens_daily[k][i] for k in member_keys
                   if ens_daily[k][i] is not None]
        if not members:
            continue
        mean = statistics.mean(members)
        spread = statistics.stdev(members) if len(members) > 1 else 0.5
        forecast.append({"date": day, "mean": round(mean, 1),
                         "spread": round(max(spread, 0.5), 2)})

    # --- Climatology for days 17-35 (5-year same-calendar stats) -----------
    by_md: dict[str, list[float]] = {}
    for t, m in zip(times, means, strict=True):
        if m is not None:
            by_md.setdefault(t[5:], []).append(m)  # "MM-DD" key
    today = date.today()
    climatology = []
    for offset in range(FORECAST_DAYS, CLIMATOLOGY_DAYS):
        day = today + timedelta(days=offset)
        vals = by_md.get(day.isoformat()[5:], [])
        if vals:
            climatology.append({
                "date": day.isoformat(),
                "mean": round(statistics.mean(vals), 1),
                "std": round(max(statistics.stdev(vals), 0.7), 2) if len(vals) > 1 else 1.0,
            })

    return {
        "location": {"lat": lat, "lon": lon,
                     "elevation": archive.get("elevation")},
        "history": history,
        "forecast": forecast,
        "climatology": climatology,
        "sources": ("History: ERA5 reanalysis (Open-Meteo) · Forecast: ICON+GFS "
                    "ensemble mean ±1σ (16 days) · Beyond: 5-year climatology"),
    }
