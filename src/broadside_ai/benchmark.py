"""Benchmark harness - measure what matters: latency, cost, diversity.

Three metrics, honestly reported:
1. Latency: wall-clock time for scatter (parallel) vs. sequential
2. Cost: actual token counts (scatter multiplies by about N+1 including synthesis)
3. Diversity: how different are the N outputs from each other (Jaccard distance)
"""

from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from broadside_ai.backends import get_backend
from broadside_ai.backends.base import AgentResult
from broadside_ai.gather import gather
from broadside_ai.scatter import scatter
from broadside_ai.task import Task


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""

    task_name: str
    n: int
    backend: str
    model: str = ""

    scatter_wall_ms: float = 0.0
    scatter_total_tokens: int = 0
    synthesis_tokens: int = 0

    sequential_wall_ms: float = 0.0
    sequential_total_tokens: int = 0

    diversity_score: float = 0.0

    scatter_outputs: list[str] = field(default_factory=list)
    sequential_output: str = ""

    @property
    def total_tokens(self) -> int:
        return self.scatter_total_tokens + self.synthesis_tokens

    @property
    def speedup(self) -> float:
        """Wall-clock speedup: sequential time / parallel scatter time."""
        if self.scatter_wall_ms == 0:
            return 0.0
        return self.sequential_wall_ms / self.scatter_wall_ms

    @property
    def token_multiplier(self) -> float:
        """Cost multiplier: total scatter+synthesis tokens / single sequential call tokens."""
        if self.sequential_total_tokens == 0:
            return 0.0
        # Compare against ONE sequential call, not N - that is the real
        # cost question: "how much more do I pay for scatter vs just asking once?"
        single_call_tokens = self.sequential_total_tokens / self.n if self.n else 0
        if single_call_tokens == 0:
            return 0.0
        return self.total_tokens / single_call_tokens

    @property
    def scatter_only_multiplier(self) -> float:
        """Token multiplier for scatter alone (no synthesis)."""
        single_call_tokens = self.sequential_total_tokens / self.n if self.n else 0
        if single_call_tokens == 0:
            return 0.0
        return self.scatter_total_tokens / single_call_tokens

    def summary(self) -> dict[str, Any]:
        return {
            "task": self.task_name,
            "n_agents": self.n,
            "backend": self.backend,
            "model": self.model,
            "parallel_wall_ms": round(self.scatter_wall_ms, 1),
            "sequential_wall_ms": round(self.sequential_wall_ms, 1),
            "speedup": round(self.speedup, 2),
            "scatter_tokens": self.scatter_total_tokens,
            "synthesis_tokens": self.synthesis_tokens,
            "total_tokens": self.total_tokens,
            "sequential_tokens": self.sequential_total_tokens,
            "token_multiplier": round(self.token_multiplier, 1),
            "scatter_only_multiplier": round(self.scatter_only_multiplier, 1),
            "diversity_score": round(self.diversity_score, 3),
        }


def _jaccard_distance(a: str, b: str) -> float:
    """Simple word-level Jaccard distance between two texts.

    Not a perfect diversity metric, but it is dependency-free and gives
    a reasonable signal. Embedding-based distance is a future upgrade.
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
    """Run a full benchmark: scatter/gather (parallel) vs. sequential baseline."""
    bk = backend_kwargs or {}
    ak = agent_kwargs or {}

    result = BenchmarkResult(task_name=task_name, n=n, backend=backend)

    t0 = time.perf_counter()
    scatter_results = await scatter(
        task=task,
        n=n,
        backend=backend,
        backend_kwargs=bk,
        agent_kwargs=ak,
        parallel=True,
    )
    scatter_wall = (time.perf_counter() - t0) * 1000

    gathered = gather(scatter_results, wall_clock_ms=scatter_wall, n_requested=n)

    if scatter_results:
        result.model = scatter_results[0].model

    result.scatter_wall_ms = scatter_wall
    result.scatter_total_tokens = gathered.total_tokens
    result.scatter_outputs = gathered.texts

    from broadside_ai.synthesize import synthesize

    synthesis = await synthesize(
        gathered,
        strategy="llm",
        backend=backend,
        backend_kwargs=bk,
    )
    result.synthesis_tokens = synthesis.synthesis_tokens

    # Run the same task N times, one at a time. This is what you would do
    # without Broadside-AI: prompt the model N times and pick the best.
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

    result.diversity_score = measure_diversity(result.scatter_outputs)

    return result


async def run_benchmark_suite(
    tasks: list[tuple[str, Task]],
    n: int = 3,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    output_dir: str | None = None,
    on_task_start: Any = None,
    on_task_done: Any = None,
) -> list[BenchmarkResult] | tuple[list[BenchmarkResult], Path]:
    """Run benchmarks across multiple tasks and optionally save results."""
    results = []
    total = len(tasks)
    for i, (name, task) in enumerate(tasks):
        if on_task_start:
            on_task_start(name, i, total)

        r = await benchmark_task(
            task=task,
            task_name=name,
            n=n,
            backend=backend,
            backend_kwargs=backend_kwargs,
        )
        results.append(r)

        if on_task_done:
            on_task_done(r, i, total)

    if output_dir:
        run_dir = _build_run_dir(output_dir, results, backend, backend_kwargs)
        _save_benchmark_results(results, run_dir, n, backend, backend_kwargs)
        return results, run_dir

    return results


def _build_run_dir(
    base_dir: str,
    results: list[BenchmarkResult],
    backend: str,
    backend_kwargs: dict[str, Any] | None,
) -> Path:
    """Create a descriptive run directory."""
    model = results[0].model if results else "unknown"
    model_safe = model.replace(":", "-").replace("/", "-")
    n = results[0].n if results else 3
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{model_safe}_{n}agents_{stamp}"
    run_dir = Path(base_dir) / dir_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _get_system_info() -> dict[str, Any]:
    """Collect hardware and OS info so local benchmark results have context."""
    info: dict[str, Any] = {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu": platform.processor() or "unknown",
        "cpu_count": os.cpu_count(),
    }
    # Try to get RAM - works on most platforms without extra dependencies.
    try:
        if platform.system() == "Windows":
            import ctypes

            windll = getattr(ctypes, "windll", None)
            if windll is None:
                return info
            kernel32 = windll.kernel32

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            info["ram_gb"] = round(stat.ullTotalPhys / (1024**3), 1)
        else:
            sysconf = getattr(os, "sysconf", None)
            if sysconf is None:
                return info
            mem_bytes = sysconf("SC_PAGE_SIZE") * sysconf("SC_PHYS_PAGES")
            info["ram_gb"] = round(mem_bytes / (1024**3), 1)
    except Exception:
        pass
    return info


def _save_benchmark_results(
    results: list[BenchmarkResult],
    run_dir: Path,
    n: int,
    backend: str,
    backend_kwargs: dict[str, Any] | None,
) -> None:
    """Save benchmark results as JSON and a human-readable markdown report."""
    model = results[0].model if results else "unknown"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    system_info = _get_system_info()

    payload = {
        "metadata": {
            "timestamp": timestamp,
            "backend": backend,
            "model": model,
            "n_agents": n,
            "backend_kwargs": backend_kwargs or {},
            "system": system_info,
        },
        "results": [r.summary() for r in results],
    }
    (run_dir / "results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    for r in results:
        task_dir = run_dir / r.task_name
        task_dir.mkdir(exist_ok=True)

        for i, text in enumerate(r.scatter_outputs):
            (task_dir / f"agent_{i + 1}.txt").write_text(text, encoding="utf-8")

        if r.sequential_output:
            (task_dir / "sequential_baseline.txt").write_text(
                r.sequential_output, encoding="utf-8"
            )

        (task_dir / "summary.json").write_text(
            json.dumps(r.summary(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    lines = [
        "# Benchmark Results",
        "",
        f"**Model:** {model}  ",
        f"**Backend:** {backend}  ",
        f"**Agents per scatter:** {n}  ",
        f"**Date:** {timestamp}  ",
        f"**System:** {system_info.get('os', 'unknown')}, "
        f"{system_info.get('cpu', 'unknown')}, "
        f"{system_info.get('cpu_count', '?')} cores, "
        f"{system_info.get('ram_gb', '?')} GB RAM  ",
        "",
        "## Results",
        "",
        (
            "| Task | Parallel | Sequential | Speedup | Tokens (scatter+synth) "
            "| Cost vs 1 call | Diversity |"
        ),
        "|------|----------|------------|---------|----------------------|----------------|-----------|",
    ]

    for r in results:
        lines.append(
            f"| {r.task_name} "
            f"| {r.scatter_wall_ms / 1000:.1f}s "
            f"| {r.sequential_wall_ms / 1000:.1f}s "
            f"| {r.speedup:.2f}x "
            f"| {r.scatter_total_tokens}+{r.synthesis_tokens}={r.total_tokens} "
            f"| {r.token_multiplier:.1f}x "
            f"| {r.diversity_score:.3f} |"
        )

    avg_speedup = sum(r.speedup for r in results) / len(results) if results else 0
    avg_token_mult = sum(r.token_multiplier for r in results) / len(results) if results else 0
    avg_diversity = sum(r.diversity_score for r in results) / len(results) if results else 0
    lines.append(
        f"| **Average** "
        f"| | "
        f"| **{avg_speedup:.2f}x** "
        f"| "
        f"| **{avg_token_mult:.1f}x** "
        f"| **{avg_diversity:.3f}** |"
    )

    lines.extend(
        [
            "",
            "## How to read this",
            "",
            f"**Speedup** = sequential wall-clock / parallel wall-clock. "
            f"Values above 1.0 mean parallel is faster. With {n} agents on a cloud "
            f"backend, theoretical max is {n:.1f}x.",
            "",
            f"**Cost vs 1 call** = total tokens (scatter + synthesis) / tokens for a "
            f"single LLM call. This is the real cost question: how much more do you "
            f"pay for scatter/gather vs just prompting once? Scatter alone costs about {n}x; "
            f"the LLM synthesis strategy adds another about 1x on top.",
            "",
            "**Diversity** = average pairwise Jaccard distance (word-level) across "
            "scatter outputs. 0.0 = identical, 1.0 = completely different. Higher "
            "diversity means the scatter is surfacing genuinely different perspectives.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "pip install broadside-ai",
            "python benchmarks/suite.py",
            "```",
            "",
            "Results are written to `benchmarks/results/`.",
        ]
    )

    (run_dir / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
