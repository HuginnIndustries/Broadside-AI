"""Gather — collect and normalize scatter results."""

from __future__ import annotations

from dataclasses import dataclass, field

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

    def summary(self) -> dict[str, object]:
        """Quick stats for logging or HITL display."""
        return {
            "completed": self.n_completed,
            "failed": self.n_failed,
            "total_tokens": self.total_tokens,
            "wall_clock_ms": round(self.wall_clock_ms, 1),
            "models_used": list({r.model for r in self.results}),
        }


def gather(
    results: list[AgentResult],
    wall_clock_ms: float = 0.0,
    n_requested: int | None = None,
) -> GatherResult:
    """Collect scatter outputs into a normalized structure.

    Args:
        results: Completed AgentResults from scatter.
        wall_clock_ms: Actual elapsed wall-clock time for the scatter.
        n_requested: How many branches were requested (to calculate failure count).
    """
    n_failed = (n_requested - len(results)) if n_requested else 0

    return GatherResult(
        results=results,
        total_tokens=sum(r.total_tokens for r in results),
        total_latency_ms=sum(r.latency_ms for r in results),
        wall_clock_ms=wall_clock_ms,
        texts=[r.text for r in results],
        n_completed=len(results),
        n_failed=max(0, n_failed),
    )
