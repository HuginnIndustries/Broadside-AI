"""Tests for budget circuit breaker."""

import pytest

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
from broadside_ai.budget import BudgetExceeded, ScatterBudget
from broadside_ai.scatter import scatter
from broadside_ai.task import Task


class BudgetProbeBackend(Backend):
    """Backend with configurable token usage for budget tests."""

    def __init__(self, tokens_per_side: int = 500, **kwargs: object) -> None:
        self.tokens_per_side = tokens_per_side

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        return AgentResult(
            text="budget probe",
            tokens_in=self.tokens_per_side,
            tokens_out=self.tokens_per_side,
            latency_ms=5.0,
            model="budget-probe",
            backend="budget-probe",
        )

    def name(self) -> str:
        return "budget-probe"


register("budget-probe", BudgetProbeBackend)


def test_unbounded_budget():
    b = ScatterBudget()
    b.record(1000)
    b.record(5000)
    assert b.used == 6000
    assert not b.exhausted
    assert b.remaining is None


def test_budget_within_limit():
    b = ScatterBudget(max_tokens=10000)
    b.record(3000)
    assert b.used == 3000
    assert b.remaining == 7000
    assert not b.exhausted


def test_budget_exceeded():
    b = ScatterBudget(max_tokens=5000)
    b.record(3000)
    with pytest.raises(BudgetExceeded) as exc_info:
        b.record(3000)
    assert exc_info.value.limit == 5000
    assert exc_info.value.used == 6000


def test_budget_exhausted_flag():
    b = ScatterBudget(max_tokens=1000)
    b.record(500)
    assert not b.exhausted
    # Manually push past limit to test exhausted check
    b._used = 1000
    assert b.exhausted


def test_budget_exact_boundary_raises():
    """record() and exhausted must agree at the exact boundary."""
    b = ScatterBudget(max_tokens=1000)
    with pytest.raises(BudgetExceeded):
        b.record(1000)
    assert b.exhausted


@pytest.mark.asyncio
async def test_scatter_keeps_result_that_exhausts_budget():
    budget = ScatterBudget(max_tokens=1000)

    results = await scatter(
        Task(prompt="test"),
        n=3,
        backend="budget-probe",
        backend_kwargs={"tokens_per_side": 500},
        budget=budget,
        parallel=False,
    )

    assert len(results) == 1
    assert results[0].text == "budget probe"
