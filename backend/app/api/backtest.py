"""Backtest endpoint — replayed rule performance over historical prices."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.backtest import run_backtest

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])


@router.get("")
def backtest(tickers: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Replay price-based signal rules over stored price history and report
    forward returns (+5/+10/+20 days) vs the unconditional baseline.

    Optional `tickers=CC,GC` to scope the run. Requires sufficient stored
    history (run POST /assets/refresh-prices?days=800 once for depth).
    """
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    return run_backtest(db, ticker_list)
