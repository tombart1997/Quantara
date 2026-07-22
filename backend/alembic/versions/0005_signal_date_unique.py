"""Add signal_date + uniqueness so duplicate signals are impossible.

The duplicate root cause was concurrent engine runs from multiple backend
processes interleaving delete/insert. A UNIQUE(asset_id, name, signal_date)
constraint makes the database itself the arbiter: the losing process gets an
IntegrityError (handled in the engine), never a duplicate row.

Revision ID: 0005_signal_date_unique
Revises: 0004_event_recurrence
Create Date: 2026-07-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_signal_date_unique"
down_revision: str | None = "0004_event_recurrence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("signal_date", sa.Date(), nullable=True))
    # Backfill from created_at for existing rows.
    op.execute("UPDATE signals SET signal_date = date(created_at) WHERE signal_date IS NULL")
    op.create_index(
        "uq_signals_asset_name_date",
        "signals",
        ["asset_id", "name", "signal_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_signals_asset_name_date", "signals")
    op.drop_column("signals", "signal_date")
