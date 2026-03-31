"""Gather — collect and normalize scatter results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from broadside_ai.backends.base import AgentResult


@dataclass
class GatherResult:
    """Normalized collection of scatter outputs, ready for synthesis.

    This is the natural HITL checkpoint — all results are in, nothing has
    been decided yet. A human (or synthesizer) reviews from here.
    """

    results: list[AgentResult]
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    wall_clock_ms: float = 0.0  # actual elapsed time (parallel, so < sum of latencies)

    # Populated during gather
    texts: list[str] = field(default_factory=list)
    n_completed: int = 0
    n_failed: int = 0

    # Structured output parsing (populated when output_schema is provided)
    parsed_outputs: list[dict[str, Any] | None] = field(default_factory=list)
    n_parsed: int = 0

    def summary(self) -> dict[str, object]:
        """Quick stats for logging or HITL display."""
        result: dict[str, object] = {
            "completed": self.n_completed,
            "failed": self.n_failed,
            "total_tokens": self.total_tokens,
            "wall_clock_ms": round(self.wall_clock_ms, 1),
            "models_used": list({r.model for r in self.results}),
        }
        if self.parsed_outputs:
            result["n_parsed"] = self.n_parsed
        return result


def gather(
    results: list[AgentResult],
    wall_clock_ms: float = 0.0,
    n_requested: int | None = None,
    output_schema: dict[str, Any] | None = None,
) -> GatherResult:
    """Collect scatter outputs into a normalized structure.

    Args:
        results: Completed AgentResults from scatter.
        wall_clock_ms: Actual elapsed wall-clock time for the scatter.
        n_requested: How many branches were requested (to calculate failure count).
        output_schema: If provided, attempt JSON parsing on each result.
    """
    n_failed = (n_requested - len(results)) if n_requested else 0

    parsed_outputs: list[dict[str, Any] | None] = []
    n_parsed = 0

    if output_schema is not None:
        from broadside_ai.parsing import try_parse_json

        for r in results:
            parsed = try_parse_json(r.text)
            r.parsed = parsed
            parsed_outputs.append(parsed)
            if parsed is not None:
                n_parsed += 1

    return GatherResult(
        results=results,
        total_tokens=sum(r.total_tokens for r in results),
        total_latency_ms=sum(r.latency_ms for r in results),
        wall_clock_ms=wall_clock_ms,
        texts=[r.text for r in results],
        n_completed=len(results),
        n_failed=max(0, n_failed),
        parsed_outputs=parsed_outputs,
        n_parsed=n_parsed,
    )
