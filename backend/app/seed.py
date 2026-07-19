"""Seed the database with demo data. Idempotent: does nothing if assets exist.

Run from backend/:  python -m app.seed
"""
from __future__ import annotations

from app.db.session import SessionLocal
from app.models import (
    Asset,
    AssetType,
    PriceHistory,
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

        # NOTE: nothing content-like is seeded anymore — no mock events, no
        # mock news, no example journal entries. Real data comes from the
        # providers (refresh endpoints) and the user's own entries.

        db.commit()

        # Run the signal engine once so a fresh dashboard has signals to show.
        from app.services.signals import run as run_signal_engine
        created_signals = run_signal_engine(db)

        print(f"Seeded {len(assets)} assets with {HISTORY_DAYS} days of prices, "
              f"{len(created_signals)} signals. "
              f"No events/news/journal — use the refresh endpoints for real data.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
