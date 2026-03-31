"""Tests for weighted merge synthesis strategy."""

import json

import pytest

from broadside_ai.backends.base import AgentResult
from broadside_ai.gather import gather
from broadside_ai.strategies.weighted_merge import (
    _extract_weights,
    _merge_fields,
    synthesize_weighted_merge,
)


def _make_json_result(data: dict, tokens: int = 100) -> AgentResult:
    """Create an AgentResult with JSON text."""
    return AgentResult(
        text=json.dumps(data),
        tokens_in=tokens,
        tokens_out=tokens,
        latency_ms=50.0,
        model="test-model",
        backend="test",
    )


def _gather_json(outputs: list[dict]) -> tuple:
    """Create a GatherResult with parsed JSON outputs."""
    results = [_make_json_result(d) for d in outputs]
    schema = {"score": "float", "label": "string"}
    gathered = gather(results, wall_clock_ms=100.0, n_requested=len(results), output_schema=schema)
    return gathered


@pytest.mark.asyncio
async def test_uniform_numeric_merge():
    """Three agents with numeric scores, uniform weights."""
    outputs = [
        {"score": 7.0, "label": "good"},
        {"score": 8.0, "label": "good"},
        {"score": 9.0, "label": "good"},
    ]
    gathered = _gather_json(outputs)
    result = await synthesize_weighted_merge(gathered)
    assert result.strategy == "weighted_merge"
    assert result.parsed_result is not None
    assert result.parsed_result["score"] == pytest.approx(8.0, abs=0.01)
    assert result.parsed_result["label"] == "good"
    assert result.synthesis_tokens == 0  # no LLM calls


@pytest.mark.asyncio
async def test_confidence_weighted_merge():
    """Agent with higher confidence should dominate."""
    outputs = [
        {"score": 10.0, "confidence": 0.9, "label": "A"},
        {"score": 5.0, "confidence": 0.1, "label": "B"},
    ]
    gathered = _gather_json(outputs)
    result = await synthesize_weighted_merge(gathered)
    assert result.parsed_result is not None
    # Score should be heavily weighted toward 10.0
    assert result.parsed_result["score"] > 8.0


@pytest.mark.asyncio
async def test_categorical_majority_vote():
    """String fields use majority vote."""
    outputs = [
        {"label": "spam", "score": 1},
        {"label": "spam", "score": 2},
        {"label": "ham", "score": 3},
    ]
    gathered = _gather_json(outputs)
    result = await synthesize_weighted_merge(gathered)
    assert result.parsed_result is not None
    assert result.parsed_result["label"] == "spam"


@pytest.mark.asyncio
async def test_fallback_to_llm_with_no_parsed():
    """Falls back to LLM synthesis when outputs aren't structured."""
    results = [
        AgentResult(
            text="plain text",
            tokens_in=10,
            tokens_out=10,
            latency_ms=5.0,
            model="m",
            backend="b",
        )
        for _ in range(3)
    ]
    gathered = gather(results, wall_clock_ms=50.0, n_requested=3)
    # No output_schema means no parsing, so parsed_outputs is empty
    result = await synthesize_weighted_merge(gathered, backend="mock")
    # Falls back to LLM — strategy is still weighted_merge? No, it's "llm" from fallback
    assert result.strategy == "llm"


@pytest.mark.asyncio
async def test_fallback_with_single_parsed():
    """Falls back when only 1 output parsed (need >= 2)."""
    results = [
        _make_json_result({"score": 5}),
        AgentResult(
            text="not json",
            tokens_in=10,
            tokens_out=10,
            latency_ms=5.0,
            model="m",
            backend="b",
        ),
    ]
    schema = {"score": "float"}
    gathered = gather(results, wall_clock_ms=50.0, n_requested=2, output_schema=schema)
    result = await synthesize_weighted_merge(gathered, backend="mock")
    assert result.strategy == "llm"  # fell back


@pytest.mark.asyncio
async def test_list_merge():
    """List fields keep items from majority."""
    outputs = [
        {"tags": ["python", "ai", "web"]},
        {"tags": ["python", "ai", "ml"]},
        {"tags": ["python", "ai"]},
    ]
    gathered = _gather_json(outputs)
    result = await synthesize_weighted_merge(gathered)
    assert result.parsed_result is not None
    tags = result.parsed_result["tags"]
    assert "python" in tags
    assert "ai" in tags


@pytest.mark.asyncio
async def test_result_text_includes_json():
    """The text result should include the merged JSON."""
    outputs = [{"score": 5}, {"score": 5}]
    gathered = _gather_json(outputs)
    result = await synthesize_weighted_merge(gathered)
    assert "WEIGHTED MERGE" in result.result
    assert '"score"' in result.result


def test_extract_weights_with_confidence():
    """Weights should be normalized from confidence values."""
    outputs = [{"confidence": 0.8}, {"confidence": 0.2}]
    weights = _extract_weights(outputs)
    assert weights[0] == pytest.approx(0.8, abs=0.01)
    assert weights[1] == pytest.approx(0.2, abs=0.01)


def test_extract_weights_uniform():
    """Without confidence fields, weights should be uniform."""
    outputs = [{"score": 1}, {"score": 2}]
    weights = _extract_weights(outputs)
    assert weights == [0.5, 0.5]


def test_merge_fields_mixed():
    """Merge with both numeric and string fields."""
    outputs = [
        {"score": 8.0, "label": "good"},
        {"score": 6.0, "label": "ok"},
        {"score": 7.0, "label": "good"},
    ]
    weights = [1 / 3, 1 / 3, 1 / 3]
    merged = _merge_fields(outputs, weights)
    assert merged["score"] == pytest.approx(7.0, abs=0.01)
    assert merged["label"] == "good"  # majority
