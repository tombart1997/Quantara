"""Add news_keywords column to assets (per-asset news search query).

Revision ID: 0002_news_keywords
Revises: 0001_initial
Create Date: 2026-07-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_news_keywords"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("news_keywords", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "news_keywords")
