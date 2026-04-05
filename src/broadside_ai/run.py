"""High-level runner - scatter/gather/synthesize in one call."""

from __future__ import annotations

import threading
import time
from typing import Any

from broadside_ai.budget import ScatterBudget
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
) -> Synthesis:
    """Run a full scatter/gather/synthesize cycle."""
    budget = ScatterBudget(max_tokens=max_tokens) if max_tokens else None
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

    gathered = gather(
        results,
        wall_clock_ms=wall_ms,
        n_requested=n,
        output_schema=task.output_schema,
    )

    syn_backend = synthesis_backend or backend
    syn_bk = backend_kwargs if syn_backend == backend else None
    return await synthesize(
        gathered=gathered,
        strategy=synthesis_strategy,
        backend=syn_backend,
        backend_kwargs=syn_bk,
        model=synthesis_model,
        output_schema=task.output_schema,
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
    early_stop: EarlyStop | None = None,
) -> Synthesis:
    """Synchronous version of run() for scripts and notebooks."""
    import asyncio

    async def _run_async() -> Synthesis:
        return await run(
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
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run_async())

    result: Synthesis | None = None
    error: BaseException | None = None

    def _runner() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(_run_async())
        except BaseException as exc:  # pragma: no cover - exercised via re-raise below
            error = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if error is not None:
        raise error

    assert result is not None
    return result
