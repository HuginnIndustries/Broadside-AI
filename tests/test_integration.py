"""Integration tests — full scatter/gather/synthesize with mock backend."""

import json

import pytest

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
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


class JsonMockBackend(Backend):
    """Mock backend that returns JSON responses for structured output testing."""

    def __init__(self, **kwargs: object) -> None:
        self._call_count = 0
        self._responses = [
            {"label": "spam", "confidence": 0.9, "score": 8},
            {"label": "spam", "confidence": 0.7, "score": 7},
            {"label": "ham", "confidence": 0.3, "score": 5},
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


register("json-mock", JsonMockBackend)


@pytest.mark.asyncio
async def test_full_pipeline_weighted_merge():
    """End-to-end with weighted_merge strategy and structured outputs."""
    task = Task(
        prompt="Classify this email",
        output_schema={"label": "string", "confidence": "float", "score": "int"},
    )
    results = await scatter(task, n=3, backend="json-mock", parallel=True)
    gathered = gather(
        results,
        wall_clock_ms=50.0,
        n_requested=3,
        output_schema=task.output_schema,
    )
    assert gathered.n_parsed == 3

    synthesis = await synthesize(
        gathered,
        strategy="weighted_merge",
        backend="mock",
        output_schema=task.output_schema,
    )
    assert synthesis.strategy == "weighted_merge"
    assert synthesis.parsed_result is not None
    assert synthesis.parsed_result["label"] == "spam"  # majority
    assert synthesis.synthesis_tokens == 0  # no LLM calls


@pytest.mark.asyncio
async def test_structured_output_with_llm_strategy():
    """LLM strategy still works when structured outputs are available."""
    task = Task(
        prompt="Classify this",
        output_schema={"label": "string"},
    )
    results = await scatter(task, n=2, backend="json-mock", parallel=True)
    gathered = gather(
        results,
        wall_clock_ms=50.0,
        n_requested=2,
        output_schema=task.output_schema,
    )
    assert gathered.n_parsed == 2
    # LLM strategy ignores parsed outputs, still works
    synthesis = await synthesize(gathered, strategy="llm", backend="mock")
    assert synthesis.strategy == "llm"
