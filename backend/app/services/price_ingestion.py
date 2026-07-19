"""Price ingestion: fetch history from the configured provider and upsert.

The (asset_id, date) unique constraint makes this idempotent: existing days
are updated in place, new days are inserted.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, PriceHistory
from app.services.providers import get_provider

logger = logging.getLogger(__name__)


def refresh_prices(db: Session, days: int = 365, ticker: str | None = None) -> dict[str, int]:
    """Refresh daily prices for all assets (or one ticker).

    Returns {ticker: number_of_bars_stored}. Failures for one asset are
    logged and skipped so a single bad ticker can't break the run.
    """
    provider = get_provider()
    result: dict[str, int] = {}

    stmt = select(Asset)
    if ticker is not None:
        stmt = stmt.where(Asset.ticker == ticker.upper())
    for asset in db.scalars(stmt):
        bars = provider.get_daily_history(asset.ticker, days)
        if not bars:
            result[asset.ticker] = 0
            continue
        existing = {
            p.date: p
            for p in db.scalars(select(PriceHistory).where(PriceHistory.asset_id == asset.id))
        }
        for bar in bars:
            row = existing.get(bar.date)
            if row is None:
                db.add(PriceHistory(
                    asset_id=asset.id, date=bar.date, open=bar.open,
                    high=bar.high, low=bar.low, close=bar.close, volume=bar.volume,
                ))
            else:
                row.open, row.high, row.low, row.close, row.volume = (
                    bar.open, bar.high, bar.low, bar.close, bar.volume,
                )
        result[asset.ticker] = len(bars)
        db.flush()
    db.commit()
    return result
