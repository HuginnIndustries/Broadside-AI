"""Shared test fixtures for Broadside-AI."""

from __future__ import annotations

import json

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
from broadside_ai.gather import GatherResult, gather


class MockBackend(Backend):
    """A backend that returns canned responses without calling any API."""

    def __init__(self, responses: list[str] | None = None, **kwargs: object) -> None:
        self._responses = responses or ["mock response"]
        self._call_count = 0

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return AgentResult(
            text=text,
            tokens_in=10,
            tokens_out=20,
            latency_ms=5.0,
            model="mock-model",
            backend="mock",
        )

    def name(self) -> str:
        return "mock"


class JsonMockBackend(Backend):
    """A backend that returns JSON responses for structured output tests."""

    def __init__(self, **kwargs: object) -> None:
        self._call_count = 0
        self._responses = [
            {"label": "spam", "confidence": 0.9, "score": 8, "tags": ["python", "ai"]},
            {"label": "spam", "confidence": 0.7, "score": 7, "tags": ["python", "ml"]},
            {"label": "ham", "confidence": 0.3, "score": 5, "tags": ["python", "ai"]},
        ]

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        data = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return AgentResult(
            text=json.dumps(data),
            tokens_in=10,
            tokens_out=20,
            latency_ms=5.0,
            model="json-mock",
            backend="json-mock",
        )

    def name(self) -> str:
        return "json-mock"


register("mock", MockBackend)
register("json-mock", JsonMockBackend)


def make_result(text: str = "hello", tokens: int = 100) -> AgentResult:
    return AgentResult(
        text=text,
        tokens_in=tokens,
        tokens_out=tokens,
        latency_ms=50.0,
        model="test-model",
        backend="test",
    )


def make_gather(texts: list[str]) -> GatherResult:
    results = [make_result(text) for text in texts]
    return gather(results, wall_clock_ms=100.0, n_requested=len(texts))
