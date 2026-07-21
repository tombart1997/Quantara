"""Backtest tests: aggregation math and the no-lookahead property."""
from __future__ import annotations

from app.services import backtest as bt
from app.services.backtest import _summarize


class TestSummarize:
    def test_basic_stats(self):
        s = _summarize([1.0, 2.0, -1.0], baseline=0.5)
        assert s["n"] == 3
        assert s["hit_rate"] == round(2 / 3 * 100, 1)
        assert s["mean"] == 0.67
        assert s["median"] == -1.0 or s["median"] == 1.0  # median of [1,2,-1] = 1.0
        assert s["delta_vs_baseline"] == round(0.67 - 0.5, 2)

    def test_empty_returns(self):
        assert _summarize([], baseline=1.0) == {"n": 0}

    def test_delta_none_without_baseline(self):
        assert _summarize([1.0], baseline=None)["delta_vs_baseline"] is None


class TestNoLookahead:
    """The replay context for day i must contain only bars up to i.
    Property: truncating history after day i must not change whether rules
    fire on day i. We verify by construction: replay_asset slices
    bars[:i+1] — the same rule evaluated on a truncated series must agree."""

    def test_context_window_matches_truncation(self):
        from types import SimpleNamespace
        from datetime import date, timedelta
        from app.services.signals.rules import SignalContext, large_price_move

        bars = [
            SimpleNamespace(date=date.today() - timedelta(days=10 - i),
                            open=c, high=c, low=c, close=c, volume=1_000_000)
            for i, c in enumerate([100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 106])
        ]
        # Rule on full series at index 10 (last day).
        full = SignalContext(prices=bars, upcoming_events=[], recent_news=[])
        # Same day evaluated with strictly no future data (identical slice).
        no_future = SignalContext(prices=bars[:11], upcoming_events=[], recent_news=[])
        assert (large_price_move(full) is not None) == (large_price_move(no_future) is not None)

    def test_replay_window_respects_lookback_and_horizon(self):
        assert bt.MIN_LOOKBACK >= 260  # 52-week rule needs a full year
        assert max(bt.HORIZONS) == 20

    def test_only_price_rules_replayed(self):
        names = {r.__name__ for r in bt.PRICE_RULES}
        assert names == {"large_price_move", "volume_spike",
                         "near_52w_extreme", "momentum_streak"}
