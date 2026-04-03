"""Gather - collect and normalize scatter results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from broadside_ai.backends.base import AgentResult


@dataclass
class GatherResult:
    """Normalized collection of scatter outputs, ready for synthesis."""

    results: list[AgentResult]
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    wall_clock_ms: float = 0.0
    n_requested: int = 0
    texts: list[str] = field(default_factory=list)
    n_completed: int = 0
    n_failed: int = 0
    parsed_outputs: list[dict[str, Any] | None] = field(default_factory=list)
    n_parsed: int = 0

    def summary(self) -> dict[str, object]:
        """Quick stats for logging or machine output."""
        return {
            "n_requested": self.n_requested,
            "completed": self.n_completed,
            "failed": self.n_failed,
            "n_parsed": self.n_parsed,
            "total_tokens": self.total_tokens,
            "wall_clock_ms": round(self.wall_clock_ms, 1),
            "models_used": list({r.model for r in self.results}),
        }


def gather(
    results: list[AgentResult],
    wall_clock_ms: float = 0.0,
    n_requested: int | None = None,
    output_schema: dict[str, Any] | None = None,
) -> GatherResult:
    """Collect scatter outputs into a normalized structure."""
    requested = n_requested if n_requested is not None else len(results)
    n_failed = max(0, requested - len(results))

    parsed_outputs: list[dict[str, Any] | None] = []
    n_parsed = 0

    if output_schema is not None:
        from broadside_ai.parsing import try_parse_json

        for result in results:
            parsed = try_parse_json(result.text)
            result.parsed = parsed
            parsed_outputs.append(parsed)
            if parsed is not None:
                n_parsed += 1

    return GatherResult(
        results=results,
        total_tokens=sum(r.total_tokens for r in results),
        total_latency_ms=sum(r.latency_ms for r in results),
        wall_clock_ms=wall_clock_ms,
        n_requested=requested,
        texts=[r.text for r in results],
        n_completed=len(results),
        n_failed=n_failed,
        parsed_outputs=parsed_outputs,
        n_parsed=n_parsed,
    )
