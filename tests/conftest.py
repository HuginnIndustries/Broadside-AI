"""Shared test fixtures — mock backend, helper factories."""

from __future__ import annotations

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


# Register mock backend so get_backend("mock") works
register("mock", MockBackend)


def make_result(text: str = "hello", tokens: int = 100) -> AgentResult:
    """Create a test AgentResult."""
    return AgentResult(
        text=text,
        tokens_in=tokens,
        tokens_out=tokens,
        latency_ms=50.0,
        model="test-model",
        backend="test",
    )


def make_gather(texts: list[str]) -> GatherResult:
    """Create a GatherResult from a list of text strings."""
    results = [make_result(t) for t in texts]
    return gather(results, wall_clock_ms=100.0, n_requested=len(texts))
