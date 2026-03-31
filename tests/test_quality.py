"""Tests for quality signals and early termination."""

import pytest

from broadside_ai.backends.base import AgentResult
from broadside_ai.quality import EarlyStop, should_stop


def _make_result(text: str = "hello") -> AgentResult:
    return AgentResult(
        text=text,
        tokens_in=10,
        tokens_out=10,
        latency_ms=5.0,
        model="test",
        backend="test",
    )


# --- EarlyStop validation ---


def test_early_stop_defaults():
    es = EarlyStop()
    assert es.min_complete is None
    assert es.agreement_threshold is None


def test_early_stop_rejects_min_complete_one():
    with pytest.raises(ValueError, match="min_complete must be >= 2"):
        EarlyStop(min_complete=1)


def test_early_stop_rejects_bad_threshold():
    with pytest.raises(ValueError):
        EarlyStop(agreement_threshold=0.0)
    with pytest.raises(ValueError):
        EarlyStop(agreement_threshold=1.5)


# --- should_stop with min_complete ---


def test_stop_at_min_complete():
    es = EarlyStop(min_complete=2)
    results = [_make_result("a"), _make_result("b")]
    assert should_stop(results, es) is True


def test_no_stop_below_min_complete():
    es = EarlyStop(min_complete=3)
    results = [_make_result("a"), _make_result("b")]
    assert should_stop(results, es) is False


def test_no_stop_with_one_result():
    es = EarlyStop(min_complete=2)
    results = [_make_result("a")]
    assert should_stop(results, es) is False


# --- should_stop with agreement ---


def test_stop_on_unanimous_agreement():
    es = EarlyStop(agreement_threshold=1.0)
    results = [_make_result("same"), _make_result("same"), _make_result("same")]
    assert should_stop(results, es) is True


def test_no_stop_on_disagreement():
    es = EarlyStop(agreement_threshold=1.0)
    results = [_make_result("yes"), _make_result("no")]
    assert should_stop(results, es) is False


def test_stop_on_majority_agreement():
    es = EarlyStop(agreement_threshold=0.66)
    results = [_make_result("yes"), _make_result("yes"), _make_result("no")]
    assert should_stop(results, es) is True


def test_no_stop_below_majority():
    es = EarlyStop(agreement_threshold=0.75)
    results = [_make_result("a"), _make_result("b"), _make_result("c")]
    assert should_stop(results, es) is False


# --- should_stop with both min_complete and agreement ---


def test_stop_requires_both_when_set():
    """When both min_complete and agreement are set, both must be satisfied."""
    es = EarlyStop(min_complete=2, agreement_threshold=1.0)
    # 2 results that agree → should stop
    results = [_make_result("same"), _make_result("same")]
    assert should_stop(results, es) is True


def test_no_stop_min_met_but_no_agreement():
    """min_complete met but results disagree → don't stop."""
    es = EarlyStop(min_complete=2, agreement_threshold=1.0)
    results = [_make_result("yes"), _make_result("no")]
    assert should_stop(results, es) is False


# --- Agreement with structured outputs ---


def test_agreement_with_json():
    """Structured outputs are compared by parsed content."""
    es = EarlyStop(agreement_threshold=1.0)
    r1 = _make_result('{"label": "spam", "confidence": 0.9}')
    r2 = _make_result('{"label": "spam", "confidence": 0.7}')
    # Same label, different confidence → should agree (confidence is ignored)
    assert should_stop([r1, r2], es) is True


def test_disagreement_with_json():
    es = EarlyStop(agreement_threshold=1.0)
    r1 = _make_result('{"label": "spam"}')
    r2 = _make_result('{"label": "ham"}')
    assert should_stop([r1, r2], es) is False


# --- Scatter integration ---


@pytest.mark.asyncio
async def test_scatter_with_early_stop():
    """Scatter with early_stop returns fewer results when signals fire."""
    from broadside_ai.scatter import scatter
    from broadside_ai.task import Task

    task = Task(prompt="test")
    es = EarlyStop(min_complete=2)
    results = await scatter(task, n=5, backend="mock", parallel=True, early_stop=es)
    # Should get at least 2 but potentially fewer than 5
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_scatter_sequential_with_early_stop():
    """Sequential scatter with early_stop stops after enough results."""
    from broadside_ai.scatter import scatter
    from broadside_ai.task import Task

    task = Task(prompt="test")
    es = EarlyStop(min_complete=2)
    results = await scatter(task, n=5, backend="mock", parallel=False, early_stop=es)
    # Sequential stops immediately after min_complete
    assert len(results) == 2


@pytest.mark.asyncio
async def test_scatter_without_early_stop_returns_all():
    """Without early_stop, all branches complete."""
    from broadside_ai.scatter import scatter
    from broadside_ai.task import Task

    task = Task(prompt="test")
    results = await scatter(task, n=3, backend="mock", parallel=True)
    assert len(results) == 3
