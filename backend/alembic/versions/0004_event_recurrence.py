"""Add recurrence support to events.

recurrence: NONE / WEEKLY / MONTHLY / QUARTERLY / YEARLY.
series_id: links all materialized occurrences of one recurring series.

Revision ID: 0004_event_recurrence
Revises: 0003_region_leverage
Create Date: 2026-07-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_event_recurrence"
down_revision: str | None = "0003_region_leverage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("recurrence", sa.String(12), server_default="NONE", nullable=False),
    )
    op.add_column("events", sa.Column("series_id", sa.String(36), nullable=True))
    op.create_index("ix_events_series_id", "events", ["series_id"])


def downgrade() -> None:
    op.drop_index("ix_events_series_id", "events")
    op.drop_column("events", "series_id")
    op.drop_column("events", "recurrence")
