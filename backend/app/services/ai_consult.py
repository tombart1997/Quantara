"""AI consultant service — builds a data-grounded prompt and (optionally)
calls the Kimi API.

Two modes, selected purely by config:
  - No API key  -> prompt-only: the generated prompt is returned so the user
                   can paste it into any AI chat.
  - API key set -> the backend calls Kimi (OpenAI-compatible endpoint) and
                   returns the model's answer alongside the prompt.

The prompt is always built from live database content — never from the AI's
general knowledge — so the consultation is grounded in what the dashboard
actually shows.
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Asset, Event, JournalEntry, NewsArticle, PriceHistory, Signal

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an investment research analyst assistant embedded in a personal "
    "research dashboard. You receive a snapshot of real data from the user's "
    "database (prices, events, news, signals, journal notes). Base your "
    "analysis ONLY on this provided data and clearly labeled general market "
    "knowledge. Be balanced: always cover the bull case, the bear case, and "
    "what to watch next. Do not give buy/sell instructions or price targets; "
    "this is decision support, not financial advice. Keep it structured and "
    "concise (under 400 words)."
)

CROSS_REFERENCE_SYSTEM_PROMPT = (
    "You are an investment research analyst specializing in cross-asset "
    "narrative analysis. You receive a snapshot of real data from the user's "
    "database plus a set of events/themes the user selected. Your job: find "
    "the narrative connecting those events to the target asset — including "
    "non-obvious second-order effects (supply chains, input costs, rate "
    "transmission, demand shifts, currency effects, positioning). Be strictly "
    "metric-driven: cite the specific numbers from the data (price levels, "
    "percentage changes, sentiment scores, importance ratings, dates) instead "
    "of generic statements, and say explicitly when a hypothesized link is NOT "
    "supported by the data. Do not give buy/sell instructions or price "
    "targets; this is decision support, not financial advice."
)


def _asset_section(db: Session, asset: Asset) -> str:
    lines = [
        f"## Asset: {asset.name} ({asset.ticker})",
        f"Type: {asset.asset_type.value} | Exchange: {asset.exchange} | "
        f"Sector: {asset.sector or '-'} | Region: {asset.region or '-'} | "
        f"Leverage: {asset.leverage}x",
    ]

    prices = list(db.scalars(
        select(PriceHistory).where(PriceHistory.asset_id == asset.id)
        .order_by(PriceHistory.date.desc()).limit(30)
    ))
    if prices:
        latest = prices[0]
        lines.append(f"Latest close: {latest.close} ({latest.date})")
        if len(prices) >= 2 and prices[-1].close:
            month_change = (latest.close - prices[-1].close) / prices[-1].close * 100
            lines.append(f"30-day change: {month_change:+.1f}%")
        lines.append("Last 5 closes: " + ", ".join(
            f"{p.date}: {p.close}" for p in prices[:5]
        ))

    events = list(db.scalars(
        select(Event).where(Event.asset_id == asset.id, Event.date >= datetime.now())
        .order_by(Event.date).limit(5)
    ))
    if events:
        lines.append("Upcoming events:")
        lines += [f"  - {e.date:%Y-%m-%d}: {e.title} (importance {e.importance}/5)" for e in events]

    news = list(db.scalars(
        select(NewsArticle).where(NewsArticle.assets.any(id=asset.id))
        .order_by(NewsArticle.published_at.desc()).limit(5)
    ).unique())
    if news:
        lines.append("Recent news:")
        lines += [
            f"  - [{n.published_at:%Y-%m-%d}] {n.headline} "
            f"(sentiment {n.sentiment:+.2f})" if n.sentiment is not None else
            f"  - [{n.published_at:%Y-%m-%d}] {n.headline}"
            for n in news
        ]

    signals = list(db.scalars(
        select(Signal).where(Signal.asset_id == asset.id)
        .order_by(Signal.created_at.desc()).limit(3)
    ))
    if signals:
        lines.append("Active signals (rule-based, transparent):")
        for s in signals:
            lines.append(f"  - {s.name} — score {s.score}/100")
            lines += [f"      reason: {r}" for r in s.reasons]

    journal = list(db.scalars(
        select(JournalEntry).where(JournalEntry.asset_id == asset.id)
        .order_by(JournalEntry.date.desc()).limit(3)
    ))
    if journal:
        lines.append("My journal notes:")
        for j in journal:
            entry = f"  - [{j.date}] Thesis: {j.thesis} (confidence {j.confidence}/10)"
            if j.risk:
                entry += f" | Risk: {j.risk}"
            lines.append(entry)

    return "\n".join(lines)


def _overview_section(db: Session) -> str:
    """Whole-portfolio context when no specific asset is selected."""
    lines = ["## Portfolio overview"]
    for asset in db.scalars(select(Asset).where(Asset.in_watchlist.is_(True))):
        prices = list(db.scalars(
            select(PriceHistory.close).where(PriceHistory.asset_id == asset.id)
            .order_by(PriceHistory.date.desc()).limit(2)
        ))
        change = ""
        if len(prices) == 2 and prices[1]:
            change = f" ({(prices[0] - prices[1]) / prices[1] * 100:+.2f}%)"
        lines.append(f"  - {asset.ticker}: {prices[0] if prices else 'no data'}{change}")
    signals = list(db.scalars(select(Signal).order_by(Signal.created_at.desc()).limit(5)))
    if signals:
        lines.append("Latest signals:")
        lines += [f"  - {s.name} — {s.score}/100" for s in signals]
    return "\n".join(lines)


def build_prompt(db: Session, ticker: str | None = None, question: str | None = None) -> str:
    parts = ["# Investment research context", ""]
    if ticker:
        asset = db.scalar(select(Asset).where(Asset.ticker == ticker.upper()))
        if asset is None:
            raise ValueError(f"Unknown ticker {ticker!r}")
        parts.append(_asset_section(db, asset))
    else:
        parts.append(_overview_section(db))
    parts.append("")
    parts.append("# Task")
    parts.append(question.strip() if question and question.strip()
                 else "Give me a balanced research assessment of the above.")
    return "\n".join(parts)


def _events_section(db: Session, event_ids: list[int]) -> str:
    events = [e for e in (db.get(Event, i) for i in event_ids) if e is not None]
    lines = ["## Selected events / themes to cross-reference"]
    for e in events:
        line = (f"  - [{e.date:%Y-%m-%d}] {e.title} "
                f"(type: {e.event_type.value}, importance: {e.importance}/5")
        if e.asset:
            line += f", linked asset: {e.asset.ticker}"
        line += ")"
        if e.description:
            line += f" — {e.description}"
        lines.append(line)
    return "\n".join(lines)


def build_cross_reference_prompt(
    db: Session, ticker: str, event_ids: list[int], question: str | None = None
) -> str:
    """Prompt that hunts for a narrative connecting N events to one asset."""
    asset = db.scalar(select(Asset).where(Asset.ticker == ticker.upper()))
    if asset is None:
        raise ValueError(f"Unknown ticker {ticker!r}")

    parts = ["# Investment research context", ""]
    parts.append(_asset_section(db, asset))
    parts.append("")
    parts.append(_events_section(db, event_ids))
    parts.append("")
    parts.append("# Task")
    if question and question.strip():
        parts.append(question.strip())
        parts.append("")
    parts.append(
        f"Cross-reference the selected events/themes against {asset.ticker}. "
        "For each event, analyze the transmission channel to this asset "
        "(direct exposure, supply chain, input costs, rates, demand, "
        "positioning) and rate the link as strong / weak / unsupported based "
        "on the data above. Then look for the combined narrative: do the "
        "events reinforce or contradict each other for this asset? Ground "
        "every claim in the specific numbers provided (price levels, % "
        "changes, sentiment scores, importance ratings, dates). "
        "Finish with a 'Rational summary' section that weighs strategic "
        "options completely rationally: risk vs upside, and timing — which "
        "event dates matter and what to watch before and after each."
    )
    return "\n".join(parts)


def consult(db: Session, ticker: str | None, question: str | None,
            event_ids: list[int] | None = None) -> dict:
    settings = get_settings()
    if event_ids:
        if not ticker:
            raise ValueError("Cross-reference requires a target asset (ticker)")
        prompt = build_cross_reference_prompt(db, ticker, event_ids, question)
        system_prompt = CROSS_REFERENCE_SYSTEM_PROMPT
    else:
        prompt = build_prompt(db, ticker, question)
        system_prompt = SYSTEM_PROMPT
    result = {
        "prompt": prompt,
        "configured": bool(settings.kimi_api_key),
        "model": settings.kimi_model,
        "response": None,
    }
    if not settings.kimi_api_key:
        return result

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{settings.kimi_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.kimi_api_key}"},
                json={
                    "model": settings.kimi_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            result["response"] = resp.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        logger.warning("Kimi API error %s: %s", e.response.status_code, e.response.text[:200])
        result["error"] = f"Kimi API returned {e.response.status_code}. Check key/model config."
    except Exception as e:
        logger.exception("Kimi API call failed")
        result["error"] = f"Could not reach the Kimi API: {e}"
    return result
