"""Ripple engine — propagates activated signals through the causal graph.

Score math (deliberately simple and fully decomposable):
    contribution = activation/100 x magnitude x order_decay x confidence x direction
Per asset, contributions from all active signals are listed individually —
conflicts are SHOWN, never silently netted. The net score is just the sum;
the decomposition is the product.

Crowdedness ("priced-in") heuristic, transparent by design:
    priced_in = clamp(actual 30d move in the expected direction / magnitude, 0..1)
No pretense of precision — it flags beneficiaries that already ran.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, PriceHistory
from app.services.ripple import (
    EDGES,
    ORDER_DECAY,
    SIGNALS,
    edges_for_signal,
    edges_for_ticker,
)
from app.services.ripple.detectors import detect_all

ACTIVATION_THRESHOLD = 10.0  # below this a signal is treated as dormant


def _contrib(edge: tuple, activation: float) -> dict:
    _, ticker, direction, magnitude, lag, confidence, order, provenance = edge
    impact = activation / 100 * magnitude * ORDER_DECAY[order] * confidence * direction
    return {
        "ticker": ticker,
        "direction": direction,
        "impact": round(impact, 2),
        "magnitude_pct": magnitude,
        "lag": lag,
        "confidence": confidence,
        "order": order,
        "decay": ORDER_DECAY[order],
        "provenance": provenance,
    }


def _actual_move(db: Session, ticker: str, days: int = 30) -> float | None:
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


def _priced_in(db: Session, contribution: dict) -> float | None:
    """0..1 estimate that the expected move already happened."""
    actual = _actual_move(db, contribution["ticker"])
    if actual is None or contribution["magnitude_pct"] == 0:
        return None
    expected_dir_move = actual * contribution["direction"]
    return round(max(0.0, min(1.0, expected_dir_move / contribution["magnitude_pct"])), 2)


def compute_state(db: Session, overrides: dict[str, float] | None = None) -> dict:
    """Full ripple state: activations, per-signal exposure, per-asset scores.

    overrides={SIGNAL_ID: 0-100} = scenario mode: those activations replace
    the measured ones, all others are forced dormant.
    """
    measured = detect_all(db, SIGNALS)
    activations = {
        s["id"]: (overrides.get(s["id"], {"activation": 0.0})
                  if overrides is not None else measured[s["id"]])
        for s in SIGNALS
    }

    # --- Per-signal ranked exposure --------------------------------------
    signals_out = []
    for s in SIGNALS:
        act = activations[s["id"]]["activation"]
        contributions = []
        if act >= ACTIVATION_THRESHOLD or overrides is not None:
            for edge in edges_for_signal(s["id"]):
                c = _contrib(edge, act)
                c["priced_in"] = _priced_in(db, c)
                contributions.append(c)
        contributions.sort(key=lambda c: abs(c["impact"]), reverse=True)
        signals_out.append({
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "activation": act,
            "activation_detail": activations[s["id"]].get("detail", "scenario override"),
            "active": act >= ACTIVATION_THRESHOLD,
            "propagation_strength": round(sum(abs(c["impact"]) for c in contributions), 2),
            "exposure": contributions,
        })
    signals_out.sort(key=lambda s: s["propagation_strength"], reverse=True)

    # --- Per-asset score cards --------------------------------------------
    assets_out = []
    for asset in db.scalars(select(Asset)):
        contribs = []
        for edge in edges_for_ticker(asset.ticker):
            act = activations[edge[0]]["activation"]
            if act < ACTIVATION_THRESHOLD:
                continue
            c = _contrib(edge, act)
            c["signal_id"] = edge[0]
            c["signal_name"] = next(s["name"] for s in SIGNALS if s["id"] == edge[0])
            c["activation"] = act
            contribs.append(c)
        if not contribs:
            continue
        contribs.sort(key=lambda c: c["impact"], reverse=True)
        net = round(sum(c["impact"] for c in contribs), 2)
        dominant = max(contribs, key=lambda c: abs(c["impact"]))
        positive = [c for c in contribs if c["impact"] > 0]
        negative = [c for c in contribs if c["impact"] < 0]
        assets_out.append({
            "ticker": asset.ticker,
            "name": asset.name,
            "net_score": net,
            "dominant_signal": dominant["signal_id"],
            "conflict": bool(positive and negative),
            "contributions": contribs,
        })
    assets_out.sort(key=lambda a: abs(a["net_score"]), reverse=True)

    # --- Portfolio mirror (watchlist overlay) ------------------------------
    portfolio = []
    for a in assets_out:
        asset = db.scalar(select(Asset).where(Asset.ticker == a["ticker"]))
        if asset and asset.in_watchlist:
            portfolio.append(a)
    by_signal: dict[str, float] = {}
    for a in portfolio:
        for c in a["contributions"]:
            by_signal[c["signal_name"]] = round(
                by_signal.get(c["signal_name"], 0.0) + c["impact"], 2)

    return {
        "mode": "scenario" if overrides is not None else "live",
        "signals": signals_out,
        "assets": assets_out,
        "portfolio": {
            "positions": portfolio,
            "implicit_bets": sorted(
                ({"signal": k, "net_impact": v} for k, v in by_signal.items()),
                key=lambda x: abs(x["net_impact"]), reverse=True),
        },
    }
