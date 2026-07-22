"""Signals produced by the rule-based signal engine.

Transparency is the core requirement: a signal is never just a score.
`reasons` stores the human-readable list of rules that fired, so the UI can
always show *why* something was flagged. No prediction claims — just
observed conditions combined into a 0-100 attention score.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("uq_signals_asset_name_date", "asset_id", "name", "signal_date", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))         # e.g. "Cocoa supply risk increased"
    reasons: Mapped[list] = mapped_column(JSON)            # ["Weather anomaly", "Volume spike", ...]
    score: Mapped[int] = mapped_column(Integer)            # 0..100 attention score
    # The day the signal describes. UNIQUE(asset, name, day) makes duplicate
    # signals impossible even under concurrent engine processes.
    signal_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="signals")
