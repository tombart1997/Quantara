"""News articles and their many-to-many link to assets.

An article often mentions several assets (e.g. an AI-sector piece mentioning
NVDA and AMD), so the link is a proper association table rather than a FK.

`sentiment` is nullable on purpose: it will be filled later by an AI/NLP
pipeline. Raw articles are stored without it until then.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset

# Association table: no extra columns needed, so a plain Table (not a model).
news_asset = Table(
    "news_asset",
    Base.metadata,
    Column("news_id", ForeignKey("news_articles.id"), primary_key=True),
    Column("asset_id", ForeignKey("assets.id"), primary_key=True),
)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100))       # e.g. "Reuters", "ICCO"
    headline: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    summary: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    sentiment: Mapped[float | None] = mapped_column(Float)  # -1.0 .. +1.0, filled later
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assets: Mapped[list[Asset]] = relationship(secondary=news_asset, back_populates="news_articles")
