"""Signal rules — the transparent building blocks of the signal engine.

Each rule inspects a preloaded SignalContext and either stays silent or
returns a RuleResult with:
  - a human-readable reason INCLUDING the numbers behind it (the UI shows
    this verbatim — transparency is the whole point),
  - a weight contributing to the 0-100 attention score.

Rules observe; they never predict. Adding a new rule = appending one
function to RULES. No other code changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.models import Event, NewsArticle, PriceHistory

# --- Tunable thresholds (intentionally plain constants, not hidden config) ---
PRICE_MOVE_THRESHOLD_PCT = 5.0
VOLUME_SPIKE_MULTIPLE = 2.0
EVENT_WINDOW_DAYS = 10
SENTIMENT_WINDOW_DAYS = 7
SENTIMENT_THRESHOLD = 0.3
WEEK52_PROXIMITY_PCT = 3.0
STREAK_DAYS = 3


@dataclass
class SignalContext:
    """Everything rules are allowed to look at for one asset."""

    prices: list[PriceHistory]        # recent daily bars, oldest first
    upcoming_events: list[Event]      # asset events within EVENT_WINDOW_DAYS
    recent_news: list[NewsArticle]    # asset news within SENTIMENT_WINDOW_DAYS


@dataclass
class RuleResult:
    title: str        # short label, used for the signal name
    reason: str       # full explanation with numbers
    weight: int       # contribution to the score


@dataclass
class Evaluation:
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    top_title: str | None = None


def large_price_move(ctx: SignalContext) -> RuleResult | None:
    if len(ctx.prices) < 2:
        return None
    prev, latest = ctx.prices[-2], ctx.prices[-1]
    if not prev.close:
        return None
    change_pct = (latest.close - prev.close) / prev.close * 100
    if abs(change_pct) < PRICE_MOVE_THRESHOLD_PCT:
        return None
    direction = "up" if change_pct > 0 else "down"
    return RuleResult(
        title="Large price movement",
        reason=(f"Close moved {change_pct:+.1f}% on {latest.date} "
                f"({prev.close} -> {latest.close}; threshold ±{PRICE_MOVE_THRESHOLD_PCT}%)"),
        weight=30,
    )


def volume_spike(ctx: SignalContext) -> RuleResult | None:
    bars = [p for p in ctx.prices if p.volume]
    if len(bars) < 31:
        return None
    latest = bars[-1]
    avg_30d = sum(p.volume for p in bars[-31:-1]) / 30
    if not avg_30d or latest.volume < VOLUME_SPIKE_MULTIPLE * avg_30d:
        return None
    return RuleResult(
        title="Unusual volume",
        reason=(f"Volume {latest.volume:,.0f} on {latest.date} is "
                f"{latest.volume / avg_30d:.1f}x the 30-day average "
                f"(threshold {VOLUME_SPIKE_MULTIPLE}x)"),
        weight=25,
    )


def upcoming_important_event(ctx: SignalContext) -> RuleResult | None:
    if not ctx.upcoming_events:
        return None
    top = max(ctx.upcoming_events, key=lambda e: e.importance)
    weight = top.importance * 5  # importance 3-5 -> 15-25
    titles = "; ".join(f"{e.title} ({e.date:%Y-%m-%d}, importance {e.importance})"
                       for e in ctx.upcoming_events)
    return RuleResult(
        title="Important event approaching",
        reason=f"{len(ctx.upcoming_events)} event(s) within {EVENT_WINDOW_DAYS} days: {titles}",
        weight=weight,
    )


def news_sentiment_shift(ctx: SignalContext) -> RuleResult | None:
    scored = [n for n in ctx.recent_news if n.sentiment is not None]
    if not scored:
        return None
    avg = sum(n.sentiment for n in scored) / len(scored)
    if abs(avg) < SENTIMENT_THRESHOLD:
        return None
    tone = "positive" if avg > 0 else "negative"
    return RuleResult(
        title="News sentiment shifting",
        reason=(f"Average sentiment of {len(scored)} article(s) in the last "
                f"{SENTIMENT_WINDOW_DAYS} days is {avg:+.2f} ({tone}; "
                f"threshold ±{SENTIMENT_THRESHOLD})"),
        weight=20,
    )


def near_52w_extreme(ctx: SignalContext) -> RuleResult | None:
    """Close within WEEK52_PROXIMITY_PCT of the 52-week high or low."""
    if len(ctx.prices) < 60:
        return None
    latest = ctx.prices[-1].close
    year = ctx.prices[-260:]  # ~1 trading year
    hi = max(p.high for p in year)
    lo = min(p.low for p in year)
    if hi and latest >= hi * (1 - WEEK52_PROXIMITY_PCT / 100):
        return RuleResult(
            title="Near 52-week high",
            reason=(f"Close {latest} on {ctx.prices[-1].date} is "
                    f"{(latest / hi - 1) * 100:+.1f}% vs the 52-week high {hi} "
                    f"(within {WEEK52_PROXIMITY_PCT}%)"),
            weight=20,
        )
    if lo and latest <= lo * (1 + WEEK52_PROXIMITY_PCT / 100):
        return RuleResult(
            title="Near 52-week low",
            reason=(f"Close {latest} on {ctx.prices[-1].date} is "
                    f"{(latest / lo - 1) * 100:+.1f}% vs the 52-week low {lo} "
                    f"(within {WEEK52_PROXIMITY_PCT}%)"),
            weight=20,
        )
    return None


def momentum_streak(ctx: SignalContext) -> RuleResult | None:
    """STREAK_DAYS consecutive closes in the same direction."""
    if len(ctx.prices) < STREAK_DAYS + 1:
        return None
    closes = [p.close for p in ctx.prices[-(STREAK_DAYS + 1):]]
    if all(b > a for a, b in zip(closes, closes[1:])):
        return RuleResult(
            title="Momentum streak",
            reason=f"{STREAK_DAYS} consecutive up closes: {closes}",
            weight=15,
        )
    if all(b < a for a, b in zip(closes, closes[1:])):
        return RuleResult(
            title="Momentum streak",
            reason=f"{STREAK_DAYS} consecutive down closes: {closes}",
            weight=15,
        )
    return None


def event_sentiment_alignment(ctx: SignalContext) -> RuleResult | None:
    """Upcoming event AND news sentiment pointing the same way — the
    combination is more interesting than either alone."""
    if not ctx.upcoming_events:
        return None
    scored = [n for n in ctx.recent_news if n.sentiment is not None]
    if not scored:
        return None
    avg = sum(n.sentiment for n in scored) / len(scored)
    if abs(avg) < SENTIMENT_THRESHOLD:
        return None
    top = max(ctx.upcoming_events, key=lambda e: e.importance)
    return RuleResult(
        title="Event-sentiment alignment",
        reason=(f"News sentiment {avg:+.2f} over {len(scored)} article(s) "
                f"coincides with upcoming '{top.title}' "
                f"({top.date:%Y-%m-%d}, importance {top.importance})"),
        weight=15,
    )


# The engine simply iterates this list.
RULES = [
    large_price_move,
    volume_spike,
    upcoming_important_event,
    news_sentiment_shift,
    near_52w_extreme,
    momentum_streak,
    event_sentiment_alignment,
]


def evaluate(ctx: SignalContext) -> Evaluation:
    """Run every rule and combine the fired ones into score + reasons."""
    result = Evaluation()
    best_weight = -1
    for rule in RULES:
        fired = rule(ctx)
        if fired is None:
            continue
        result.reasons.append(f"{fired.title}: {fired.reason}")
        result.score += fired.weight
        if fired.weight > best_weight:
            best_weight, result.top_title = fired.weight, fired.title
    result.score = min(100, result.score)
    return result
