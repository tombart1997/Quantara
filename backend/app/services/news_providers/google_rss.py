"""Google News RSS provider — no API key required.

Uses the public RSS search endpoint. Articles are fetched per asset with a
search query (stored on the asset as `news_keywords`), which beats most free
API tiers for commodity coverage (ICCO, weather, crop reports).

Note: article URLs are Google redirect links, which is fine for a personal
research tool — they still open the original article in a browser.
"""
from __future__ import annotations

import calendar
import logging
from datetime import datetime, timezone

import feedparser

from app.services.news_providers.base import NewsItem, NewsProvider

logger = logging.getLogger(__name__)

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Politeness: identify ourselves instead of posing as a browser.
USER_AGENT = "investing-dashboard/0.1 (personal research tool)"


class GoogleNewsRssProvider(NewsProvider):
    def fetch_news(self, query: str, max_items: int = 20) -> list[NewsItem]:
        url = RSS_URL.format(query=query.replace(" ", "+"))
        feed = feedparser.parse(url, agent=USER_AGENT)
        items: list[NewsItem] = []
        for entry in feed.entries[:max_items]:
            published = None
            if getattr(entry, "published_parsed", None):
                published = calendar.timegm(entry.published_parsed)
            if published is None:
                continue  # undated articles are useless for a timeline
            items.append(
                NewsItem(
                    source=getattr(getattr(entry, "source", None), "title", "Google News"),
                    headline=entry.title,
                    url=entry.link,
                    summary=None,  # RSS summaries are HTML boilerplate; skipped on purpose
                    published_at=datetime.fromtimestamp(published, tz=timezone.utc).replace(tzinfo=None),
                )
            )
        logger.info("Fetched %d articles for query %r", len(items), query)
        return items
