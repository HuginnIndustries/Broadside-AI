"""Tests for weighted merge synthesis."""

import json

import pytest

from broadside_ai.backends.base import AgentResult
from broadside_ai.gather import gather
from broadside_ai.strategies.weighted_merge import (
    _extract_weights,
    _merge_fields,
    _merge_lists,
    synthesize_weighted_merge,
)


def _make_json_result(data: dict[str, object], tokens: int = 100) -> AgentResult:
    return AgentResult(
        text=json.dumps(data),
        tokens_in=tokens,
        tokens_out=tokens,
        latency_ms=50.0,
        model="test-model",
        backend="test",
    )


def _gather_json(outputs: list[dict[str, object]]):
    results = [_make_json_result(output) for output in outputs]
    schema = {"score": "float", "label": "string", "tags": "list"}
    return gather(results, wall_clock_ms=100.0, n_requested=len(results), output_schema=schema)


@pytest.mark.asyncio
async def test_uniform_numeric_merge():
    gathered = _gather_json(
        [
            {"score": 7.0, "label": "good"},
            {"score": 8.0, "label": "good"},
            {"score": 9.0, "label": "good"},
        ]
    )
    result = await synthesize_weighted_merge(gathered)
    assert result.strategy == "weighted_merge"
    assert result.requested_strategy == "weighted_merge"
    assert result.parsed_result is not None
    assert result.parsed_result["score"] == pytest.approx(8.0, abs=0.01)
    assert result.synthesis_tokens == 0


@pytest.mark.asyncio
async def test_confidence_weighted_merge():
    gathered = _gather_json(
        [
            {"score": 10.0, "confidence": 0.9, "label": "A"},
            {"score": 5.0, "confidence": 0.1, "label": "B"},
        ]
    )
    result = await synthesize_weighted_merge(gathered)
    assert result.parsed_result is not None
    assert result.parsed_result["score"] > 8.0


@pytest.mark.asyncio
async def test_list_merge():
    gathered = _gather_json(
        [
            {"tags": ["python", "ai", "web"]},
            {"tags": ["python", "ai", "ml"]},
            {"tags": ["python", "ai"]},
        ]
    )
    result = await synthesize_weighted_merge(gathered)
    assert result.parsed_result is not None
    assert "python" in result.parsed_result["tags"]
    assert "ai" in result.parsed_result["tags"]


@pytest.mark.asyncio
async def test_fallback_to_llm_marks_requested_strategy():
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
    result = await synthesize_weighted_merge(gathered, backend="mock")
    assert result.strategy == "llm"
    assert result.requested_strategy == "weighted_merge"


def test_extract_weights_uniform():
    assert _extract_weights([{"score": 1}, {"score": 2}]) == [0.5, 0.5]


def test_merge_fields_numeric_and_majority():
    merged = _merge_fields(
        [
            {"score": 8.0, "label": "good"},
            {"score": 6.0, "label": "ok"},
            {"score": 7.0, "label": "good"},
        ],
        [1 / 3, 1 / 3, 1 / 3],
    )
    assert merged["score"] == pytest.approx(7.0, abs=0.01)
    assert merged["label"] == "good"


def test_merge_fields_booleans_use_majority_vote():
    merged = _merge_fields(
        [
            {"approved": True},
            {"approved": False},
            {"approved": True},
        ],
        [1 / 3, 1 / 3, 1 / 3],
    )
    assert merged["approved"] is True


def test_merge_lists_requires_strict_majority():
    assert _merge_lists([["python"], ["ai"]]) == []
    assert _merge_lists([["python"], ["python"], ["ai"], ["ai"]]) == []
