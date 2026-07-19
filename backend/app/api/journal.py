"""Personal research journal endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Asset, JournalEntry, User
from app.schemas import JournalCreate, JournalRead

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])

# Single-user app: all entries are attributed to one local user row.
DEFAULT_USER_EMAIL = "local@investing-dashboard"


def get_or_create_default_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == DEFAULT_USER_EMAIL))
    if user is None:
        user = User(email=DEFAULT_USER_EMAIL, display_name="Me")
        db.add(user)
        db.flush()
    return user


def to_read(entry: JournalEntry) -> JournalRead:
    return JournalRead(
        id=entry.id,
        asset_id=entry.asset_id,
        asset_ticker=entry.asset.ticker if entry.asset else None,
        date=entry.date,
        thesis=entry.thesis,
        expected_outcome=entry.expected_outcome,
        risk=entry.risk,
        confidence=entry.confidence,
    )


@router.get("", response_model=list[JournalRead])
def list_entries(asset_id: int | None = None, db: Session = Depends(get_db)) -> list[JournalRead]:
    stmt = (
        select(JournalEntry)
        .options(joinedload(JournalEntry.asset))
        .order_by(JournalEntry.date.desc())
    )
    if asset_id is not None:
        stmt = stmt.where(JournalEntry.asset_id == asset_id)
    return [to_read(e) for e in db.scalars(stmt)]


@router.post("", response_model=JournalRead, status_code=201)
def create_entry(payload: JournalCreate, db: Session = Depends(get_db)) -> JournalRead:
    if db.get(Asset, payload.asset_id) is None:
        raise HTTPException(404, f"Unknown asset id {payload.asset_id}")
    entry = JournalEntry(**payload.model_dump(), user_id=get_or_create_default_user(db).id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return to_read(entry)
