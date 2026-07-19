"""Thesis review: pair journal entries with what the market actually did.

Nothing here is stored — entry-vs-current performance is computed from
price history on read, so entries never need syncing with prices.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JournalEntry, PriceHistory

# Entries older than this many days get flagged for review.
REVIEW_AFTER_DAYS = 30


def _close_on_or_before(db: Session, asset_id: int, day: date) -> float | None:
    return db.scalar(
        select(PriceHistory.close)
        .where(PriceHistory.asset_id == asset_id, PriceHistory.date <= day)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )


def _latest_close(db: Session, asset_id: int) -> float | None:
    return db.scalar(
        select(PriceHistory.close)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )


def build_review(db: Session) -> list[dict]:
    """Every journal entry, oldest first, with outcome metrics attached."""
    review = []
    for entry in db.scalars(select(JournalEntry).order_by(JournalEntry.date)):
        entry_close = _close_on_or_before(db, entry.asset_id, entry.date)
        current_close = _latest_close(db, entry.asset_id)
        change_pct = None
        if entry_close and current_close:
            change_pct = round((current_close - entry_close) / entry_close * 100, 2)
        days_open = (date.today() - entry.date).days
        review.append({
            "entry": entry,
            "asset_ticker": entry.asset.ticker if entry.asset else None,
            "entry_close": entry_close,
            "current_close": current_close,
            "change_pct": change_pct,
            "days_open": days_open,
            "review_due": days_open >= REVIEW_AFTER_DAYS,
        })
    return review
