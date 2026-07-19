"""Unit tests for LLM sentiment scoring (mocked HTTP) and keyword fallback."""
from __future__ import annotations

import json

import app.services.llm_sentiment as llm


class FakeResponse:
    def __init__(self, scores):
        self._scores = scores

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": json.dumps(self._scores)}}]}


class FakeClient:
    """Stands in for httpx.Client; captures the request and replays scores."""
    last_payload = None
    scores = [0.5]

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, headers=None, json=None):
        FakeClient.last_payload = json
        return FakeResponse(FakeClient.scores)


def _configure(monkeypatch, api_key="test-key"):
    monkeypatch.setattr(llm, "get_settings", lambda: type(
        "S", (), {"kimi_api_key": api_key,
                  "kimi_base_url": "https://example.test/v1",
                  "kimi_model": "test-model"})())
    monkeypatch.setattr(llm.httpx, "Client", FakeClient)


class TestLlmScoring:
    def test_parses_scores_in_order(self, monkeypatch):
        _configure(monkeypatch)
        FakeClient.scores = [0.9, -0.4, 0.0]
        result = llm.score_headlines(["a", "b", "c"])
        assert result == [0.9, -0.4, 0.0]

    def test_scores_clamped_to_range(self, monkeypatch):
        _configure(monkeypatch)
        FakeClient.scores = [5.0, -7.0]
        assert llm.score_headlines(["a", "b"]) == [1.0, -1.0]

    def test_wrong_count_falls_back_to_keywords(self, monkeypatch):
        _configure(monkeypatch)
        FakeClient.scores = [0.5]  # 1 score for 2 headlines -> batch rejected
        result = llm.score_headlines(["record profit beats estimates", "markets quiet"])
        assert result[0] is not None  # keyword scorer caught "record/profit/beat(s)"
        assert result[1] is None      # no keyword hit

    def test_markdown_fences_tolerated(self, monkeypatch):
        _configure(monkeypatch)

        class FencedClient(FakeClient):
            def post(self, url, headers=None, json=None):
                return type("R", (), {
                    "raise_for_status": lambda self: None,
                    "json": lambda self: {"choices": [{"message": {
                        "content": "```json\n[0.3]\n```"}}]},
                })()

        monkeypatch.setattr(llm.httpx, "Client", FencedClient)
        assert llm.score_headlines(["a"]) == [0.3]


class TestFallback:
    def test_no_key_uses_keyword_scorer(self, monkeypatch):
        _configure(monkeypatch, api_key="")
        result = llm.score_headlines(["record profit", "markets quiet"])
        assert result[0] is not None
        assert result[1] is None

    def test_api_error_falls_back(self, monkeypatch):
        _configure(monkeypatch)

        class BoomClient(FakeClient):
            def post(self, url, headers=None, json=None):
                raise ConnectionError("down")

        monkeypatch.setattr(llm.httpx, "Client", BoomClient)
        result = llm.score_headlines(["record profit"])
        assert result == [llm.score_text("record profit")]
