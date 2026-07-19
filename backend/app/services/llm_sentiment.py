"""LLM-based news sentiment scoring via Kimi, with keyword fallback.

When KIMI_API_KEY is configured, headlines are scored in batches by the LLM
(far better than the keyword placeholder: it understands context like
"prices fall on weak demand" vs "prices fall on record harvest" — bullish vs
bearish for different assets). Without a key, or if the API call fails,
each headline silently falls back to the keyword scorer so ingestion never
breaks over sentiment.
"""
from __future__ import annotations

import json
import logging

import httpx

from app.core.config import get_settings
from app.services.news_providers.sentiment import score_text

logger = logging.getLogger(__name__)

# Headlines per API call — big enough for efficiency, small enough that a
# malformed response costs little.
BATCH_SIZE = 20

_SYSTEM = (
    "You are a financial news sentiment scorer. For each headline, output a "
    "sentiment score from -1.0 (very bearish for the asset/market discussed) "
    "to +1.0 (very bullish), considering the asset's perspective. Use 0.0 for "
    "neutral or purely factual headlines. Respond with ONLY a JSON array of "
    "numbers, one per headline, in the same order. No explanations."
)


def _score_batch_llm(headlines: list[str]) -> list[float | None] | None:
    """Score one batch via Kimi. Returns None on any failure."""
    settings = get_settings()
    if not settings.kimi_api_key:
        return None
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{settings.kimi_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.kimi_api_key}"},
                json={
                    "model": settings.kimi_model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": "\n".join(
                            f"{i + 1}. {h}" for i, h in enumerate(headlines)
                        )},
                    ],
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        # Tolerate markdown fences around the JSON array.
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        scores = json.loads(content)
        if not isinstance(scores, list) or len(scores) != len(headlines):
            logger.warning("LLM sentiment: bad shape (%d scores for %d headlines)",
                           len(scores) if isinstance(scores, list) else -1, len(headlines))
            return None
        return [max(-1.0, min(1.0, float(s))) for s in scores]
    except Exception:
        logger.exception("LLM sentiment scoring failed; falling back to keywords")
        return None


def score_headlines(headlines: list[str]) -> list[float | None]:
    """Score headlines with the best available method.

    LLM in batches when configured; keyword scorer per headline otherwise
    (or wherever the LLM batch failed).
    """
    results: list[float | None] = [None] * len(headlines)
    for start in range(0, len(headlines), BATCH_SIZE):
        batch = headlines[start:start + BATCH_SIZE]
        llm_scores = _score_batch_llm(batch)
        for i, headline in enumerate(batch):
            results[start + i] = (
                llm_scores[i] if llm_scores is not None else score_text(headline)
            )
    return results
