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
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
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
    path = CACHE_DIR / f"{_coord_key(lat, lon)}.v2.json"  # v2: + wind/humidity/cloud
    if path.exists() and time.time() - path.stat().st_mtime < ARCHIVE_TTL:
        return json.loads(path.read_text())

    end = date.today() - timedelta(days=5)  # ERA5 lags ~5 days
    start = date(end.year - HISTORY_YEARS, 1, 1)
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": ("temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
                  "wind_speed_10m_max,relative_humidity_2m_mean,cloud_cover_mean"),
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


def _conditions(lat: float, lon: float) -> dict:
    """Current conditions + 16-day daily wind/humidity/cloud/precipitation."""
    key = ("conditions", round(lat, 2), round(lon, 2))
    now = time.time()
    if key in _ensemble_cache and now - _ensemble_cache[key][0] < ENSEMBLE_TTL:
        return _ensemble_cache[key][1]
    params = {
        "latitude": lat, "longitude": lon,
        "current": ("temperature_2m,relative_humidity_2m,cloud_cover,"
                    "wind_speed_10m,wind_direction_10m,wind_gusts_10m"),
        "daily": ("precipitation_probability_max,wind_speed_10m_max,"
                  "wind_gusts_10m_max,wind_direction_10m_dominant,"
                  "relative_humidity_2m_mean,cloud_cover_mean"),
        "forecast_days": FORECAST_DAYS, "timezone": "UTC",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(FORECAST_URL, params=params)
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
    hist_wind = archive["daily"].get("wind_speed_10m_max", [None] * len(times))
    hist_hum = archive["daily"].get("relative_humidity_2m_mean", [None] * len(times))
    hist_cloud = archive["daily"].get("cloud_cover_mean", [None] * len(times))
    history = [
        {"date": t, "mean": m, "max": x, "min": n,
         "wind_max": w, "humidity": h, "cloud": c}
        for t, m, x, n, w, h, c in zip(times, means, tmax, tmin,
                                       hist_wind, hist_hum, hist_cloud,
                                       strict=True)
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

    # --- Current conditions + 16-day daily wind/humidity/cloud -------------
    cond = _conditions(lat, lon)
    cond_daily = cond.get("daily", {})

    def col(name: str) -> list:
        return cond_daily.get(name) or []

    conditions = []
    for i, day in enumerate(col("time")):
        def at(name: str):
            series = col(name)
            return series[i] if i < len(series) else None
        conditions.append({
            "date": day,
            "precip_prob": at("precipitation_probability_max"),
            "wind_max": at("wind_speed_10m_max"),
            "gusts_max": at("wind_gusts_10m_max"),
            "wind_dir": at("wind_direction_10m_dominant"),
            "humidity": at("relative_humidity_2m_mean"),
            "cloud": at("cloud_cover_mean"),
        })
    current = cond.get("current", {})

    return {
        "location": {"lat": lat, "lon": lon,
                     "elevation": archive.get("elevation")},
        "current": {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "cloud": current.get("cloud_cover"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_dir": current.get("wind_direction_10m"),
            "gusts": current.get("wind_gusts_10m"),
        },
        "history": history,
        "forecast": forecast,
        "climatology": climatology,
        "conditions": conditions,
        "sources": ("History: ERA5 reanalysis (Open-Meteo) · Forecast: ICON+GFS "
                    "ensemble mean ±1σ (16 days) · Beyond: 5-year climatology"),
    }
