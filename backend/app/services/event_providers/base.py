"""Event provider abstraction.

Same pluggable philosophy as market data and news: the ingestion service
combines events from all configured providers; sources are interchangeable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.enums import EventType


@dataclass(frozen=True)
class EventItem:
    """One upcoming event, vendor-neutral.

    ticker=None marks a macro event (asset_id NULL in the database).
    """

    ticker: str | None
    event_type: EventType
    date: datetime
    title: str
    description: str | None
    importance: int  # 1-5


class EventProvider(Protocol):
    """Contract every event provider must fulfill."""

    def fetch_events(self, tickers: list[str]) -> list[EventItem]:
        """Return upcoming events for the given tickers (or macro events)."""
        ...
