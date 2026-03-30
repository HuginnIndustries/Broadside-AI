"""High-level runner — scatter/gather/synthesize in one call.

This is the entry point most users will reach for. It wires together the
three phases and returns a Synthesis.
"""

from __future__ import annotations

import time
from typing import Any

from broadside.budget import ScatterBudget
from broadside.gather import gather
from broadside.scatter import scatter
from broadside.synthesize import Synthesis, synthesize
from broadside.task import Task


async def run(
    task: Task,
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    agent_kwargs: dict[str, Any] | None = None,
    synthesis_strategy: str = "llm",
    synthesis_backend: str | None = None,
    synthesis_model: str | None = None,
    max_tokens: int | None = None,
    parallel: bool | None = None,
) -> Synthesis:
    """Run a full scatter/gather/synthesize cycle.

    This is the simple path. For more control, call scatter(), gather(),
    and synthesize() individually.

    Args:
        task: What to scatter.
        n: Number of parallel agents (default 3, sweet spot 3-5).
        backend: LLM backend for scatter phase.
        backend_kwargs: Passed to backend constructor.
        agent_kwargs: Passed to each agent call (temperature, etc.).
        synthesis_strategy: How to combine results. Default "llm".
        synthesis_backend: Backend for synthesis (defaults to same as scatter).
        synthesis_model: Model override for synthesis step.
        max_tokens: Per-scatter token budget. None = unbounded.
        parallel: Run branches concurrently. Defaults to True for cloud
                  backends, False for local (Ollama) to avoid overloading.

    Returns:
        Synthesis with the final result, raw outputs, and cost data.
    """
    budget = ScatterBudget(max_tokens=max_tokens) if max_tokens else None

    # Scatter
    t0 = time.perf_counter()
    results = await scatter(
        task=task,
        n=n,
        backend=backend,
        backend_kwargs=backend_kwargs,
        agent_kwargs=agent_kwargs,
        budget=budget,
        parallel=parallel,
    )
    wall_ms = (time.perf_counter() - t0) * 1000

    # Gather
    gathered = gather(results, wall_clock_ms=wall_ms, n_requested=n)

    # Synthesize
    syn_backend = synthesis_backend or backend
    syn_bk = backend_kwargs if syn_backend == backend else None

    return await synthesize(
        gathered=gathered,
        strategy=synthesis_strategy,
        backend=syn_backend,
        backend_kwargs=syn_bk,
        model=synthesis_model,
    )


def run_sync(
    task: Task,
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    agent_kwargs: dict[str, Any] | None = None,
    synthesis_strategy: str = "llm",
    synthesis_backend: str | None = None,
    synthesis_model: str | None = None,
    max_tokens: int | None = None,
    parallel: bool | None = None,
) -> Synthesis:
    """Synchronous version of run() — no asyncio knowledge needed.

    Same arguments as run(). Use this in scripts, notebooks, and anywhere
    you don't want to think about async/await.
    """
    import asyncio

    return asyncio.run(
        run(
            task=task,
            n=n,
            backend=backend,
            backend_kwargs=backend_kwargs,
            agent_kwargs=agent_kwargs,
            synthesis_strategy=synthesis_strategy,
            synthesis_backend=synthesis_backend,
            synthesis_model=synthesis_model,
            max_tokens=max_tokens,
            parallel=parallel,
        )
    )
