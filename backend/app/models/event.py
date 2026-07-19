"""Event model — calendar entries linked to assets (or macro-wide).

asset_id is nullable: macro events (CPI, FOMC) affect everything and are not
tied to a single asset.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EventType

if TYPE_CHECKING:
    from app.models.asset import Asset


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), index=True)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False, length=30, validate_strings=True)
    )
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    # 1 (minor) to 5 (market-moving) — lets the UI and signal engine weigh events.
    importance: Mapped[int] = mapped_column(Integer, default=3)
    # Recurrence of a manually created series. Occurrences are materialized
    # as real rows sharing one series_id, so downstream queries stay simple.
    recurrence: Mapped[str] = mapped_column(String(12), server_default="NONE")
    series_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset | None] = relationship(back_populates="events")
