"""Unit tests for the signal rules — synthetic contexts, no database."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app.services.signals.rules import (
    RULES,
    SignalContext,
    evaluate,
    event_sentiment_alignment,
    large_price_move,
    momentum_streak,
    near_52w_extreme,
    news_sentiment_shift,
    upcoming_important_event,
    volume_spike,
)


def bar(close: float, days_ago: int = 0, volume: float | None = 1_000_000, high=None, low=None):
    return SimpleNamespace(
        date=date.today() - timedelta(days=days_ago),
        close=close, open=close, volume=volume,
        high=high if high is not None else close,
        low=low if low is not None else close,
    )


def event(title="Report", importance=4, days_ahead=5):
    return SimpleNamespace(
        title=title, importance=importance,
        date=datetime.now() + timedelta(days=days_ahead),
    )


def news(sentiment: float | None):
    return SimpleNamespace(sentiment=sentiment)


def ctx(prices=(), events=(), articles=()):
    return SignalContext(prices=list(prices), upcoming_events=list(events), recent_news=list(articles))


class TestLargePriceMove:
    def test_fires_above_threshold(self):
        c = ctx(prices=[bar(100, 1), bar(106)])
        result = large_price_move(c)
        assert result is not None and "+6.0%" in result.reason

    def test_silent_below_threshold(self):
        assert large_price_move(ctx(prices=[bar(100, 1), bar(102)])) is None

    def test_silent_with_insufficient_data(self):
        assert large_price_move(ctx(prices=[bar(100)])) is None


class TestVolumeSpike:
    def test_fires_on_spike(self):
        prices = [bar(100, days_ago=i, volume=1_000_000) for i in range(31, 0, -1)]
        prices.append(bar(100, volume=3_000_000))
        assert volume_spike(ctx(prices=prices)) is not None

    def test_silent_on_normal_volume(self):
        prices = [bar(100, days_ago=i, volume=1_000_000) for i in range(31, 0, -1)]
        prices.append(bar(100, volume=1_100_000))
        assert volume_spike(ctx(prices=prices)) is None

    def test_silent_without_volume(self):
        prices = [bar(100, days_ago=i, volume=None) for i in range(40)]
        assert volume_spike(ctx(prices=prices)) is None


class TestUpcomingEvent:
    def test_weight_scales_with_importance(self):
        assert upcoming_important_event(ctx(events=[event(importance=5)])).weight == 25
        assert upcoming_important_event(ctx(events=[event(importance=3)])).weight == 15

    def test_silent_without_events(self):
        assert upcoming_important_event(ctx()) is None


class TestSentiment:
    def test_fires_beyond_threshold(self):
        result = news_sentiment_shift(ctx(articles=[news(0.5), news(0.7)]))
        assert result is not None and "+0.60" in result.reason

    def test_silent_when_neutral_or_unscored(self):
        assert news_sentiment_shift(ctx(articles=[news(0.1), news(None)])) is None
        assert news_sentiment_shift(ctx(articles=[news(None)])) is None


class TestNear52wExtreme:
    def test_fires_near_high(self):
        prices = [bar(100, days_ago=i, high=110, low=90) for i in range(300, 0, -1)]
        prices.append(bar(108.5, high=108.5, low=108))  # within 3% of 110
        result = near_52w_extreme(ctx(prices=prices))
        assert result is not None and result.title == "Near 52-week high"

    def test_silent_mid_range(self):
        prices = [bar(100, days_ago=i, high=150, low=50) for i in range(300, 0, -1)]
        prices.append(bar(100, high=101, low=99))
        assert near_52w_extreme(ctx(prices=prices)) is None


class TestMomentumStreak:
    def test_fires_on_up_streak(self):
        prices = [bar(c, days_ago=3 - i) for i, c in enumerate([100, 101, 102, 103])]
        result = momentum_streak(ctx(prices=prices))
        assert result is not None and "up closes" in result.reason

    def test_silent_when_mixed(self):
        prices = [bar(c, days_ago=3 - i) for i, c in enumerate([100, 101, 99, 102])]
        assert momentum_streak(ctx(prices=prices)) is None


class TestAlignment:
    def test_requires_both_event_and_sentiment(self):
        assert event_sentiment_alignment(ctx(events=[event()], articles=[news(0.8)])) is not None
        assert event_sentiment_alignment(ctx(events=[event()], articles=[news(0.1)])) is None
        assert event_sentiment_alignment(ctx(articles=[news(0.8)])) is None


class TestEvaluate:
    def test_combines_reasons_and_score(self):
        c = ctx(
            prices=[bar(100, 1), bar(110)],   # +10% price move -> 30
            events=[event(importance=5)],      # -> 25
            articles=[news(0.9)],              # -> 20 (+15 alignment)
        )
        ev = evaluate(c)
        assert ev.score == 90  # 30 + 25 + 20 + 15
        assert len(ev.reasons) == 4
        assert ev.top_title == "Large price movement"

    def test_score_capped_at_100(self):
        c = ctx(
            prices=[bar(100, 1), bar(120)],
            events=[event(importance=5), event("B", 5)],
            articles=[news(0.9)],
        )
        assert evaluate(c).score <= 100

    def test_all_rules_registered(self):
        assert len(RULES) == 7
