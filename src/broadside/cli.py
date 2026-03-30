"""CLI entrypoint — `broadside run` from the terminal."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from broadside.budget import ScatterBudget
from broadside.gather import gather
from broadside.scatter import scatter
from broadside.synthesize import synthesize
from broadside.task import Task

console = Console()


@click.group()
@click.version_option(package_name="broadside")
def main() -> None:
    """Broadside — parallel LLM agent orchestration using scatter/gather."""
    pass


@main.command()
@click.argument("task_file", type=click.Path(exists=True), required=False)
@click.option("--prompt", "-p", help="Inline prompt (instead of a task file).")
@click.option("--n", "-n", default=3, help="Number of parallel agents (default: 3).")
@click.option("--backend", "-b", default="ollama", help="LLM backend (default: ollama).")
@click.option("--model", "-m", help="Model name (backend-specific).")
@click.option("--synthesis", "-s", default="llm", help="Synthesis strategy (default: llm).")
@click.option("--max-tokens", type=int, help="Per-scatter token budget.")
@click.option("--raw", is_flag=True, help="Show raw outputs instead of synthesis.")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON.")
def run(
    task_file: str | None,
    prompt: str | None,
    n: int,
    backend: str,
    model: str | None,
    synthesis: str,
    max_tokens: int | None,
    raw: bool,
    json_out: bool,
) -> None:
    """Run a scatter/gather cycle on a task."""
    if not task_file and not prompt:
        console.print("[red]Error:[/red] Provide a task file or --prompt.")
        sys.exit(1)

    # Build the task
    if task_file:
        task = _load_task_file(task_file)
    else:
        task = Task(prompt=prompt)  # type: ignore[arg-type]

    # Build backend kwargs
    bk: dict[str, Any] = {}
    if model:
        bk["model"] = model

    budget = ScatterBudget(max_tokens=max_tokens) if max_tokens else None

    # Run the scatter/gather/synthesize pipeline
    asyncio.run(_run_pipeline(task, n, backend, bk, synthesis, budget, raw, json_out))


async def _run_pipeline(
    task: Task,
    n: int,
    backend: str,
    backend_kwargs: dict[str, Any],
    strategy: str,
    budget: ScatterBudget | None,
    raw: bool,
    json_out: bool,
) -> None:
    """Execute the full pipeline with rich output."""
    import time

    # Scatter
    with console.status(f"[bold blue]Scattering to {n} agents...[/bold blue]"):
        t0 = time.perf_counter()
        results = await scatter(
            task=task,
            n=n,
            backend=backend,
            backend_kwargs=backend_kwargs,
            budget=budget,
        )
        wall_ms = (time.perf_counter() - t0) * 1000

    # Gather
    gathered = gather(results, wall_clock_ms=wall_ms, n_requested=n)

    if raw:
        _show_raw(gathered.texts, json_out)
        return

    # Synthesize
    with console.status("[bold blue]Synthesizing...[/bold blue]"):
        result = await synthesize(
            gathered=gathered,
            strategy=strategy,
            backend=backend,
            backend_kwargs=backend_kwargs,
        )

    if json_out:
        _show_json(result)
    else:
        _show_rich(result)


def _load_task_file(path: str) -> Task:
    """Load a task from a YAML or JSON file."""
    p = Path(path)
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    elif p.suffix == ".json":
        data = json.loads(text)
    else:
        # Treat as plain text prompt
        return Task(prompt=text.strip())
    return Task(**data)


def _show_raw(texts: list[str], json_out: bool) -> None:
    if json_out:
        console.print_json(json.dumps({"outputs": texts}))
    else:
        for i, text in enumerate(texts):
            console.print(Panel(text, title=f"Output {i + 1}"))


def _show_json(result: Any) -> None:
    from broadside.synthesize import Synthesis

    assert isinstance(result, Synthesis)
    console.print_json(
        json.dumps(
            {
                "synthesis": result.result,
                "strategy": result.strategy,
                "n_outputs": len(result.raw_outputs),
                "total_tokens": result.total_tokens(),
                "wall_clock_ms": round(result.gather.wall_clock_ms, 1),
            }
        )
    )


def _show_rich(result: Any) -> None:
    from broadside.synthesize import Synthesis

    assert isinstance(result, Synthesis)

    # Stats table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Agents completed", str(result.gather.n_completed))
    table.add_row("Total tokens", f"{result.total_tokens():,}")
    table.add_row("Wall clock", f"{result.gather.wall_clock_ms:.0f}ms")
    table.add_row("Strategy", result.strategy)
    console.print(table)
    console.print()

    # Synthesis
    console.print(Panel(result.result, title="[bold green]Synthesis[/bold green]"))
