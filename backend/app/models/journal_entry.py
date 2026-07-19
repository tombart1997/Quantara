"""Personal research journal entries, attached to an asset.

Captures a thesis the way the user actually writes it: what they believe,
what they expect, what could go wrong, and how confident they are.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.user import User


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    thesis: Mapped[str] = mapped_column(Text)
    expected_outcome: Mapped[str | None] = mapped_column(Text)
    risk: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)  # 1..10, validated in the schema layer
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="journal_entries")
    user: Mapped[User] = relationship(back_populates="journal_entries")
