"""Temperature endpoints — location-based weather analysis (Open-Meteo)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.temperature import geocode, get_analysis

router = APIRouter(prefix="/api/v1/temperature", tags=["temperature"])


@router.get("/geocode")
def temperature_geocode(q: str = Query(min_length=2)) -> list[dict]:
    """City/place search. Returns [{name, country, admin1, lat, lon}]."""
    try:
        return geocode(q)
    except Exception as e:
        raise HTTPException(502, f"geocoding upstream error: {e}") from e


@router.get("/analysis")
def temperature_analysis(lat: float, lon: float) -> dict:
    """History (90d) + 16-day ensemble forecast with ±1σ band + 35-day
    climatology for one location."""
    try:
        return get_analysis(lat, lon)
    except Exception as e:
        raise HTTPException(502, f"temperature upstream error: {e}") from e
