"""News provider factory — the single place that decides which source is used."""
from app.services.news_providers.base import NewsProvider
from app.services.news_providers.google_rss import GoogleNewsRssProvider


def get_news_provider() -> NewsProvider:
    # Only one source for now. Later sources (NewsAPI, Alpha Vantage, ...)
    # register here, selectable via a settings value like the market provider.
    return GoogleNewsRssProvider()
