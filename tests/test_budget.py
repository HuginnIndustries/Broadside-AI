"""Tests for budget circuit breaker."""

import pytest

from broadside_ai.budget import BudgetExceeded, ScatterBudget


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
