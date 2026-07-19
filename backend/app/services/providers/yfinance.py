"""Real market data via Yahoo Finance (yfinance), no API key required.

Internal tickers don't always match Yahoo symbols (futures and indexes
especially), so a mapping translates them. Stocks and ETFs pass through
unchanged. Anything not in the map is used as-is.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import yfinance as yf

from app.services.providers.base import MarketDataProvider, PriceBar

logger = logging.getLogger(__name__)

# Internal ticker -> Yahoo Finance symbol.
YAHOO_SYMBOLS = {
    "CC": "CC=F",      # cocoa futures
    "GC": "GC=F",      # gold futures
    "ZW": "ZW=F",      # wheat futures
    "CL": "CL=F",      # WTI crude oil futures
    "NG": "NG=F",      # natural gas futures
    "SI": "SI=F",      # silver futures
    "HG": "HG=F",      # copper futures
    "ZC": "ZC=F",      # corn futures
    "ZS": "ZS=F",      # soybean futures
    "KC": "KC=F",      # coffee futures
    "SB": "SB=F",      # sugar futures
    "SPX": "^GSPC",    # S&P 500
    "NDX": "^NDX",     # Nasdaq 100
    "DJI": "^DJI",     # Dow Jones Industrial Average
    "RUT": "^RUT",     # Russell 2000
    "N225": "^N225",   # Nikkei 225
    "DAX": "^GDAXI",   # DAX 40
    "FTSE": "^FTSE",   # FTSE 100
    "STOXX50E": "^STOXX50E",  # Euro Stoxx 50
    "HSI": "^HSI",     # Hang Seng
    "VIX": "^VIX",     # CBOE volatility index
}


class YFinanceProvider(MarketDataProvider):
    def get_daily_history(self, ticker: str, days: int) -> list[PriceBar]:
        symbol = YAHOO_SYMBOLS.get(ticker, ticker)
        start = date.today() - timedelta(days=days + 10)  # margin for weekends/holidays
        try:
            history = yf.Ticker(symbol).history(start=start, interval="1d", auto_adjust=True)
        except Exception:
            logger.exception("yfinance fetch failed for %s (%s)", ticker, symbol)
            return []
        if history.empty:
            logger.warning("yfinance returned no data for %s (%s)", ticker, symbol)
            return []

        bars: list[PriceBar] = []
        for timestamp, row in history.iterrows():
            volume = row.get("Volume")
            bars.append(
                PriceBar(
                    date=timestamp.date(),
                    open=round(float(row["Open"]), 2),
                    high=round(float(row["High"]), 2),
                    low=round(float(row["Low"]), 2),
                    close=round(float(row["Close"]), 2),
                    # Indexes have no meaningful volume -> store NULL.
                    volume=None if volume != volume else float(volume),  # NaN check
                )
            )
        return bars[-days:]
