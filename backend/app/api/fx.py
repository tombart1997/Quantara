"""Currency matrix endpoint (FX cross rates, server-cached)."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.fx import get_matrix

router = APIRouter(prefix="/api/v1/fx", tags=["fx"])


@router.get("/matrix")
def fx_matrix() -> dict:
    """Bloomberg-style cross-rate matrix for 8 major currencies.

    Cached server-side for 60s, so polling every ~30s from the UI is cheap.
    rates[row][col] = units of COL per 1 ROW; changes_pct is the daily
    change of each cross rate computed from previous closes.
    """
    return get_matrix()
