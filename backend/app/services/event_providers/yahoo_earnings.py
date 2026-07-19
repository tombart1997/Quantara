"""Real earnings dates via Yahoo Finance (yfinance) — no API key required.

Only stocks (and some ETFs) have earnings; for futures/indexes Yahoo returns
nothing, which is correct behavior — they simply get no earnings events.
"""
from __future__ import annotations

import logging
from datetime import datetime

import yfinance as yf

from app.services.event_providers.base import EventItem, EventProvider
from app.models.enums import EventType
from app.services.providers.yfinance import YAHOO_SYMBOLS

logger = logging.getLogger(__name__)

# How many quarters of earnings dates to pull (past + future mixed).
EARNINGS_LIMIT = 12


class YahooEarningsProvider(EventProvider):
    def fetch_events(self, tickers: list[str]) -> list[EventItem]:
        items: list[EventItem] = []
        for ticker in tickers:
            symbol = YAHOO_SYMBOLS.get(ticker, ticker)
            try:
                dates = yf.Ticker(symbol).get_earnings_dates(limit=EARNINGS_LIMIT)
            except Exception:
                logger.warning("Earnings fetch failed for %s (%s)", ticker, symbol)
                continue
            if dates is None or dates.empty:
                continue
            for ts, row in dates.iterrows():
                when = ts.to_pydatetime().replace(tzinfo=None)
                if when < datetime.now():
                    continue  # only upcoming earnings belong in the calendar
                estimate = row.get("EPS Estimate")
                description = (
                    f"EPS estimate: {estimate}" if estimate == estimate else None  # NaN check
                )
                items.append(EventItem(
                    ticker=ticker,
                    event_type=EventType.EARNINGS,
                    date=when,
                    title=f"{ticker} earnings report",
                    description=description,
                    importance=4,
                ))
        return items
