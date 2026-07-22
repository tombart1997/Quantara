"""Signal engine — loads data, runs the rules, persists signals.

One signal per asset per run. Re-running on the same day REPLACES that day's
signals (instead of stacking duplicates), so the endpoint is safe to call as
often as you like.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Asset, Event, NewsArticle, PriceHistory, Signal
from app.services.signals.rules import (
    EVENT_WINDOW_DAYS,
    SENTIMENT_WINDOW_DAYS,
    Evaluation,
    SignalContext,
    evaluate,
)

# How many recent days of bars rules may inspect (52-week rule needs ~1y).
PRICE_LOOKBACK_DAYS = 370


def build_context(db: Session, asset: Asset) -> SignalContext:
    prices = list(db.scalars(
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset.id,
               PriceHistory.date >= date.today() - timedelta(days=PRICE_LOOKBACK_DAYS))
        .order_by(PriceHistory.date)
    ))
    events = list(db.scalars(
        select(Event)
        .where(Event.asset_id == asset.id,
               Event.date >= datetime.now(),
               Event.date <= datetime.now() + timedelta(days=EVENT_WINDOW_DAYS))
        .order_by(Event.date)
    ))
    news = list(db.scalars(
        select(NewsArticle)
        .where(NewsArticle.assets.any(id=asset.id),
               NewsArticle.published_at >= datetime.now() - timedelta(days=SENTIMENT_WINDOW_DAYS))
    ))
    return SignalContext(prices=prices, upcoming_events=events, recent_news=news)


def signal_name(asset: Asset, ev: Evaluation) -> str:
    return f"{asset.ticker}: {ev.top_title}" if ev.top_title else f"{asset.ticker}: no triggers"


def run(db: Session) -> list[Signal]:
    """Evaluate every asset and persist today's signals. Returns what was stored.

    Race safety: the (asset, name, signal_date) unique constraint is the final
    arbiter when multiple engine processes run concurrently — a losing insert
    is skipped, never duplicated.
    """
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    db.execute(delete(Signal).where(Signal.created_at >= today_start))

    created: list[Signal] = []
    for asset in db.scalars(select(Asset)):
        ev = evaluate(build_context(db, asset))
        if ev.score == 0:
            continue  # nothing fired -> no signal, no noise
        signal = Signal(asset_id=asset.id, name=signal_name(asset, ev),
                        reasons=ev.reasons, score=ev.score, signal_date=today)
        try:
            with db.begin_nested():  # savepoint: only this insert rolls back
                db.add(signal)
                db.flush()
            created.append(signal)
        except IntegrityError:
            continue  # a concurrent process already wrote this one
    db.commit()
    return created
