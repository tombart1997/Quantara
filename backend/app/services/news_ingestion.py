"""News ingestion: fetch -> dedupe -> score sentiment -> link to assets.

Deduplication relies on the unique constraint on NewsArticle.url: anything
already stored is skipped, so re-running ingestion is cheap and safe.

Sentiment is scored in ONE batched pass over all new articles (LLM when
configured, keyword fallback otherwise) — not per article — to keep the
number of API calls low.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, NewsArticle
from app.services.llm_sentiment import score_headlines
from app.services.news_providers import get_news_provider

logger = logging.getLogger(__name__)


def ingest_news(db: Session, max_per_asset: int = 15) -> dict[str, int]:
    """Fetch news for every asset and store new articles.

    Returns {ticker: number_of_new_articles} for visibility.
    """
    provider = get_news_provider()
    existing_urls = set(db.scalars(select(NewsArticle.url)))
    result: dict[str, int] = {}
    pending: list[NewsArticle] = []

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
                sentiment=None,  # scored in the batch pass below
                assets=[asset],
            )
            db.add(article)
            existing_urls.add(item.url)
            pending.append(article)
            new_count += 1
        result[asset.ticker] = new_count

    if pending:
        scores = score_headlines([a.headline for a in pending])
        for article, score in zip(pending, scores, strict=True):
            article.sentiment = score

    db.commit()
    return result


def rescore_sentiment(db: Session, limit: int = 100) -> dict[str, int]:
    """Re-score the most recent articles (e.g. after adding an API key)."""
    articles = list(db.scalars(
        select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(limit)
    ))
    if not articles:
        return {"rescored": 0}
    scores = score_headlines([a.headline for a in articles])
    for article, score in zip(articles, scores, strict=True):
        article.sentiment = score
    db.commit()
    return {"rescored": len(articles)}
