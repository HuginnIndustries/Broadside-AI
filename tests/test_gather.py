"""Tests for gather — result normalization."""

from broadside.backends.base import AgentResult
from broadside.gather import gather


def _make_result(text: str = "hello", tokens: int = 100) -> AgentResult:
    return AgentResult(
        text=text,
        tokens_in=tokens,
        tokens_out=tokens,
        latency_ms=50.0,
        model="test-model",
        backend="test",
    )


def test_gather_basic():
    results = [_make_result("a"), _make_result("b"), _make_result("c")]
    g = gather(results, wall_clock_ms=150.0, n_requested=3)
    assert g.n_completed == 3
    assert g.n_failed == 0
    assert g.texts == ["a", "b", "c"]
    assert g.total_tokens == 600  # 3 * (100 in + 100 out)


def test_gather_with_failures():
    results = [_make_result("a")]
    g = gather(results, wall_clock_ms=100.0, n_requested=3)
    assert g.n_completed == 1
    assert g.n_failed == 2


def test_gather_summary():
    results = [_make_result()]
    g = gather(results, wall_clock_ms=100.0)
    s = g.summary()
    assert "completed" in s
    assert "total_tokens" in s
