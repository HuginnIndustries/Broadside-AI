"""Integration tests for the Broadside-AI pipeline."""

import pytest

from broadside_ai.gather import gather
from broadside_ai.run import run
from broadside_ai.scatter import scatter
from broadside_ai.synthesize import synthesize
from broadside_ai.task import Task


@pytest.mark.asyncio
async def test_full_pipeline_llm():
    task = Task(prompt="What is 2+2?")
    result = await run(task, n=3, backend="mock")
    assert result.strategy == "llm"
    assert result.result


@pytest.mark.asyncio
async def test_full_pipeline_weighted_merge():
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
    synthesis_result = await synthesize(
        gathered,
        strategy="weighted_merge",
        backend="mock",
        output_schema=task.output_schema,
    )
    assert synthesis_result.requested_strategy == "weighted_merge"
    assert synthesis_result.parsed_result is not None
    assert synthesis_result.parsed_result["label"] == "spam"
