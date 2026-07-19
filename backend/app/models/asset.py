"""Asset model — a stock, commodity, ETF or index the user researches."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AssetType

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.journal_entry import JournalEntry
    from app.models.news_article import NewsArticle
    from app.models.price_history import PriceHistory
    from app.models.signal import Signal


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    exchange: Mapped[str] = mapped_column(String(50))      # e.g. NASDAQ, ICE
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, native_enum=False, length=20, validate_strings=True)
    )
    sector: Mapped[str | None] = mapped_column(String(100))  # e.g. Semiconductors, Softs
    # Market region for grouping in the UI: US / EUROPE / ASIA / GLOBAL.
    region: Mapped[str | None] = mapped_column(String(20))
    # 1.0 = normal asset; 2.0 = 2x leveraged product, etc.
    leverage: Mapped[float] = mapped_column(Float, server_default="1.0")
    # Search query used by news providers ("cocoa price ICE" beats "Cocoa
    # Futures" as a query). Falls back to the asset name when NULL.
    news_keywords: Mapped[str | None] = mapped_column(String(200))
    # Single-user watchlist for now: a flag on the asset is simpler than a
    # join table. Promote to a table if multi-user watchlists are ever needed.
    in_watchlist: Mapped[bool] = mapped_column(Boolean, server_default=false())

    prices: Mapped[list[PriceHistory]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", order_by="PriceHistory.date"
    )
    events: Mapped[list[Event]] = relationship(back_populates="asset")
    news_articles: Mapped[list[NewsArticle]] = relationship(
        secondary="news_asset", back_populates="assets"
    )
    journal_entries: Mapped[list[JournalEntry]] = relationship(back_populates="asset")
    signals: Mapped[list[Signal]] = relationship(back_populates="asset")
