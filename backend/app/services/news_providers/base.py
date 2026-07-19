"""News provider abstraction.

Same philosophy as the market-data providers: the rest of the app depends on
this protocol, never on a specific news source. Adding NewsAPI, Alpha
Vantage, or another RSS source later means adding one file and registering it
in the factory — ingestion, linking, and the signal engine stay untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class NewsItem:
    """One raw news article, vendor-neutral. Sentiment is scored separately."""

    source: str
    headline: str
    url: str
    summary: str | None
    published_at: datetime


class NewsProvider(Protocol):
    """Contract every news provider must fulfill."""

    def fetch_news(self, query: str, max_items: int = 20) -> list[NewsItem]:
        """Return recent articles matching the query, newest first."""
        ...
