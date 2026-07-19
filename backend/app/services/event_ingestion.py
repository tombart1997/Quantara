"""Event ingestion: fetch from all providers, dedupe, store.

Dedupe key is (asset, event date, title): provider data is refreshed in
place conceptually, so anything already stored with the same key is skipped.
Manually created events are never touched — ingestion only adds.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, Event
from app.services.event_providers import get_event_providers

logger = logging.getLogger(__name__)


def ingest_events(db: Session) -> dict[str, int]:
    """Fetch upcoming events from all providers. Returns {'added': n, 'skipped': n}."""
    tickers = list(db.scalars(select(Asset.ticker)))
    items = []
    for provider in get_event_providers():
        items.extend(provider.fetch_events(tickers))

    asset_ids = {a.ticker: a.id for a in db.scalars(select(Asset))}
    existing = {
        (e.asset_id, e.date, e.title) for e in db.scalars(select(Event))
    }

    added = skipped = 0
    for item in items:
        asset_id = asset_ids.get(item.ticker) if item.ticker else None
        if item.ticker and asset_id is None:
            continue  # provider returned a ticker we don't track
        key = (asset_id, item.date, item.title)
        if key in existing:
            skipped += 1
            continue
        db.add(Event(
            asset_id=asset_id,
            event_type=item.event_type,
            date=item.date,
            title=item.title,
            description=item.description,
            importance=item.importance,
        ))
        existing.add(key)
        added += 1
    db.commit()
    logger.info("Event ingestion: %d added, %d skipped", added, skipped)
    return {"added": added, "skipped": skipped}
