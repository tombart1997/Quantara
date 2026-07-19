"""News endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import NewsArticle
from app.schemas import NewsRead
from app.services.news_ingestion import ingest_news, rescore_sentiment

router = APIRouter(prefix="/api/v1/news", tags=["news"])


def to_read(article: NewsArticle) -> NewsRead:
    return NewsRead(
        id=article.id,
        source=article.source,
        headline=article.headline,
        url=article.url,
        summary=article.summary,
        published_at=article.published_at,
        sentiment=article.sentiment,
        tickers=[a.ticker for a in article.assets],
    )


@router.get("", response_model=list[NewsRead])
def list_news(
    asset_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[NewsRead]:
    stmt = (
        select(NewsArticle)
        .options(joinedload(NewsArticle.assets))
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
    )
    if asset_id is not None:
        stmt = stmt.where(NewsArticle.assets.any(id=asset_id))
    return [to_read(a) for a in db.scalars(stmt).unique()]


@router.post("/refresh")
def refresh_news(db: Session = Depends(get_db)) -> dict[str, int]:
    """Fetch the latest news from the configured provider for every asset.

    Already-known articles (by URL) are skipped. Returns {ticker: new count}.
    """
    return ingest_news(db)


@router.post("/rescore-sentiment")
def rescore(limit: int = 100, db: Session = Depends(get_db)) -> dict[str, int]:
    """Re-score sentiment for the most recent articles.

    Useful after adding a Kimi API key: existing keyword-scored (or
    unscored) articles get proper LLM scores.
    """
    return rescore_sentiment(db, limit=limit)
