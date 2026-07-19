"""API schemas (Pydantic).

These define the wire format of the API. They are deliberately separate from
the ORM models: the database shape and the API shape can evolve independently.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssetType, EventType


# --- Assets -----------------------------------------------------------------
class AssetCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    exchange: str = Field(min_length=1, max_length=50)
    asset_type: AssetType
    sector: str | None = None
    region: str | None = None
    leverage: float = Field(default=1.0, gt=0)
    news_keywords: str | None = None
    in_watchlist: bool = False


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    exchange: str
    asset_type: AssetType
    sector: str | None
    region: str | None
    leverage: float
    news_keywords: str | None
    in_watchlist: bool


# --- Prices -------------------------------------------------------------------
class PriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None


# --- Events -------------------------------------------------------------------
class EventCreate(BaseModel):
    asset_id: int | None = None
    event_type: EventType
    date: datetime
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    importance: int = Field(default=3, ge=1, le=5)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int | None
    asset_ticker: str | None = None
    event_type: EventType
    date: datetime
    title: str
    description: str | None
    importance: int


# --- News -----------------------------------------------------------------------
class NewsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    headline: str
    url: str
    summary: str | None
    published_at: datetime
    sentiment: float | None
    tickers: list[str] = []


# --- Journal ---------------------------------------------------------------------
class JournalCreate(BaseModel):
    asset_id: int
    date: date
    thesis: str = Field(min_length=1)
    expected_outcome: str | None = None
    risk: str | None = None
    confidence: int = Field(ge=1, le=10)


class JournalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    asset_ticker: str | None = None
    date: date
    thesis: str
    expected_outcome: str | None
    risk: str | None
    confidence: int


# --- Signals -----------------------------------------------------------------------
class SignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    asset_ticker: str | None = None
    name: str
    reasons: list[str]
    score: int
    created_at: datetime


# --- Dashboard aggregate --------------------------------------------------------------
class WatchlistItem(BaseModel):
    asset: AssetRead
    latest_close: float | None
    change_pct: float | None  # day-over-day percentage change of the close


class DashboardResponse(BaseModel):
    watchlist: list[WatchlistItem]
    upcoming_events: list[EventRead]
    recent_news: list[NewsRead]
    active_signals: list[SignalRead]
