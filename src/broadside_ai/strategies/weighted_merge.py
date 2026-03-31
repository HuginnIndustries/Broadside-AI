"""Weighted merge synthesis — best for scored recommendations.

Aggregates structured outputs field-by-field:
- Numeric fields: confidence-weighted average
- String fields: majority vote
- List fields: union of items appearing in majority of outputs

Requires structured outputs (output_schema on the task). Falls back to
LLM synthesis if fewer than 2 outputs parsed successfully.

This is the right strategy when:
- The task produces structured data (JSON with typed fields)
- Agents return confidence scores alongside their answers
- You want a principled numeric aggregation, not just text blending
"""

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
    """Merge structured outputs using confidence-weighted aggregation.

    Falls back to LLM synthesis when structured data is unavailable.
    On the happy path, does zero LLM calls — pure algorithmic merge.
    """
    valid = [p for p in gathered.parsed_outputs if p is not None]

    if len(valid) < 2:
        # Not enough structured data — fall back to LLM synthesis
        from broadside_ai.synthesize import _synthesize_llm

        return await _synthesize_llm(gathered, backend, backend_kwargs, model)

    # Extract confidence weights (if present), else uniform
    weights = _extract_weights(valid)

    # Merge field by field
    merged = _merge_fields(valid, weights)

    # Build human-readable summary
    text = _format_summary(merged, valid, weights)

    return Synthesis(
        result=text,
        strategy="weighted_merge",
        gather=gathered,
        raw_outputs=gathered.texts,
        synthesis_tokens=0,  # no LLM calls
        parsed_result=merged,
    )


def _extract_weights(outputs: list[dict[str, Any]]) -> list[float]:
    """Extract confidence scores as weights, or use uniform weights."""
    weights = []
    for out in outputs:
        conf = out.get("confidence")
        if isinstance(conf, (int, float)) and conf > 0:
            weights.append(float(conf))
        else:
            weights.append(1.0)

    # Normalize to sum to 1
    total = sum(weights)
    if total > 0:
        weights = [w / total for w in weights]
    else:
        n = len(outputs)
        weights = [1.0 / n] * n

    return weights


def _merge_fields(outputs: list[dict[str, Any]], weights: list[float]) -> dict[str, Any]:
    """Merge each field using type-appropriate aggregation."""
    # Collect all keys across outputs
    all_keys: set[str] = set()
    for out in outputs:
        all_keys.update(out.keys())

    # Don't merge the confidence field itself — it's metadata
    all_keys.discard("confidence")

    merged: dict[str, Any] = {}
    for key in sorted(all_keys):
        values = [(out.get(key), w) for out, w in zip(outputs, weights) if key in out]
        if not values:
            continue

        raw_vals = [v for v, _ in values]
        val_weights = [w for _, w in values]

        if all(isinstance(v, (int, float)) for v in raw_vals):
            merged[key] = _merge_numeric(raw_vals, val_weights)
        elif all(isinstance(v, str) for v in raw_vals):
            merged[key] = _merge_categorical(raw_vals)
        elif all(isinstance(v, list) for v in raw_vals):
            merged[key] = _merge_lists(raw_vals)
        else:
            # Mixed types or unsupported — take the most common
            merged[key] = _merge_categorical([str(v) for v in raw_vals])

    return merged


def _merge_numeric(values: list[Any], weights: list[float]) -> float:
    """Weighted average of numeric values."""
    total_weight = sum(weights)
    if total_weight == 0:
        return sum(values) / len(values)
    return round(sum(v * w for v, w in zip(values, weights)) / total_weight, 4)


def _merge_categorical(values: list[str]) -> str:
    """Majority vote for string values."""
    from collections import Counter

    counts = Counter(values)
    return counts.most_common(1)[0][0]


def _merge_lists(values: list[list[Any]]) -> list[Any]:
    """Keep items that appear in a majority of outputs."""
    from collections import Counter

    n = len(values)
    threshold = n / 2
    all_items: list[Any] = []
    for lst in values:
        all_items.extend(lst)
    counts = Counter(str(item) for item in all_items)

    # Build ordered result: keep items appearing in majority, preserve first-seen order
    seen: set[str] = set()
    result: list[Any] = []
    for lst in values:
        for item in lst:
            key = str(item)
            if key not in seen and counts[key] >= threshold:
                seen.add(key)
                result.append(item)
    return result


def _format_summary(
    merged: dict[str, Any],
    outputs: list[dict[str, Any]],
    weights: list[float],
) -> str:
    """Build a human-readable summary of the merge."""
    n = len(outputs)
    has_confidence = any("confidence" in out for out in outputs)

    lines = [
        f"WEIGHTED MERGE ({n} agents)",
        f"Weighting: {'confidence-based' if has_confidence else 'uniform'}",
        "",
        "MERGED RESULT:",
        json.dumps(merged, indent=2),
        "",
        "FIELD DETAILS:",
    ]

    for key, value in merged.items():
        agent_vals = [out.get(key) for out in outputs if key in out]
        unique = len(set(str(v) for v in agent_vals))
        if unique == 1:
            lines.append(f"  {key}: {value} (unanimous)")
        elif isinstance(value, float):
            vals_str = ", ".join(str(v) for v in agent_vals)
            lines.append(f"  {key}: {value} (weighted avg of [{vals_str}])")
        else:
            lines.append(f"  {key}: {value} ({unique} distinct values, majority wins)")

    return "\n".join(lines)
