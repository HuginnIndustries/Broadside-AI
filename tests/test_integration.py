"""Integration tests — full scatter/gather/synthesize with mock backend."""

import pytest

from broadside_ai.gather import gather
from broadside_ai.scatter import scatter
from broadside_ai.synthesize import Synthesis, synthesize
from broadside_ai.task import Task

# conftest.py registers the "mock" backend on import


@pytest.mark.asyncio
async def test_full_pipeline():
    """End-to-end: scatter → gather → synthesize with mock backend."""
    task = Task(prompt="What is 2+2?")

    # Scatter
    results = await scatter(task, n=3, backend="mock", parallel=True)
    assert len(results) == 3

    # Gather
    gathered = gather(results, wall_clock_ms=100.0, n_requested=3)
    assert gathered.n_completed == 3
    assert gathered.n_failed == 0
    assert len(gathered.texts) == 3

    # Synthesize (LLM strategy)
    synthesis = await synthesize(gathered, strategy="llm", backend="mock")
    assert isinstance(synthesis, Synthesis)
    assert synthesis.strategy == "llm"
    assert synthesis.result  # non-empty
    assert synthesis.total_tokens() > 0


@pytest.mark.asyncio
async def test_full_pipeline_consensus():
    """End-to-end with consensus strategy."""
    task = Task(prompt="What is the capital of France?")
    results = await scatter(task, n=3, backend="mock", parallel=True)
    gathered = gather(results, wall_clock_ms=50.0, n_requested=3)
    synthesis = await synthesize(gathered, strategy="consensus", backend="mock")
    assert synthesis.strategy == "consensus"


@pytest.mark.asyncio
async def test_full_pipeline_voting():
    """End-to-end with voting strategy."""
    task = Task(prompt="Is this spam? yes or no")
    results = await scatter(task, n=3, backend="mock", parallel=True)
    gathered = gather(results, wall_clock_ms=50.0, n_requested=3)
    synthesis = await synthesize(gathered, strategy="voting", backend="mock")
    assert synthesis.strategy == "voting"


@pytest.mark.asyncio
async def test_scatter_sequential():
    """Scatter with parallel=False runs sequentially."""
    task = Task(prompt="test")
    results = await scatter(task, n=3, backend="mock", parallel=False)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_scatter_rejects_zero():
    """n=0 should raise ValueError."""
    task = Task(prompt="test")
    with pytest.raises(ValueError, match="n must be >= 1"):
        await scatter(task, n=0, backend="mock")


@pytest.mark.asyncio
async def test_scatter_with_context():
    """Scatter preserves task context in the prompt."""
    task = Task(
        prompt="Compare databases",
        context={"db1": "PostgreSQL", "db2": "MySQL"},
    )
    results = await scatter(task, n=2, backend="mock")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_synthesize_unknown_strategy():
    """Unknown strategy raises ValueError."""
    task = Task(prompt="test")
    results = await scatter(task, n=2, backend="mock")
    gathered = gather(results, wall_clock_ms=10.0, n_requested=2)
    with pytest.raises(ValueError, match="Unknown synthesis strategy"):
        await synthesize(gathered, strategy="nonexistent", backend="mock")


@pytest.mark.asyncio
async def test_scatter_with_budget():
    """Scatter with a token budget tracks usage."""
    from broadside_ai.budget import ScatterBudget

    budget = ScatterBudget(max_tokens=10000)
    task = Task(prompt="test")
    results = await scatter(task, n=3, backend="mock", budget=budget)
    assert len(results) == 3
    assert budget.used > 0
