"""Macro/economic calendar via Finnhub — OPTIONAL, needs a free API key.

Active only when FINNHUB_API_KEY is set. Produces macro events
(asset_id NULL): CPI, FOMC, jobs reports, etc. Free tier:
https://finnhub.io/register
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import httpx

from app.core.config import get_settings
from app.models.enums import EventType
from app.services.event_providers.base import EventItem, EventProvider

logger = logging.getLogger(__name__)

API_URL = "https://finnhub.io/api/v1/calendar/economic"

_IMPACT_TO_IMPORTANCE = {"high": 5, "medium": 3, "low": 1}


class FinnhubCalendarProvider(EventProvider):
    def fetch_events(self, tickers: list[str]) -> list[EventItem]:
        key = get_settings().finnhub_api_key
        if not key:
            return []
        params = {
            "from": date.today().isoformat(),
            "to": (date.today() + timedelta(days=60)).isoformat(),
            "token": key,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(API_URL, params=params)
                resp.raise_for_status()
                entries = resp.json().get("economicCalendar", [])
        except Exception as e:
            logger.warning("Finnhub economic calendar fetch failed: %s", e)
            return []

        items: list[EventItem] = []
        for e in entries:
            try:
                when = datetime.fromisoformat(e["date"].replace("Z", "+00:00")).replace(tzinfo=None)
            except (KeyError, ValueError):
                continue
            country = e.get("country", "")
            items.append(EventItem(
                ticker=None,  # macro event, not tied to one asset
                event_type=EventType.ECONOMIC_RELEASE,
                date=when,
                title=f"{e.get('event', 'Economic release')} ({country})" if country else e.get("event", "Economic release"),
                description=f"Estimate: {e.get('estimate')}" if e.get("estimate") is not None else None,
                importance=_IMPACT_TO_IMPORTANCE.get(str(e.get("impact", "")).lower(), 2),
            ))
        return items
