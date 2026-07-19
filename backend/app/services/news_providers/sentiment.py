"""Keyword-based sentiment scoring — a transparent PLACEHOLDER.

This is a simple lexicon scorer, not NLP. It exists so the signal engine's
sentiment rule works on real articles before a proper AI/NLP pipeline is
added. Scores are deliberately coarse: (#positive - #negative) / (#total),
clamped to [-1, 1]. Returns None when no signal words are found, so neutral
headlines don't pollute the average.
"""
from __future__ import annotations

POSITIVE = {
    "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains",
    "jump", "jumps", "rise", "rises", "beat", "beats", "record", "growth",
    "profit", "strong", "upgrade", "upgraded", "bullish", "boost", "boosts",
    "outperform", "breakthrough", "expands", "expansion", "optimism",
}
NEGATIVE = {
    "fall", "falls", "drop", "drops", "plunge", "plunges", "crash", "decline",
    "declines", "miss", "misses", "loss", "losses", "weak", "downgrade",
    "downgraded", "bearish", "warning", "warns", "risk", "crisis", "slump",
    "fear", "concerns", "cut", "cuts", "shortage", "deficit", "recall",
}


def score_text(text: str) -> float | None:
    words = {w.strip(".,!?;:\"'()").lower() for w in text.split()}
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    if pos + neg == 0:
        return None
    return round((pos - neg) / (pos + neg), 2)
