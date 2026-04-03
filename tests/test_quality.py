"""Tests for quality signals and early termination."""

import pytest

from broadside_ai.quality import EarlyStop, should_stop
from broadside_ai.scatter import scatter
from broadside_ai.task import Task
from tests.conftest import make_result


def test_early_stop_defaults():
    early_stop = EarlyStop()
    assert early_stop.min_complete is None
    assert early_stop.agreement_threshold is None


def test_early_stop_rejects_bad_values():
    with pytest.raises(ValueError):
        EarlyStop(min_complete=1)
    with pytest.raises(ValueError):
        EarlyStop(agreement_threshold=0.0)


def test_should_stop_with_min_complete():
    early_stop = EarlyStop(min_complete=2)
    assert should_stop([make_result("a"), make_result("b")], early_stop) is True


def test_should_stop_with_structured_agreement_ignores_confidence():
    early_stop = EarlyStop(agreement_threshold=1.0)
    first = make_result('{"label": "spam", "confidence": 0.9}')
    second = make_result('{"label": "spam", "confidence": 0.2}')
    assert should_stop([first, second], early_stop) is True


@pytest.mark.asyncio
async def test_parallel_scatter_with_early_stop_returns_partial_results():
    task = Task(prompt="test")
    early_stop = EarlyStop(min_complete=2)
    results = await scatter(task, n=5, backend="mock", parallel=True, early_stop=early_stop)
    assert 2 <= len(results) <= 5


@pytest.mark.asyncio
async def test_sequential_scatter_with_early_stop_stops_immediately():
    task = Task(prompt="test")
    early_stop = EarlyStop(min_complete=2)
    results = await scatter(task, n=5, backend="mock", parallel=False, early_stop=early_stop)
    assert len(results) == 2
