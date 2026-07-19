"""Initial schema: users, assets, price_history, events, news, journal, signals.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum("STOCK", "COMMODITY", "ETF", "INDEX", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("in_watchlist", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_assets_ticker", "assets", ["ticker"], unique=True)

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.UniqueConstraint("asset_id", "date", name="uq_price_asset_date"),
    )
    op.create_index("ix_price_history_asset_id", "price_history", ["asset_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "EARNINGS", "ECONOMIC_RELEASE", "COMPANY_ANNOUNCEMENT",
                "COMMODITY_REPORT", "WEATHER",
                native_enum=False, length=30,
            ),
            nullable=False,
        ),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_events_asset_id", "events", ["asset_id"])
    op.create_index("ix_events_date", "events", ["date"])

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("sentiment", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("url", name="uq_news_articles_url"),
    )
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])

    op.create_table(
        "news_asset",
        sa.Column("news_id", sa.Integer(), sa.ForeignKey("news_articles.id"), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
    )

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=True),
        sa.Column("risk", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_journal_entries_asset_id", "journal_entries", ["asset_id"])

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_signals_asset_id", "signals", ["asset_id"])


def downgrade() -> None:
    op.drop_table("signals")
    op.drop_table("journal_entries")
    op.drop_table("news_asset")
    op.drop_table("news_articles")
    op.drop_table("events")
    op.drop_table("price_history")
    op.drop_table("assets")
    op.drop_table("users")
