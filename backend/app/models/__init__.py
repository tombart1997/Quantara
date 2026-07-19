"""Importing this package registers every model on Base.metadata.

Alembic's env.py relies on this for autogenerate support.
"""
from app.models.asset import Asset
from app.models.enums import AssetType, EventType
from app.models.event import Event
from app.models.journal_entry import JournalEntry
from app.models.news_article import NewsArticle, news_asset
from app.models.price_history import PriceHistory
from app.models.signal import Signal
from app.models.user import User

__all__ = [
    "Asset",
    "AssetType",
    "Event",
    "EventType",
    "JournalEntry",
    "NewsArticle",
    "PriceHistory",
    "Signal",
    "User",
    "news_asset",
]
