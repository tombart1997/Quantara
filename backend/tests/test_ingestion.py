"""Ingestion dedup tests against an in-memory database."""
from __future__ import annotations

from datetime import datetime

import app.services.news_ingestion as news_ingestion
from app.models import Asset, AssetType, Event, NewsArticle
from app.models.enums import EventType
from app.services.event_ingestion import ingest_events
from app.services.news_ingestion import ingest_news
from app.services.news_providers.base import NewsItem


class FakeNewsProvider:
    def __init__(self, items):
        self._items = items

    def fetch_news(self, query: str, max_items: int = 20):
        return self._items


def _article(n: int) -> NewsItem:
    return NewsItem(
        source="Test", headline=f"Headline {n}",
        url=f"https://test.example/{n}", summary=None,
        published_at=datetime(2026, 7, 19, 9, 0),
    )


def _add_asset(db, ticker="CC"):
    db.add(Asset(ticker=ticker, name="Cocoa", exchange="ICE",
                 asset_type=AssetType.COMMODITY, news_keywords="cocoa"))
    db.commit()


class TestNewsDedup:
    def test_second_ingest_adds_nothing(self, db, monkeypatch):
        _add_asset(db)
        provider = FakeNewsProvider([_article(1), _article(2)])
        monkeypatch.setattr(news_ingestion, "get_news_provider", lambda: provider)

        assert ingest_news(db) == {"CC": 2}
        assert ingest_news(db) == {"CC": 0}  # dedup by URL
        assert db.query(NewsArticle).count() == 2

    def test_articles_linked_to_asset(self, db, monkeypatch):
        _add_asset(db)
        monkeypatch.setattr(news_ingestion, "get_news_provider",
                            lambda: FakeNewsProvider([_article(1)]))
        ingest_news(db)
        article = db.query(NewsArticle).one()
        assert [a.ticker for a in article.assets] == ["CC"]


class TestEventDedup:
    def test_ingestion_never_duplicates(self, db, monkeypatch):
        _add_asset(db)
        # Simulate what the provider layer produces by inserting through the
        # same dedup key twice via two ingest runs with a fake provider.
        import app.services.event_ingestion as event_ingestion
        from app.services.event_providers.base import EventItem

        item = EventItem(ticker="CC", event_type=EventType.COMMODITY_REPORT,
                         date=datetime(2026, 8, 1, 14, 0), title="ICCO bulletin",
                         description=None, importance=4)

        class FakeEventProvider:
            def fetch_events(self, tickers):
                return [item]

        monkeypatch.setattr(event_ingestion, "get_event_providers",
                            lambda: [FakeEventProvider()])
        assert ingest_events(db) == {"added": 1, "skipped": 0}
        assert ingest_events(db) == {"added": 0, "skipped": 1}
        assert db.query(Event).count() == 1
