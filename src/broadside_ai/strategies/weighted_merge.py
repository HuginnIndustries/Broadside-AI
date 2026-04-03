"""Weighted merge synthesis for structured outputs."""

from __future__ import annotations

import json
from typing import Any

from broadside_ai.gather import GatherResult
from broadside_ai.synthesize import Synthesis


async def synthesize_weighted_merge(
    gathered: GatherResult,
    output_schema: dict[str, Any] | None = None,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    model: str | None = None,
) -> Synthesis:
    """Merge structured outputs using confidence-weighted aggregation."""
    valid = [parsed for parsed in gathered.parsed_outputs if parsed is not None]
    if len(valid) < 2:
        from broadside_ai.synthesize import _synthesize_llm

        fallback = await _synthesize_llm(gathered, backend, backend_kwargs, model)
        fallback.requested_strategy = "weighted_merge"
        return fallback

    weights = _extract_weights(valid)
    merged = _merge_fields(valid, weights)
    text = _format_summary(merged, valid)

    return Synthesis(
        result=text,
        strategy="weighted_merge",
        gather=gathered,
        raw_outputs=gathered.texts,
        synthesis_tokens=0,
        parsed_result=merged,
        requested_strategy="weighted_merge",
    )


def _extract_weights(outputs: list[dict[str, Any]]) -> list[float]:
    weights = []
    for output in outputs:
        confidence = output.get("confidence")
        if isinstance(confidence, (int, float)) and confidence > 0:
            weights.append(float(confidence))
        else:
            weights.append(1.0)

    total = sum(weights)
    if total > 0:
        return [weight / total for weight in weights]
    return [1.0 / len(outputs)] * len(outputs)


def _merge_fields(outputs: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    all_keys: set[str] = set()
    for output in outputs:
        all_keys.update(output.keys())

    all_keys.discard("confidence")

    merged: dict[str, Any] = {}
    for key in sorted(all_keys):
        values = [
            (output[key], weight) for output, weight in zip(outputs, weights) if key in output
        ]
        raw_values = [value for value, _ in values]
        value_weights = [weight for _, weight in values]

        if all(isinstance(value, (int, float)) for value in raw_values):
            merged[key] = _merge_numeric(raw_values, value_weights)
        elif all(isinstance(value, str) for value in raw_values):
            merged[key] = _merge_categorical([str(value) for value in raw_values])
        elif all(isinstance(value, list) for value in raw_values):
            merged[key] = _merge_lists([list(value) for value in raw_values])
        else:
            merged[key] = _merge_categorical([str(value) for value in raw_values])

    return merged


def _merge_numeric(values: list[Any], weights: list[float]) -> float:
    total_weight = sum(weights)
    if total_weight == 0:
        return float(sum(values) / len(values))
    return round(
        float(sum(value * weight for value, weight in zip(values, weights)) / total_weight),
        4,
    )


def _merge_categorical(values: list[str]) -> str:
    from collections import Counter

    return Counter(values).most_common(1)[0][0]


def _merge_lists(values: list[list[Any]]) -> list[Any]:
    from collections import Counter

    all_items: list[Any] = []
    for value_list in values:
        all_items.extend(value_list)

    threshold = len(values) / 2
    counts = Counter(str(item) for item in all_items)
    seen: set[str] = set()
    result: list[Any] = []
    for value_list in values:
        for item in value_list:
            key = str(item)
            if key not in seen and counts[key] >= threshold:
                seen.add(key)
                result.append(item)
    return result


def _format_summary(merged: dict[str, Any], outputs: list[dict[str, Any]]) -> str:
    lines = [
        f"WEIGHTED MERGE ({len(outputs)} agents)",
        "MERGED RESULT:",
        json.dumps(merged, indent=2),
    ]
    return "\n".join(lines)
