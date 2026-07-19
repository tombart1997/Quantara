"""Signal endpoints (read-only — signals are produced by the engine, step 4)."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Signal
from app.schemas import SignalRead
from app.services.signals import run as run_engine

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


def to_read(signal: Signal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        asset_id=signal.asset_id,
        asset_ticker=signal.asset.ticker if signal.asset else None,
        name=signal.name,
        reasons=signal.reasons,
        score=signal.score,
        created_at=signal.created_at,
    )


@router.get("", response_model=list[SignalRead])
def list_signals(
    asset_id: int | None = None,
    days: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[SignalRead]:
    """List signals, newest first. `days` looks back for history
    (daily snapshots persist — recompute only replaces the current day)."""
    stmt = (
        select(Signal)
        .options(joinedload(Signal.asset))
        .order_by(Signal.created_at.desc())
        .limit(limit)
    )
    if asset_id is not None:
        stmt = stmt.where(Signal.asset_id == asset_id)
    if days is not None:
        stmt = stmt.where(Signal.created_at >= datetime.now() - timedelta(days=days))
    return [to_read(s) for s in db.scalars(stmt)]


@router.post("/recompute", response_model=list[SignalRead])
def recompute_signals(db: Session = Depends(get_db)) -> list[SignalRead]:
    """Re-run the rule engine over all assets.

    Replaces today's signals, so this is safe to call repeatedly. Returns the
    freshly created signals with their full reason lists.
    """
    return [to_read(s) for s in run_engine(db)]
