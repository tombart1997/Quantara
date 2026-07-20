"""Ripple Engine endpoints.

GET  /api/v1/ripple/state    -> full live state (signals, exposure, portfolio)
POST /api/v1/ripple/scenario -> state recomputed with activation overrides
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ripple.engine import compute_state

router = APIRouter(prefix="/api/v1/ripple", tags=["ripple"])


class ScenarioRequest(BaseModel):
    # SIGNAL_ID -> activation 0-100. Replaces measured activations;
    # unlisted signals are forced dormant (clean "what-if").
    activations: dict[str, float] = Field(min_length=1)


@router.get("/state")
def ripple_state(db: Session = Depends(get_db)) -> dict:
    """Live ripple state: measured signal activations, ranked exposure per
    signal, per-asset score decomposition, and the watchlist overlay."""
    return compute_state(db)


@router.post("/scenario")
def ripple_scenario(payload: ScenarioRequest, db: Session = Depends(get_db)) -> dict:
    """What-if simulation: only the given signals are active, at the given
    activation levels. Conflicts are shown per asset, never netted silently.
    """
    clipped = {k: max(0.0, min(100.0, v)) for k, v in payload.activations.items()}
    return compute_state(db, overrides={k: {"activation": v, "detail": "scenario override"}
                                        for k, v in clipped.items()})
