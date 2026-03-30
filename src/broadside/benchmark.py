"""Benchmark harness — measure what matters: latency, cost, diversity.

Three metrics, honestly reported:
1. Latency: wall-clock time for scatter vs. N sequential calls
2. Cost: actual token counts (scatter multiplies by ~N+1 including synthesis)
3. Diversity: how different are the N outputs from each other

Quality vs. single-agent baseline is a Phase 2 goal — it requires synthesis
strategies mature enough for a fair comparison.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from broadside.backends import get_backend
from broadside.backends.base import AgentResult
from broadside.gather import gather
from broadside.run import run
from broadside.synthesize import Synthesis
from broadside.task import Task


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    task_name: str
    n: int
    backend: str

    # Scatter/gather metrics
    scatter_wall_ms: float = 0.0
    scatter_total_tokens: int = 0
    synthesis_tokens: int = 0

    # Sequential baseline metrics
    sequential_wall_ms: float = 0.0
    sequential_total_tokens: int = 0

    # Diversity (0.0 = identical outputs, 1.0 = completely different)
    diversity_score: float = 0.0

    # Raw data for transparency
    scatter_outputs: list[str] = field(default_factory=list)
    sequential_output: str = ""

    @property
    def total_tokens(self) -> int:
        return self.scatter_total_tokens + self.synthesis_tokens

    @property
    def speedup(self) -> float:
        """Wall-clock speedup: sequential time / scatter time."""
        if self.scatter_wall_ms == 0:
            return 0.0
        return self.sequential_wall_ms / self.scatter_wall_ms

    @property
    def token_multiplier(self) -> float:
        """Cost multiplier: scatter tokens / sequential tokens."""
        if self.sequential_total_tokens == 0:
            return 0.0
        return self.total_tokens / self.sequential_total_tokens

    def summary(self) -> dict[str, Any]:
        return {
            "task": self.task_name,
            "n_agents": self.n,
            "backend": self.backend,
            "scatter_wall_ms": round(self.scatter_wall_ms, 1),
            "sequential_wall_ms": round(self.sequential_wall_ms, 1),
            "speedup": f"{self.speedup:.2f}x",
            "scatter_tokens": self.scatter_total_tokens,
            "synthesis_tokens": self.synthesis_tokens,
            "total_tokens": self.total_tokens,
            "sequential_tokens": self.sequential_total_tokens,
            "token_multiplier": f"{self.token_multiplier:.1f}x",
            "diversity_score": round(self.diversity_score, 3),
        }


def _jaccard_distance(a: str, b: str) -> float:
    """Simple word-level Jaccard distance between two texts.

    Not a perfect diversity metric, but it's dependency-free and gives
    a reasonable signal. Embedding-based distance is a Phase 2 upgrade.
    """
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a and not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return 1.0 - (len(intersection) / len(union))


def measure_diversity(texts: list[str]) -> float:
    """Average pairwise Jaccard distance across all output pairs.

    Returns 0.0 for identical outputs, approaches 1.0 for completely
    different outputs. With N=3, this is 3 comparisons. Fast enough.
    """
    if len(texts) < 2:
        return 0.0
    distances = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            distances.append(_jaccard_distance(texts[i], texts[j]))
    return sum(distances) / len(distances) if distances else 0.0


async def benchmark_task(
    task: Task,
    task_name: str = "unnamed",
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    agent_kwargs: dict[str, Any] | None = None,
) -> BenchmarkResult:
    """Run a full benchmark: scatter/gather vs. sequential baseline.

    This runs the same task twice:
    1. Scatter to N agents in parallel, gather, synthesize
    2. Run the same task N times sequentially (the baseline)

    Both use the same backend and model so the comparison is fair.
    """
    bk = backend_kwargs or {}
    ak = agent_kwargs or {}

    result = BenchmarkResult(task_name=task_name, n=n, backend=backend)

    # --- Scatter/gather run ---
    synthesis = await run(
        task=task,
        n=n,
        backend=backend,
        backend_kwargs=bk,
        agent_kwargs=ak,
    )
    result.scatter_wall_ms = synthesis.gather.wall_clock_ms
    result.scatter_total_tokens = synthesis.gather.total_tokens
    result.synthesis_tokens = synthesis.synthesis_tokens
    result.scatter_outputs = synthesis.raw_outputs

    # --- Sequential baseline ---
    llm = get_backend(backend, **bk)
    prompt = task.render_prompt()
    t0 = time.perf_counter()
    seq_results: list[AgentResult] = []
    for _ in range(n):
        r = await llm.complete(prompt, **ak)
        seq_results.append(r)
    result.sequential_wall_ms = (time.perf_counter() - t0) * 1000
    result.sequential_total_tokens = sum(r.total_tokens for r in seq_results)
    result.sequential_output = seq_results[0].text if seq_results else ""

    # --- Diversity ---
    result.diversity_score = measure_diversity(result.scatter_outputs)

    return result


async def run_benchmark_suite(
    tasks: list[tuple[str, Task]],
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    output_dir: str | None = None,
) -> list[BenchmarkResult]:
    """Run benchmarks across multiple tasks and optionally save results.

    Args:
        tasks: List of (name, Task) tuples.
        n: Agents per scatter.
        backend: LLM backend.
        backend_kwargs: Backend config.
        output_dir: If set, write JSON results to this directory.
    """
    results = []
    for name, task in tasks:
        r = await benchmark_task(
            task=task,
            task_name=name,
            n=n,
            backend=backend,
            backend_kwargs=backend_kwargs,
        )
        results.append(r)

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        summaries = [r.summary() for r in results]
        (out / "results.json").write_text(json.dumps(summaries, indent=2))

    return results
