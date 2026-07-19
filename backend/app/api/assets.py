"""Asset endpoints: list/create assets, watchlist toggle, price history."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Asset, PriceHistory
from app.schemas import AssetCreate, AssetRead, PriceRead
from app.services.price_ingestion import refresh_prices

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(watchlist_only: bool = False, db: Session = Depends(get_db)) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.ticker)
    if watchlist_only:
        stmt = stmt.where(Asset.in_watchlist.is_(True))
    return list(db.scalars(stmt))


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)) -> Asset:
    if db.scalar(select(Asset).where(Asset.ticker == payload.ticker.upper())):
        raise HTTPException(409, f"Asset with ticker {payload.ticker!r} already exists")
    asset = Asset(**payload.model_dump())
    asset.ticker = asset.ticker.upper()
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


# NOTE: declared before /{ticker} so "refresh-prices" isn't parsed as a ticker.
@router.post("/refresh-prices")
def refresh_price_data(
    days: int = 365,
    ticker: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Fetch daily prices from the configured market data provider.

    Upserts into price_history, so re-running is safe. Optionally limited to
    one ticker. Returns {ticker: number_of_bars_stored}.
    """
    return refresh_prices(db, days=days, ticker=ticker)


@router.get("/{ticker}", response_model=AssetRead)
def get_asset(ticker: str, db: Session = Depends(get_db)) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.ticker == ticker.upper()))
    if asset is None:
        raise HTTPException(404, f"Unknown ticker {ticker!r}")
    return asset


@router.post("/{ticker}/watchlist", response_model=AssetRead)
def toggle_watchlist(ticker: str, db: Session = Depends(get_db)) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.ticker == ticker.upper()))
    if asset is None:
        raise HTTPException(404, f"Unknown ticker {ticker!r}")
    asset.in_watchlist = not asset.in_watchlist
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{ticker}/prices", response_model=list[PriceRead])
def get_prices(
    ticker: str,
    days: int = Query(default=365, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> list[PriceHistory]:
    asset = db.scalar(select(Asset).where(Asset.ticker == ticker.upper()))
    if asset is None:
        raise HTTPException(404, f"Unknown ticker {ticker!r}")
    stmt = (
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset.id, PriceHistory.date >= date.today() - timedelta(days=days))
        .order_by(PriceHistory.date)
    )
    return list(db.scalars(stmt))
