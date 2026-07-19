"""Seed the database with demo data. Idempotent: does nothing if assets exist.

Run from backend/:  python -m app.seed
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models import (
    Asset,
    AssetType,
    Event,
    EventType,
    JournalEntry,
    PriceHistory,
    User,
)
from app.services.providers import get_provider

ASSETS = [
    # --- Stocks ----------------------------------------------------------
    dict(ticker="NVDA", name="NVIDIA Corporation", exchange="NASDAQ",
         asset_type=AssetType.STOCK, sector="Semiconductors", region="US",
         news_keywords="Nvidia stock", in_watchlist=True),
    dict(ticker="AAPL", name="Apple Inc.", exchange="NASDAQ",
         asset_type=AssetType.STOCK, sector="Technology", region="US",
         news_keywords="Apple stock", in_watchlist=False),
    # --- Commodities -----------------------------------------------------
    dict(ticker="CC", name="Cocoa Futures", exchange="ICE",
         asset_type=AssetType.COMMODITY, sector="Softs", region="GLOBAL",
         news_keywords="cocoa price", in_watchlist=True),
    dict(ticker="GC", name="Gold Futures", exchange="COMEX",
         asset_type=AssetType.COMMODITY, sector="Metals", region="GLOBAL",
         news_keywords="gold price", in_watchlist=True),
    dict(ticker="ZW", name="Wheat Futures", exchange="CBOT",
         asset_type=AssetType.COMMODITY, sector="Grains", region="GLOBAL",
         news_keywords="wheat price", in_watchlist=False),
    # --- Indexes ----------------------------------------------------------
    dict(ticker="SPX", name="S&P 500 Index", exchange="S&P",
         asset_type=AssetType.INDEX, sector="Broad Market", region="US",
         news_keywords="S&P 500", in_watchlist=False),
    dict(ticker="N225", name="Nikkei 225", exchange="TSE",
         asset_type=AssetType.INDEX, sector="Broad Market", region="ASIA",
         news_keywords="Nikkei 225", in_watchlist=False),
    dict(ticker="DAX", name="DAX 40", exchange="XETRA",
         asset_type=AssetType.INDEX, sector="Broad Market", region="EUROPE",
         news_keywords="DAX index", in_watchlist=False),
    # --- ETFs (incl. leveraged) -------------------------------------------
    dict(ticker="SPY", name="SPDR S&P 500 ETF", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Broad Market", region="US",
         news_keywords="SPY ETF", in_watchlist=False),
    dict(ticker="NVDL", name="GraniteShares 2x Long NVDA", exchange="NASDAQ",
         asset_type=AssetType.ETF, sector="Leveraged Single Stock", region="US",
         leverage=2.0, news_keywords="Nvidia leveraged ETF", in_watchlist=False),
]

HISTORY_DAYS = 365


def days_from_now(days: int, hour: int = 14) -> datetime:
    """Event timestamps anchored to 'now' so demo data is always upcoming."""
    return (datetime.now() + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Asset).count() > 0:
            print("Database already seeded — skipping.")
            return

        provider = get_provider()

        # --- Assets + price history -------------------------------------
        assets: dict[str, Asset] = {}
        for spec in ASSETS:
            asset = Asset(**spec)
            db.add(asset)
            db.flush()  # get asset.id before adding prices
            assets[asset.ticker] = asset
            for bar in provider.get_daily_history(asset.ticker, HISTORY_DAYS):
                db.add(PriceHistory(
                    asset_id=asset.id, date=bar.date, open=bar.open,
                    high=bar.high, low=bar.low, close=bar.close, volume=bar.volume,
                ))

        # --- Events -------------------------------------------------------
        nvda, cc, gc = assets["NVDA"], assets["CC"], assets["GC"]
        db.add_all([
            Event(asset_id=nvda.id, event_type=EventType.EARNINGS, date=days_from_now(21),
                  title="NVIDIA Q2 earnings report", importance=5,
                  description="Quarterly results; data-center revenue in focus."),
            Event(asset_id=nvda.id, event_type=EventType.COMPANY_ANNOUNCEMENT, date=days_from_now(35),
                  title="NVIDIA at Global AI Conference", importance=3,
                  description="Keynote; potential product announcements."),
            Event(asset_id=nvda.id, event_type=EventType.ECONOMIC_RELEASE, date=days_from_now(10),
                  title="Export regulation announcement", importance=4,
                  description="Expected update on AI chip export rules."),
            Event(asset_id=cc.id, event_type=EventType.COMMODITY_REPORT, date=days_from_now(14),
                  title="ICCO quarterly bulletin", importance=4,
                  description="Supply/demand balance update from the ICCO."),
            Event(asset_id=cc.id, event_type=EventType.COMMODITY_REPORT, date=days_from_now(28),
                  title="West Africa crop estimates", importance=4,
                  description="Mid-crop pod count estimates for Ivory Coast and Ghana."),
            Event(asset_id=cc.id, event_type=EventType.WEATHER, date=days_from_now(7),
                  title="Harmattan season outlook", importance=3,
                  description="Dry wind season can stress cocoa pods in West Africa."),
            Event(asset_id=cc.id, event_type=EventType.COMMODITY_REPORT, date=days_from_now(45),
                  title="ICE cocoa inventory report", importance=3,
                  description="Certified warehouse stocks update."),
            Event(asset_id=gc.id, event_type=EventType.ECONOMIC_RELEASE, date=days_from_now(12),
                  title="FOMC rate decision", importance=5,
                  description="Rate path guidance moves gold."),
            Event(asset_id=None, event_type=EventType.ECONOMIC_RELEASE, date=days_from_now(5),
                  title="US CPI release", importance=5,
                  description="Macro event — affects the whole market."),
        ])

        # --- Default user + example journal entry --------------------------
        # NOTE: no mock news is seeded anymore — real articles come from the
        # news provider (POST /api/v1/news/refresh).
        user = User(email="local@investing-dashboard", display_name="Me")
        db.add(user)
        db.flush()
        db.add(JournalEntry(
            asset_id=cc.id, user_id=user.id, date=datetime.now().date(),
            thesis="Supply shortage may be underestimated.",
            expected_outcome="Higher prices.",
            risk="Demand destruction.",
            confidence=7,
        ))

        db.commit()

        # Run the signal engine once so a fresh dashboard has signals to show.
        from app.services.signals import run as run_signal_engine
        created_signals = run_signal_engine(db)

        print(f"Seeded {len(assets)} assets with {HISTORY_DAYS} days of prices, "
              f"9 events, 1 journal entry, "
              f"{len(created_signals)} signals.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
