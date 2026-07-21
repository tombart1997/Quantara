"""News sentiment scoring — hybrid finance lexicon + VADER. Fully offline,
no API key, by design.

Two layers:
  1. A FINANCE-SPECIFIC lexicon (verbs and nouns that actually move markets:
     plunge, shortage, downgrade, ...) — scored as (pos-neg)/(pos+neg).
     Finance words win when present, because VADER's social-media lexicon
     misses them ("prices fall sharply" -> 0.0 in vanilla VADER).
  2. VADER compound score as fallback — 7,500 graded entries, negation and
     emphasis aware ("not good", "VERY strong").

Returns None when neither layer finds a signal, so neutral headlines don't
pollute averages. Honest limits: still bag-of-words — it reads mood, not
market direction ("shortage" is bearish text even when bullish for prices).
"""
from __future__ import annotations

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

POSITIVE = {
    "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains",
    "jump", "jumps", "rise", "rises", "beat", "beats", "record", "growth",
    "profit", "strong", "upgrade", "upgraded", "bullish", "boost", "boosts",
    "outperform", "breakthrough", "expands", "expansion", "optimism", "rebound",
}
NEGATIVE = {
    "fall", "falls", "drop", "drops", "plunge", "plunges", "crash", "decline",
    "declines", "miss", "misses", "loss", "losses", "weak", "downgrade",
    "downgraded", "bearish", "warning", "warns", "risk", "crisis", "slump",
    "fear", "concerns", "cut", "cuts", "shortage", "deficit", "recall",
}

_analyzer: SentimentIntensityAnalyzer | None = None


def _vader() -> SentimentIntensityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


def score_text(text: str) -> float | None:
    words = {w.strip(".,!?;:\"'()").lower() for w in text.split()}
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    if pos + neg > 0:
        # Finance lexicon hit. Laplace-smoothed (+1) so a single keyword
        # scores 0.5, two score 0.67, three 0.75 — avoids the false
        # precision of ±1.0 from one word.
        return round((pos - neg) / (pos + neg + 1), 2)
    compound = _vader().polarity_scores(text)["compound"]
    return round(compound, 2) if compound != 0 else None
