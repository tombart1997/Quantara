"""Provider abstraction for market data.

The rest of the app NEVER talks to a data vendor directly. It depends on the
`MarketDataProvider` protocol below. Swapping the mock for a real provider
(yfinance, Alpha Vantage, ...) means adding one file and changing one env var
— routers, seed logic, and the signal engine stay untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class PriceBar:
    """One day of OHLCV data, vendor-neutral."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None


class MarketDataProvider(Protocol):
    """Contract every market data provider must fulfill."""

    def get_daily_history(self, ticker: str, days: int) -> list[PriceBar]:
        """Return the last `days` of daily bars, oldest first."""
        ...
