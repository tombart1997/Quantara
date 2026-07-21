"""Currency matrix (Bloomberg-style FX cross rates).

Fetches each major currency as USD-per-unit via yfinance (no API key),
computes exact cross rates and daily changes from previous closes, and
caches the result for CACHE_TTL_SECONDS so the UI can poll frequently
without hammering Yahoo.
"""
from __future__ import annotations

import logging
import time

import yfinance as yf

logger = logging.getLogger(__name__)

# currency -> Yahoo symbol giving "USD per 1 unit of currency".
# USD itself is the numéraire (1.0 by definition).
CURRENCIES: dict[str, str | None] = {
    "USD": None,
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "JPY": "JPY=X",
    "CHF": "CHF=X",
    "AUD": "AUDUSD=X",
    "CAD": "CAD=X",
    "CNY": "CNY=X",
}

CACHE_TTL_SECONDS = 5  # UI polls every second; Yahoo only gets hit every 5s
_CACHE: dict = {"matrix": None, "fetched_at": 0.0}


def _last_and_previous(symbol: str) -> tuple[float, float] | None:
    """(latest price, previous close) for a Yahoo symbol; None on failure."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        last = getattr(info, "last_price", None)
        prev = getattr(info, "previous_close", None)
        if last and prev:
            return float(last), float(prev)
        # Fallback: last two daily closes.
        history = ticker.history(period="5d", interval="1d")
        if len(history) >= 2:
            closes = history["Close"]
            return float(closes.iloc[-1]), float(closes.iloc[-2])
    except Exception:
        logger.warning("FX fetch failed for %s", symbol)
    return None


def _build_matrix() -> dict:
    usd_per: dict[str, float] = {"USD": 1.0}
    prev_per: dict[str, float] = {"USD": 1.0}
    missing: list[str] = []
    for ccy, symbol in CURRENCIES.items():
        if symbol is None:
            continue
        result = _last_and_previous(symbol)
        if result is None:
            missing.append(ccy)
        else:
            usd_per[ccy], prev_per[ccy] = result

    available = [c for c in CURRENCIES if c in usd_per]
    rates: dict[str, dict[str, float]] = {}
    changes: dict[str, dict[str, float]] = {}
    for row in available:
        rates[row] = {}
        changes[row] = {}
        for col in available:
            rate = usd_per[row] / usd_per[col]
            prev_rate = prev_per[row] / prev_per[col]
            rates[row][col] = round(rate, 6)
            changes[row][col] = (
                round((rate / prev_rate - 1) * 100, 2) if prev_rate else None
            )
    return {
        "currencies": available,
        "rates": rates,          # rates[row][col] = units of COL per 1 ROW
        "changes_pct": changes,  # daily % change of that cross rate
        "missing": missing,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def get_matrix() -> dict:
    now = time.time()
    if _CACHE["matrix"] is None or now - _CACHE["fetched_at"] > CACHE_TTL_SECONDS:
        _CACHE["matrix"] = _build_matrix()
        _CACHE["fetched_at"] = now
    return _CACHE["matrix"]
