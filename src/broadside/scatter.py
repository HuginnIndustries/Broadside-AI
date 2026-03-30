"""Scatter — fan a single task out to N parallel agents."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from broadside.backends import get_backend
from broadside.backends.base import AgentResult
from broadside.budget import BudgetExceeded, ScatterBudget
from broadside.task import Task


async def scatter(
    task: Task,
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    agent_kwargs: dict[str, Any] | None = None,
    budget: ScatterBudget | None = None,
) -> list[AgentResult]:
    """Run a task across N agents in parallel, collect all results.

    Args:
        task: The work to scatter.
        n: Number of parallel agents. Default 3 (sweet spot is 3-5,
           performance plateaus beyond 4 per DeepMind 2025).
        backend: Which LLM backend to use.
        backend_kwargs: Passed to backend constructor (base_url, model, etc.).
        agent_kwargs: Passed to each backend.complete() call (temperature, etc.).
        budget: Optional per-scatter cost limit. If total tokens exceed the
                budget mid-scatter, remaining branches are cancelled.

    Returns:
        List of AgentResult from all completed branches.

    Raises:
        BudgetExceeded: If budget is set and the scatter would exceed it.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    if n > 20:
        # Not a hard limit, but a strong nudge. Research shows diminishing
        # returns past 4. If you need 20, you probably need a different pattern.
        import warnings

        warnings.warn(
            f"Scattering to {n} agents. Performance typically plateaus at 3-5. "
            "Consider whether this many branches adds value.",
            stacklevel=2,
        )

    llm = get_backend(backend, **(backend_kwargs or {}))
    prompt = task.render_prompt()
    kwargs = agent_kwargs or {}
    budget_tracker = budget or ScatterBudget()  # unbounded by default

    async def _run_one(index: int) -> AgentResult | None:
        """Run a single scatter branch, respecting budget."""
        if budget_tracker.exhausted:
            return None
        try:
            result = await llm.complete(prompt, **kwargs)
            budget_tracker.record(result.total_tokens)
            return result
        except BudgetExceeded:
            return None
        except Exception as exc:
            # Individual branch failures don't kill the scatter.
            # Log and continue — partial results are still useful.
            import warnings

            warnings.warn(
                f"Scatter branch {index} failed: {exc}",
                stacklevel=2,
            )
            return None

    results = await asyncio.gather(*[_run_one(i) for i in range(n)])
    completed = [r for r in results if r is not None]

    if not completed:
        raise RuntimeError(
            f"All {n} scatter branches failed. Check backend configuration "
            f"and that '{backend}' is running."
        )

    return completed
