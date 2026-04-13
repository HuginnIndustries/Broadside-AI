"""Scatter - fan a single task out to N agents."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from broadside_ai.backends import get_backend
from broadside_ai.backends.base import AgentResult
from broadside_ai.budget import BudgetExceeded, ScatterBudget
from broadside_ai.execution import resolve_parallel_mode
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
    """Run a task across N agents and collect completed results.

    If a ``budget`` is provided, it is mutated in-place: each branch's token
    usage is recorded against it. Create a fresh ``ScatterBudget`` for each
    call if you need independent budget tracking across runs.
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

    run_parallel = resolve_parallel_mode(backend, backend_kwargs, explicit=parallel)
    llm = get_backend(backend, **(backend_kwargs or {}))
    prompt = task.render_prompt()
    kwargs = agent_kwargs or {}
    budget_tracker = budget or ScatterBudget()
    last_error: Exception | None = None

    async def _run_one(index: int) -> AgentResult | None:
        nonlocal last_error
        if budget_tracker.exhausted:
            return None
        try:
            result = await llm.complete(prompt, **kwargs)
            try:
                budget_tracker.record(result.total_tokens)
            except BudgetExceeded:
                logger.debug(
                    "Scatter budget exhausted after branch %d; keeping the completed result",
                    index,
                )
            return result
        except Exception as exc:
            logger.debug("Scatter branch %d failed: %s", index, exc)
            last_error = exc
            return None

    if run_parallel and early_stop is not None:
        completed = await _scatter_with_early_stop(_run_one, n, early_stop)
    elif run_parallel:
        results = await asyncio.gather(*[_run_one(i) for i in range(n)])
        completed = [result for result in results if result is not None]
    else:
        completed = []
        for i in range(n):
            result = await _run_one(i)
            if result is not None:
                completed.append(result)
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
                for task in tasks:
                    if not task.done():
                        task.cancel()
                logger.debug("Early stop after %d/%d branches", len(completed), n)
                break

    for task in tasks:
        if task.cancelled():
            try:
                await task
            except asyncio.CancelledError:
                pass

    return completed
