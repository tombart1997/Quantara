"""Event calendar endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Asset, Event
from app.models.enums import EventType, Recurrence
from app.schemas import EventCreate, EventRead
from app.services.event_ingestion import ingest_events
from app.services.recurrence import OCCURRENCE_COUNT, expand

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def to_read(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        asset_id=event.asset_id,
        asset_ticker=event.asset.ticker if event.asset else None,
        event_type=event.event_type,
        date=event.date,
        title=event.title,
        description=event.description,
        importance=event.importance,
        recurrence=event.recurrence,
        series_id=event.series_id,
    )


@router.get("", response_model=list[EventRead])
def list_events(
    upcoming_only: bool = False,
    asset_id: int | None = None,
    event_type: EventType | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
) -> list[EventRead]:
    stmt = select(Event).options(joinedload(Event.asset)).order_by(Event.date)
    if upcoming_only:
        stmt = stmt.where(Event.date >= datetime.now())
    if asset_id is not None:
        stmt = stmt.where(Event.asset_id == asset_id)
    if event_type is not None:
        stmt = stmt.where(Event.event_type == event_type)
    return [to_read(e) for e in db.scalars(stmt.limit(limit))]


@router.post("", response_model=list[EventRead], status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> list[EventRead]:
    """Create an event — or a whole series when recurrence != NONE.

    Returns all created occurrences (one for a one-off event), so the caller
    knows how much was materialized.
    """
    if payload.asset_id is not None and db.get(Asset, payload.asset_id) is None:
        raise HTTPException(404, f"Unknown asset id {payload.asset_id}")

    count = OCCURRENCE_COUNT.get(payload.recurrence, 1)
    series_id = uuid.uuid4().hex if payload.recurrence != Recurrence.NONE else None
    data = payload.model_dump(exclude={"recurrence", "date"})

    created = []
    for occurrence_date in expand(payload.date, payload.recurrence, count):
        event = Event(**data, date=occurrence_date,
                      recurrence=payload.recurrence.value, series_id=series_id)
        db.add(event)
        created.append(event)
    db.commit()
    for event in created:
        db.refresh(event)
    return [to_read(e) for e in created]


@router.post("/refresh")
def refresh_events(db: Session = Depends(get_db)) -> dict[str, int]:
    """Fetch upcoming events from all configured providers.

    Always includes real earnings dates (Yahoo Finance). Macro events
    (CPI, FOMC, ...) are added when FINNHUB_API_KEY is configured.
    Already-known events are skipped; manually created events are kept.
    """
    return ingest_events(db)


@router.delete("/series/{series_id}")
def delete_series(series_id: str, db: Session = Depends(get_db)) -> dict[str, int]:
    """Delete every occurrence of a recurring series."""
    result = db.execute(delete(Event).where(Event.series_id == series_id))
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, f"Unknown series {series_id!r}")
    return {"deleted": result.rowcount}


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an event (e.g. a manually created one entered by mistake)."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(404, f"Unknown event id {event_id}")
    db.delete(event)
    db.commit()
