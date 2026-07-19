"""News ingestion: fetch -> dedupe -> score sentiment -> link to assets.

Deduplication relies on the unique constraint on NewsArticle.url: anything
already stored is skipped, so re-running ingestion is cheap and safe.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, NewsArticle
from app.services.news_providers import get_news_provider
from app.services.news_providers.sentiment import score_text

logger = logging.getLogger(__name__)


def ingest_news(db: Session, max_per_asset: int = 15) -> dict[str, int]:
    """Fetch news for every asset and store new articles.

    Returns {ticker: number_of_new_articles} for visibility.
    """
    provider = get_news_provider()
    existing_urls = set(db.scalars(select(NewsArticle.url)))
    result: dict[str, int] = {}

    for asset in db.scalars(select(Asset)):
        query = asset.news_keywords or asset.name
        new_count = 0
        for item in provider.fetch_news(query, max_items=max_per_asset):
            if item.url in existing_urls:
                continue
            article = NewsArticle(
                source=item.source,
                headline=item.headline,
                url=item.url,
                summary=item.summary,
                published_at=item.published_at,
                sentiment=score_text(item.headline),
                assets=[asset],
            )
            db.add(article)
            existing_urls.add(item.url)
            new_count += 1
        result[asset.ticker] = new_count
        db.flush()  # per-asset flush keeps a later failure from losing everything
    db.commit()
    return result
