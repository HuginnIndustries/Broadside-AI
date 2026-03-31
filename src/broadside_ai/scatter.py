"""Scatter — fan a single task out to N parallel agents."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from broadside_ai.backends import get_backend
from broadside_ai.backends.base import AgentResult
from broadside_ai.budget import BudgetExceeded, ScatterBudget
from broadside_ai.quality import EarlyStop, should_stop
from broadside_ai.task import Task

logger = logging.getLogger(__name__)


async def scatter(
    task: Task,
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    agent_kwargs: dict[str, Any] | None = None,
    budget: ScatterBudget | None = None,
    parallel: bool | None = None,
    early_stop: EarlyStop | None = None,
) -> list[AgentResult]:
    """Run a task across N agents, collect all results.

    Args:
        task: The work to scatter.
        n: Number of agents. Default 3 (sweet spot is 3-5,
           performance plateaus beyond 4 per DeepMind 2025).
        backend: Which LLM backend to use.
        backend_kwargs: Passed to backend constructor (base_url, model, etc.).
        agent_kwargs: Passed to each backend.complete() call (temperature, etc.).
        budget: Optional per-scatter cost limit. If total tokens exceed the
                budget mid-scatter, remaining branches are cancelled.
        parallel: Whether to run branches concurrently. Defaults to True for
                  cloud backends (Anthropic, OpenAI) and False for local
                  backends (Ollama) where concurrent requests can overwhelm
                  the machine.
        early_stop: Optional quality-based early termination. When set,
                    completed results are checked against quality signals
                    and remaining branches are cancelled if signals fire.

    Returns:
        List of AgentResult from all completed branches.

    Raises:
        BudgetExceeded: If budget is set and the scatter would exceed it.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    if n > 20:
        import warnings

        warnings.warn(
            f"Scattering to {n} agents. Performance typically plateaus at 3-5. "
            "Consider whether this many branches adds value.",
            stacklevel=2,
        )

    # Default to parallel — let hardware limits surface naturally
    if parallel is None:
        parallel = True

    llm = get_backend(backend, **(backend_kwargs or {}))
    prompt = task.render_prompt()
    kwargs = agent_kwargs or {}
    budget_tracker = budget or ScatterBudget()  # unbounded by default

    last_error: Exception | None = None

    async def _run_one(index: int) -> AgentResult | None:
        """Run a single scatter branch, respecting budget."""
        nonlocal last_error
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
            logger.debug("Scatter branch %d failed: %s", index, exc)
            last_error = exc
            return None

    if parallel and early_stop is not None:
        # Early termination path: collect results as they complete
        completed = await _scatter_with_early_stop(_run_one, n, early_stop)
    elif parallel:
        # Standard parallel: fire all at once, wait for all
        results = await asyncio.gather(*[_run_one(i) for i in range(n)])
        completed = [r for r in results if r is not None]
    else:
        # Sequential: run one at a time
        completed = []
        for i in range(n):
            result = await _run_one(i)
            if result is not None:
                completed.append(result)
                # Check early stop in sequential mode too
                if early_stop and should_stop(completed, early_stop):
                    logger.debug(
                        "Early stop after %d/%d branches (sequential)",
                        len(completed),
                        n,
                    )
                    break

    if not completed:
        hint = f"\n  Last error: {last_error}" if last_error else ""
        raise RuntimeError(
            f"All {n} agents failed. Check that '{backend}' is running "
            f"and the model is available.{hint}"
        )

    return completed


async def _scatter_with_early_stop(
    run_fn: Any,
    n: int,
    early_stop: EarlyStop,
) -> list[AgentResult]:
    """Run scatter branches with early termination on quality signals."""
    tasks = [asyncio.ensure_future(run_fn(i)) for i in range(n)]
    completed: list[AgentResult] = []

    for coro in asyncio.as_completed(tasks):
        result = await coro
        if result is not None:
            completed.append(result)
            if should_stop(completed, early_stop):
                # Cancel remaining tasks
                for t in tasks:
                    if not t.done():
                        t.cancel()
                logger.debug(
                    "Early stop after %d/%d branches",
                    len(completed),
                    n,
                )
                break

    # Await cancelled tasks to suppress warnings
    for t in tasks:
        if t.cancelled():
            try:
                await t
            except asyncio.CancelledError:
                pass

    return completed
