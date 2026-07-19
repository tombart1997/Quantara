"""Add region and leverage to assets.

region powers market grouping in the UI (US / Europe / Asia / global);
leverage marks leveraged products (1.0 = unleveraged, 2.0 = 2x, ...).

Revision ID: 0003_region_leverage
Revises: 0002_news_keywords
Create Date: 2026-07-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_region_leverage"
down_revision: str | None = "0002_news_keywords"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("region", sa.String(20), nullable=True))
    op.add_column(
        "assets",
        sa.Column("leverage", sa.Float(), server_default="1.0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("assets", "leverage")
    op.drop_column("assets", "region")
