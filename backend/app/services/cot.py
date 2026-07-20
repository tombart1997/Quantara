"""CFTC Commitments of Traders (COT) — real speculative positioning.

Free Socrata API, no key required, updated weekly (Friday data, ~1 week lag).
Dataset: Disaggregated Futures Only (72hh-3qpy) — we use the Managed Money
category, the standard "speculative positioning" measure.

This replaces the price-momentum crowdedness HEURISTIC with actual
positioning data for every CFTC-covered future we track.
"""
from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

API = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
CACHE_TTL = 3600  # weekly data — hourly cache is plenty

# Our ticker -> ordered candidate LIKE patterns for the CFTC market name.
# First pattern returning enough history wins (names change over the years).
MARKET_PATTERNS: dict[str, list[str]] = {
    "CC": ["%COCOA - ICE FUTURES%"],
    "KC": ["%COFFEE C - ICE FUTURES%"],
    "SB": ["%SUGAR NO. 11%"],
    "ZW": ["%WHEAT-SRW%"],
    "ZC": ["%CORN - CHICAGO%"],
    "ZS": ["%SOYBEANS - CHICAGO%"],
    "GC": ["%GOLD - COMMODITY EXCHANGE%"],
    "SI": ["%SILVER - COMMODITY EXCHANGE%"],
    "HG": ["%COPPER- #1%", "%COPPER-GRADE #1%"],
    "CL": ["%LIGHT SWEET%"],
    "NG": ["%NATURAL GAS NYME%", "%HENRY HUB%"],
}

_cache: dict[str, tuple[float, dict | None]] = {}


def _fetch_rows(pattern: str, limit: int = 60) -> list[dict]:
    params = {
        "$where": f"market_and_exchange_names like '{pattern}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(API, params=params)
        resp.raise_for_status()
        return resp.json()


def get_positioning(ticker: str) -> dict | None:
    """Managed-money positioning for one of our futures tickers.

    Returns net contracts, net as % of open interest, z-score of the net
    vs the last 52 weeks, week-over-week change, and the report date.
    None when the ticker has no CFTC coverage or the fetch fails.
    """
    ticker = ticker.upper()
    now = time.time()
    cached = _cache.get(ticker)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    patterns = MARKET_PATTERNS.get(ticker)
    if not patterns:
        _cache[ticker] = (now, None)
        return None

    result = None
    for pattern in patterns:
        try:
            rows = _fetch_rows(pattern)
        except Exception as e:
            logger.warning("COT fetch failed for %s (%s): %s", ticker, pattern, e)
            continue
        if len(rows) < 10:
            continue

        nets = []
        for r in rows:
            long_ = float(r.get("m_money_positions_long_all", 0))
            short = float(r.get("m_money_positions_short_all", 0))
            oi = float(r.get("open_interest_all", 1)) or 1.0
            nets.append((long_ - short, oi))
        latest_net, latest_oi = nets[0]
        prev_net = nets[1][0] if len(nets) > 1 else latest_net
        history = [n for n, _ in nets[:52]]
        mean = sum(history) / len(history)
        variance = sum((n - mean) ** 2 for n in history) / len(history)
        std = variance ** 0.5
        z = (latest_net - mean) / std if std else 0.0

        result = {
            "ticker": ticker,
            "report_date": rows[0]["report_date_as_yyyy_mm_dd"][:10],
            "net_contracts": int(latest_net),
            "net_pct_oi": round(latest_net / latest_oi * 100, 1),
            "wow_change": int(latest_net - prev_net),
            "z_score_52w": round(z, 2),
            "source": "CFTC COT (managed money, weekly)",
        }
        break

    _cache[ticker] = (now, result)
    return result


def covered_tickers() -> list[str]:
    return list(MARKET_PATTERNS)
