"""Dashboard aggregate endpoint.

One call returns everything the landing page needs, so the frontend doesn't
have to fan out into five requests on load.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.events import to_read as event_to_read
from app.api.news import to_read as news_to_read
from app.api.signals import to_read as signal_to_read
from app.db.session import get_db
from app.models import Asset, Event, NewsArticle, PriceHistory, Signal
from app.schemas import AssetRead, DashboardResponse, WatchlistItem

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _latest_two_closes(db: Session, asset_id: int) -> tuple[float | None, float | None]:
    stmt = (
        select(PriceHistory.close)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.date.desc())
        .limit(2)
    )
    closes = list(db.scalars(stmt))
    latest = closes[0] if closes else None
    previous = closes[1] if len(closes) > 1 else None
    return latest, previous


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    watchlist: list[WatchlistItem] = []
    for asset in db.scalars(select(Asset).where(Asset.in_watchlist.is_(True)).order_by(Asset.ticker)):
        latest, previous = _latest_two_closes(db, asset.id)
        change_pct = (
            round((latest - previous) / previous * 100, 2)
            if latest is not None and previous
            else None
        )
        watchlist.append(
            WatchlistItem(
                asset=AssetRead.model_validate(asset),
                latest_close=latest,
                change_pct=change_pct,
            )
        )

    upcoming = db.scalars(
        select(Event).where(Event.date >= datetime.now()).order_by(Event.date).limit(10)
    )
    # Recent news only for watchlisted assets — the dashboard is the user's
    # curated view, not a firehose of all 36 tickers.
    recent_news = db.scalars(
        select(NewsArticle)
        .where(NewsArticle.assets.any(Asset.in_watchlist.is_(True)))
        .order_by(NewsArticle.published_at.desc())
        .limit(10)
    ).unique()
    active_signals = db.scalars(
        select(Signal).order_by(Signal.created_at.desc()).limit(10)
    )

    return DashboardResponse(
        watchlist=watchlist,
        upcoming_events=[event_to_read(e) for e in upcoming],
        recent_news=[news_to_read(n) for n in recent_news],
        active_signals=[signal_to_read(s) for s in active_signals],
    )
