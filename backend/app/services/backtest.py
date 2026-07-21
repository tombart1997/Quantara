"""Signal backtesting — replay the price-based rules over history and
measure what happened AFTER they fired.

Methodology (kept honest on purpose):
  - Only the four price-based rules are replayed (large price move, volume
    spike, 52-week extremes, momentum streak). News/event rules can't be
    replayed — there is no historical news sentiment or event calendar in
    the database, and we don't fake it.
  - Strict no-lookahead: the context for day D contains only bars up to D.
  - Forward returns are measured at fixed horizons (+5/+10/+20 trading
    days) and compared against the unconditional baseline (all days in the
    same window for the same assets), so results read as
    "after X fired, returns averaged A% vs baseline B%".
  - Sample sizes are small. Counts are shown everywhere; treat patterns,
    not single numbers.
"""
from __future__ import annotations

import statistics
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, PriceHistory
from app.services.signals.rules import (
    RULES,
    SignalContext,
)

# Rules that depend only on prices and are therefore replayable.
PRICE_RULE_NAMES = {
    "large_price_move", "volume_spike", "near_52w_extreme", "momentum_streak",
}
PRICE_RULES = [r for r in RULES if r.__name__ in PRICE_RULE_NAMES]

HORIZONS = (5, 10, 20)
# Minimum bars before a replay day so every rule has its full context
# (52-week rule needs ~260 trading days).
MIN_LOOKBACK = 265


def _load_bars(db: Session, asset_id: int) -> list[PriceHistory]:
    return list(db.scalars(
        select(PriceHistory)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.date)
    ))


def _fwd_return(bars: list[PriceHistory], idx: int, horizon: int) -> float | None:
    if idx + horizon >= len(bars) or not bars[idx].close:
        return None
    return (bars[idx + horizon].close - bars[idx].close) / bars[idx].close * 100


def replay_asset(db: Session, asset: Asset) -> list[dict]:
    """Every rule fire in one asset's history, with forward returns."""
    bars = _load_bars(db, asset.id)
    fires: list[dict] = []
    # Leave room for the longest horizon after the last replay day.
    for i in range(MIN_LOOKBACK, len(bars) - max(HORIZONS)):
        ctx = SignalContext(prices=bars[: i + 1], upcoming_events=[], recent_news=[])
        for rule in PRICE_RULES:
            fired = rule(ctx)
            if fired is None:
                continue
            fires.append({
                "ticker": asset.ticker,
                "date": bars[i].date.isoformat(),
                "rule": rule.__name__,
                "title": fired.title,
                "fwd": {h: _fwd_return(bars, i, h) for h in HORIZONS},
            })
    return fires


def _baseline(db: Session, assets: list[Asset]) -> dict[int, float]:
    """Unconditional mean forward return per horizon across all assets."""
    per_h: dict[int, list[float]] = {h: [] for h in HORIZONS}
    for asset in assets:
        bars = _load_bars(db, asset.id)
        for i in range(MIN_LOOKBACK, len(bars) - max(HORIZONS)):
            for h in HORIZONS:
                r = _fwd_return(bars, i, h)
                if r is not None:
                    per_h[h].append(r)
    return {h: round(statistics.mean(v), 3) if v else None for h, v in per_h.items()}


def _summarize(returns: list[float], baseline: float | None) -> dict:
    if not returns:
        return {"n": 0}
    mean = round(statistics.mean(returns), 2)
    return {
        "n": len(returns),
        "hit_rate": round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1),
        "mean": mean,
        "median": round(statistics.median(returns), 2),
        "baseline_mean": baseline,
        "delta_vs_baseline": round(mean - baseline, 2) if baseline is not None else None,
    }


def run_backtest(db: Session, tickers: list[str] | None = None) -> dict:
    stmt = select(Asset)
    if tickers:
        stmt = stmt.where(Asset.ticker.in_([t.upper() for t in tickers]))
    assets = list(db.scalars(stmt))

    baseline = _baseline(db, assets)
    fires: list[dict] = []
    for asset in assets:
        fires.extend(replay_asset(db, asset))

    rule_names = sorted({f["rule"] for f in fires})
    rules_out = []
    for name in rule_names:
        rule_fires = [f for f in fires if f["rule"] == name]
        per_horizon = {}
        for h in HORIZONS:
            returns = [f["fwd"][h] for f in rule_fires if f["fwd"][h] is not None]
            per_horizon[str(h)] = _summarize(returns, baseline[h])
        rules_out.append({
            "rule": name,
            "title": rule_fires[0]["title"],
            "fires": len(rule_fires),
            "per_horizon": per_horizon,
        })

    # Per-asset breakdown (only where a rule fired at least 3 times).
    assets_out = []
    for asset in assets:
        asset_fires = [f for f in fires if f["ticker"] == asset.ticker]
        rules_map = {}
        for name in sorted({f["rule"] for f in asset_fires}):
            rf = [f for f in asset_fires if f["rule"] == name]
            if len(rf) < 3:
                continue
            rules_map[name] = {
                str(h): _summarize(
                    [f["fwd"][h] for f in rf if f["fwd"][h] is not None], baseline[h])
                for h in HORIZONS
            }
        if rules_map:
            assets_out.append({"ticker": asset.ticker, "name": asset.name, "rules": rules_map})

    dates = [f["date"] for f in fires]
    return {
        "window": {"from": min(dates) if dates else None, "to": max(dates) if dates else None},
        "horizons": list(HORIZONS),
        "baseline_mean_returns": baseline,
        "baseline_note": "Unconditional mean forward return across all assets and days in the replay window.",
        "method_note": ("Price-based rules only (large price move, volume spike, 52-week "
                        "extremes, momentum streak). News/event rules excluded — no historical "
                        "news/event data. Small samples: read patterns, not single numbers."),
        "total_fires": len(fires),
        "rules": rules_out,
        "assets": assets_out,
    }
