"""Deterministic mock market data provider.

Generates a repeatable random walk per ticker (seeded from the ticker string,
so every run produces identical data — important for a dev/demo environment).
Not realistic finance, just plausible-looking series to build against.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta

from app.services.providers.base import MarketDataProvider, PriceBar

# Base price levels so different tickers live in plausible ranges.
_BASE_PRICES = {
    "NVDA": 180.0, "AAPL": 230.0,
    "CC": 7800.0, "GC": 3300.0, "ZW": 550.0,
    "SPX": 6400.0, "N225": 40000.0, "DAX": 24000.0,
    "SPY": 640.0, "NVDL": 90.0,
}


class MockProvider(MarketDataProvider):
    def get_daily_history(self, ticker: str, days: int) -> list[PriceBar]:
        seed = int(hashlib.sha256(ticker.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        price = _BASE_PRICES.get(ticker, 100.0)
        bars: list[PriceBar] = []
        # Walk calendar days from (today - days) up to today, skipping weekends.
        # (Counting bars instead would overshoot today by the skipped days.)
        day = date.today() - timedelta(days=days)
        while day < date.today():
            day += timedelta(days=1)
            if day.weekday() >= 5:
                continue
            drift = rng.gauss(0.0005, 0.02)  # slight upward drift, 2% daily vol
            open_ = price
            close = round(price * (1 + drift), 2)
            high = round(max(open_, close) * (1 + abs(rng.gauss(0, 0.005))), 2)
            low = round(min(open_, close) * (1 - abs(rng.gauss(0, 0.005))), 2)
            volume = round(abs(rng.gauss(1_000_000, 300_000)), 0)
            bars.append(PriceBar(day, round(open_, 2), high, low, close, volume))
            price = close
        return bars
