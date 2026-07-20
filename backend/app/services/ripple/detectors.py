"""Signal detectors — compute activation 0-100 from real data.

Two kinds, both transparent:
  price_change / price_level: from stored price history (cheap, always live)
  news: 7-day RSS article count for a theme query (cached 10 min — RSS is
        slow and themes don't move minute-to-minute)

Every activation returns its reasoning, so the UI can always show WHY a
signal is lit.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, PriceHistory
from app.services.news_providers import get_news_provider

logger = logging.getLogger(__name__)

NEWS_CACHE_TTL = 600  # seconds
_news_cache: dict[str, tuple[float, dict]] = {}


def _pct_change(db: Session, ticker: str, days: int) -> float | None:
    closes = list(db.scalars(
        select(PriceHistory.close)
        .join(Asset, PriceHistory.asset_id == Asset.id)
        .where(Asset.ticker == ticker,
               PriceHistory.date >= date.today() - timedelta(days=days + 10))
        .order_by(PriceHistory.date.desc())
    ))
    if len(closes) < 2 or not closes[-1]:
        return None
    return (closes[0] - closes[-1]) / closes[-1] * 100


def _latest_close(db: Session, ticker: str) -> float | None:
    return db.scalar(
        select(PriceHistory.close)
        .join(Asset, PriceHistory.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )


def _detect_price(db: Session, signal: dict) -> dict:
    det = signal["detector"]
    ticker = det["ticker"]
    if det["kind"] == "price_change":
        value = _pct_change(db, ticker, det["days"])
        if value is None:
            return {"activation": 0.0, "detail": f"no price data for {ticker}"}
        activation = max(0.0, min(100.0, (value - det["threshold"]) / det["scale"] * 100))
        detail = (f"{ticker} {det['days']}-day change {value:+.1f}% "
                  f"(0% at {det['threshold']}%, 100% at {det['threshold'] + det['scale']}%)")
    else:  # price_level
        value = _latest_close(db, ticker)
        if value is None:
            return {"activation": 0.0, "detail": f"no price data for {ticker}"}
        activation = max(0.0, min(100.0, (value - det["floor"]) / det["scale"] * 100))
        detail = (f"{ticker} level {value} (0% at {det['floor']}, "
                  f"100% at {det['floor'] + det['scale']})")
    return {"activation": round(activation, 1), "detail": detail}


def _detect_news(signal: dict) -> dict:
    det = signal["detector"]
    query = det["query"]
    now = time.time()
    cached = _news_cache.get(query)
    if cached and now - cached[0] < NEWS_CACHE_TTL:
        return cached[1]
    try:
        # Fetch MORE than full scale so popular themes differentiate in the
        # 0-100 range instead of pinning at 100 (RSS returns ~10-15 by default).
        items = get_news_provider().fetch_news(query, max_items=30)
        count = len(items)
        activation = min(100.0, count / det["full_scale_articles"] * 100)
        detail = (f"{count} articles in 7 days for '{query}' "
                  f"(100% at {det['full_scale_articles']})")
        result = {"activation": round(activation, 1), "detail": detail}
    except Exception as e:
        logger.warning("News detector failed for %s: %s", query, e)
        result = {"activation": 0.0, "detail": f"news fetch failed for '{query}'"}
    _news_cache[query] = (now, result)
    return result


def detect_activation(db: Session, signal: dict) -> dict:
    """Activation 0-100 plus a human-readable explanation."""
    if signal["detector"]["kind"] == "news":
        return _detect_news(signal)
    return _detect_price(db, signal)


def detect_all(db: Session, signals: list[dict]) -> dict[str, dict]:
    return {s["id"]: detect_activation(db, s) for s in signals}
