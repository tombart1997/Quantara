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


def consult(db: Session, ticker: str | None, question: str | None) -> dict:
    settings = get_settings()
    prompt = build_prompt(db, ticker, question)
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
                        {"role": "system", "content": SYSTEM_PROMPT},
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
