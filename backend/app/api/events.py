"""Event calendar endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Asset, Event
from app.models.enums import EventType
from app.schemas import EventCreate, EventRead

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
    )


@router.get("", response_model=list[EventRead])
def list_events(
    upcoming_only: bool = False,
    asset_id: int | None = None,
    event_type: EventType | None = None,
    limit: int = 100,
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


@router.post("", response_model=EventRead, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)) -> EventRead:
    if payload.asset_id is not None and db.get(Asset, payload.asset_id) is None:
        raise HTTPException(404, f"Unknown asset id {payload.asset_id}")
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return to_read(event)
