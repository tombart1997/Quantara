"""Bulk asset import from a curated universe list.

Run from backend/:  python -m app.import_assets

Adds any UNIVERSE entries that don't exist yet (by ticker) and pulls their
price history from the configured market data provider. Existing assets are
left untouched, so this is safe to re-run — extend UNIVERSE and run again
whenever you want more coverage.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Asset, AssetType
from app.services.price_ingestion import refresh_prices

# The curated universe. Fields map directly onto the Asset model.
# Keep news_keywords query-friendly ("Nasdaq 100", not "^NDX").
UNIVERSE: list[dict] = [
    # --- US indexes -------------------------------------------------------
    dict(ticker="NDX", name="Nasdaq 100", exchange="NASDAQ",
         asset_type=AssetType.INDEX, sector="Broad Market", region="US",
         news_keywords="Nasdaq 100"),
    dict(ticker="DJI", name="Dow Jones Industrial Average", exchange="NYSE",
         asset_type=AssetType.INDEX, sector="Broad Market", region="US",
         news_keywords="Dow Jones"),
    dict(ticker="RUT", name="Russell 2000", exchange="NYSE",
         asset_type=AssetType.INDEX, sector="Small Cap", region="US",
         news_keywords="Russell 2000"),
    # --- Europe ------------------------------------------------------------
    dict(ticker="FTSE", name="FTSE 100", exchange="LSE",
         asset_type=AssetType.INDEX, sector="Broad Market", region="EUROPE",
         news_keywords="FTSE 100"),
    dict(ticker="STOXX50E", name="Euro Stoxx 50", exchange="Euronext",
         asset_type=AssetType.INDEX, sector="Broad Market", region="EUROPE",
         news_keywords="Euro Stoxx 50"),
    # --- Asia ---------------------------------------------------------------
    dict(ticker="HSI", name="Hang Seng Index", exchange="HKEX",
         asset_type=AssetType.INDEX, sector="Broad Market", region="ASIA",
         news_keywords="Hang Seng"),
    # --- Volatility -----------------------------------------------------------
    dict(ticker="VIX", name="CBOE Volatility Index", exchange="CBOE",
         asset_type=AssetType.INDEX, sector="Volatility", region="US",
         news_keywords="VIX volatility"),

    # --- 2x leveraged index ETFs ------------------------------------------
    dict(ticker="SSO", name="ProShares Ultra S&P 500 (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Broad Market", region="US",
         leverage=2.0, news_keywords="S&P 500 leveraged ETF"),
    dict(ticker="QLD", name="ProShares Ultra QQQ (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Broad Market", region="US",
         leverage=2.0, news_keywords="Nasdaq leveraged ETF"),
    dict(ticker="DDM", name="ProShares Ultra Dow30 (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Broad Market", region="US",
         leverage=2.0, news_keywords="Dow Jones leveraged ETF"),

    # --- Thematic ETFs (no leveraged versions exist for these niches) -----
    dict(ticker="UFO", name="Procure Space ETF", exchange="NASDAQ",
         asset_type=AssetType.ETF, sector="Space", region="US",
         news_keywords="space industry stocks"),
    dict(ticker="QTUM", name="Defiance Quantum ETF", exchange="NASDAQ",
         asset_type=AssetType.ETF, sector="Quantum Computing", region="US",
         news_keywords="quantum computing stocks"),
    dict(ticker="ICLN", name="iShares Global Clean Energy ETF", exchange="NASDAQ",
         asset_type=AssetType.ETF, sector="Renewable Energy", region="GLOBAL",
         news_keywords="renewable energy stocks"),
    dict(ticker="TAN", name="Invesco Solar ETF", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Renewable Energy", region="GLOBAL",
         news_keywords="solar energy stocks"),

    # --- Commodities (futures) --------------------------------------------
    dict(ticker="CL", name="WTI Crude Oil Futures", exchange="NYMEX",
         asset_type=AssetType.COMMODITY, sector="Energy", region="GLOBAL",
         news_keywords="WTI oil price"),
    dict(ticker="NG", name="Natural Gas Futures", exchange="NYMEX",
         asset_type=AssetType.COMMODITY, sector="Energy", region="GLOBAL",
         news_keywords="natural gas price"),
    dict(ticker="SI", name="Silver Futures", exchange="COMEX",
         asset_type=AssetType.COMMODITY, sector="Metals", region="GLOBAL",
         news_keywords="silver price"),
    dict(ticker="HG", name="Copper Futures", exchange="COMEX",
         asset_type=AssetType.COMMODITY, sector="Metals", region="GLOBAL",
         news_keywords="copper price"),
    dict(ticker="ZC", name="Corn Futures", exchange="CBOT",
         asset_type=AssetType.COMMODITY, sector="Grains", region="GLOBAL",
         news_keywords="corn price"),
    dict(ticker="ZS", name="Soybean Futures", exchange="CBOT",
         asset_type=AssetType.COMMODITY, sector="Grains", region="GLOBAL",
         news_keywords="soybean price"),
    dict(ticker="KC", name="Coffee Futures", exchange="ICE",
         asset_type=AssetType.COMMODITY, sector="Softs", region="GLOBAL",
         news_keywords="coffee price"),
    dict(ticker="SB", name="Sugar Futures", exchange="ICE",
         asset_type=AssetType.COMMODITY, sector="Softs", region="GLOBAL",
         news_keywords="sugar price"),

    # --- 2x leveraged commodity products -----------------------------------
    dict(ticker="UCO", name="ProShares Ultra Crude Oil (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Energy", region="US",
         leverage=2.0, news_keywords="crude oil price"),
    dict(ticker="BOIL", name="ProShares Ultra Natural Gas (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Energy", region="US",
         leverage=2.0, news_keywords="natural gas price"),
    dict(ticker="AGQ", name="ProShares Ultra Silver (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Metals", region="US",
         leverage=2.0, news_keywords="silver price"),
    dict(ticker="UGL", name="ProShares Ultra Gold (2x)", exchange="NYSE Arca",
         asset_type=AssetType.ETF, sector="Leveraged Metals", region="US",
         leverage=2.0, news_keywords="gold price"),

    # --- Rates & FX (signal detectors for the Ripple Engine) ------------------
    dict(ticker="DXY", name="US Dollar Index", exchange="ICE",
         asset_type=AssetType.INDEX, sector="FX", region="US",
         news_keywords="dollar index DXY"),
    dict(ticker="TNX", name="10-Year Treasury Yield", exchange="CBOE",
         asset_type=AssetType.INDEX, sector="Rates", region="US",
         news_keywords="10 year treasury yield"),
]


def import_universe(db: Session, price_days: int = 365) -> list[str]:
    """Insert missing UNIVERSE assets and refresh their prices.

    Returns the tickers that were actually added.
    """
    existing = set(db.scalars(select(Asset.ticker)))
    added: list[str] = []
    for spec in UNIVERSE:
        if spec["ticker"] in existing:
            continue
        db.add(Asset(**spec))
        added.append(spec["ticker"])
    db.commit()

    for ticker in added:
        refresh_prices(db, days=price_days, ticker=ticker)
    return added


if __name__ == "__main__":
    with SessionLocal() as db:
        added = import_universe(db)
    print(f"Added {len(added)} assets: {added}" if added else "Universe already up to date.")
