"""High-level runner — scatter/gather/synthesize in one call.

This is the entry point most users will reach for. It wires together the
three phases and returns a Synthesis.
"""

from __future__ import annotations

import time
from typing import Any

from broadside_ai.budget import ScatterBudget
from broadside_ai.checkpoints import Checkpoint, CheckpointRejected
from broadside_ai.gather import gather
from broadside_ai.quality import EarlyStop
from broadside_ai.scatter import scatter
from broadside_ai.synthesize import Synthesis, synthesize
from broadside_ai.task import Task


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
    early_stop: EarlyStop | None = None,
    checkpoint: Checkpoint | None = None,
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
        checkpoint: Optional HITL checkpoint handler. When provided, the
                    pipeline pauses at each stage for human review.

    Returns:
        Synthesis with the final result, raw outputs, and cost data.

    Raises:
        CheckpointRejected: If a human rejects at any checkpoint.
    """
    budget = ScatterBudget(max_tokens=max_tokens) if max_tokens else None

    # Pre-scatter checkpoint
    if checkpoint and not await checkpoint.pre_scatter(task, n):
        raise CheckpointRejected("pre_scatter")

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
        early_stop=early_stop,
    )
    wall_ms = (time.perf_counter() - t0) * 1000

    # Gather
    gathered = gather(
        results,
        wall_clock_ms=wall_ms,
        n_requested=n,
        output_schema=task.output_schema,
    )

    # Post-gather checkpoint
    if checkpoint and not await checkpoint.post_gather(gathered):
        raise CheckpointRejected("post_gather")

    # Synthesize
    syn_backend = synthesis_backend or backend
    syn_bk = backend_kwargs if syn_backend == backend else None

    result = await synthesize(
        gathered=gathered,
        strategy=synthesis_strategy,
        backend=syn_backend,
        backend_kwargs=syn_bk,
        model=synthesis_model,
        output_schema=task.output_schema,
    )

    # Post-synthesis checkpoint
    if checkpoint and not await checkpoint.post_synthesis(result):
        raise CheckpointRejected("post_synthesis")

    return result


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
    early_stop: EarlyStop | None = None,
    checkpoint: Checkpoint | None = None,
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
            early_stop=early_stop,
            checkpoint=checkpoint,
        )
    )
