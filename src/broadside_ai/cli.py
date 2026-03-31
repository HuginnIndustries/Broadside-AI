"""CLI entrypoint — `broadside run` from the terminal."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from broadside_ai.budget import ScatterBudget
from broadside_ai.gather import gather
from broadside_ai.scatter import scatter
from broadside_ai.synthesize import synthesize
from broadside_ai.task import Task

console = Console()


def _truncate_prompt(prompt: str, max_len: int = 60) -> str:
    """Shorten a prompt for display, preserving the start."""
    if len(prompt) <= max_len:
        return prompt
    return prompt[: max_len - 1].rstrip() + "\u2026"


# Default output directory — created alongside the user's working directory
_OUTPUT_DIR = Path("broadside_ai_output")


@click.group()
@click.version_option(package_name="broadside-ai")
def main() -> None:
    """Broadside — parallel LLM agent orchestration using scatter/gather."""
    pass


@main.command()
@click.argument("task_file", type=click.Path(exists=True), required=False)
@click.option("--prompt", "-p", help="Inline prompt (instead of a task file).")
@click.option("--n", "-n", default=3, help="Number of agents (default: 3).")
@click.option("--backend", "-b", default="ollama", help="LLM backend (default: ollama).")
@click.option("--model", "-m", help="Model name (backend-specific).")
@click.option("--synthesis", "-s", default="llm", help="Synthesis strategy (default: llm).")
@click.option("--max-tokens", type=int, help="Per-scatter token budget.")
@click.option(
    "--parallel/--sequential",
    default=None,
    help="Force parallel or sequential execution. Default: parallel.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output directory. Default: broadside_ai_output/",
)
@click.option("--no-save", is_flag=True, help="Don't save results to files.")
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
    parallel: bool | None,
    output: str | None,
    no_save: bool,
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
    output_dir = Path(output) if output else _OUTPUT_DIR
    save = not no_save

    # Run the scatter/gather/synthesize pipeline
    try:
        asyncio.run(
            _run_pipeline(
                task,
                n,
                backend,
                bk,
                synthesis,
                budget,
                parallel,
                output_dir,
                save,
                raw,
                json_out,
            )
        )
    except RuntimeError as exc:
        console.print(f"\n[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


async def _run_pipeline(
    task: Task,
    n: int,
    backend: str,
    backend_kwargs: dict[str, Any],
    strategy: str,
    budget: ScatterBudget | None,
    parallel: bool | None,
    output_dir: Path,
    save: bool,
    raw: bool,
    json_out: bool,
) -> None:
    """Execute the full pipeline with rich output."""
    import time

    run_parallel = parallel if parallel is not None else True
    mode = "parallel" if run_parallel else "sequential"

    # Resolve model display name
    model_display = backend_kwargs.get("model", "")
    if not model_display:
        if backend == "ollama":
            from broadside_ai.backends.ollama import _DEFAULT_MODEL

            model_display = f"{_DEFAULT_MODEL} (default)"
        elif backend == "anthropic":
            model_display = "claude-sonnet-4-20250514 (default)"
        elif backend == "openai":
            model_display = "gpt-4o-mini (default)"
        else:
            model_display = "(backend default)"

    # JSON mode skips all the rich display
    if json_out:
        return await _run_pipeline_quiet(
            task,
            n,
            backend,
            backend_kwargs,
            strategy,
            budget,
            run_parallel,
            output_dir,
            save,
            raw,
        )

    # --- Header panel ---
    console.print()
    console.print(
        Panel(
            f"[bold]Prompt:[/bold]  {_truncate_prompt(task.prompt)}\n"
            f"[bold]Model:[/bold]   {model_display}\n"
            f"[bold]Backend:[/bold] {backend}\n"
            f"[bold]Agents:[/bold]  {n}\n"
            f"[bold]Mode:[/bold]    {mode}\n"
            f"[bold]Synth:[/bold]   {strategy}",
            title="[bold cyan]Broadside[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    # --- Scatter phase with live progress ---
    scatter_start = time.perf_counter()

    if not run_parallel:
        # Sequential: show per-agent progress bar
        results = []
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        )
        with progress:
            ptask = progress.add_task("Scattering agents", total=n)
            from broadside_ai.backends import get_backend

            llm = get_backend(backend, **backend_kwargs)
            prompt = task.render_prompt()
            for i in range(n):
                progress.update(ptask, description=f"Agent {i + 1}/{n} thinking")
                try:
                    result = await llm.complete(prompt)
                    results.append(result)
                except Exception as exc:
                    console.print(f"  [yellow]Agent {i + 1} failed: {exc}[/yellow]")
                progress.update(ptask, advance=1)
    else:
        # Parallel: spinner with elapsed time
        progress = Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]Scattering to {n} agents in parallel[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        )
        with progress:
            ptask = progress.add_task("scatter", total=None)
            results = await scatter(
                task=task,
                n=n,
                backend=backend,
                backend_kwargs=backend_kwargs,
                budget=budget,
                parallel=True,
            )

    scatter_wall = (time.perf_counter() - scatter_start) * 1000

    if not results:
        console.print(
            f"\n[red]All {n} agents failed.[/red] Check that {backend} is running "
            f"and the model is available."
        )
        sys.exit(1)

    # Quick scatter stats
    scatter_tokens = sum(r.total_tokens for r in results)
    n_ok = len(results)
    console.print(
        f"  [green]\u2713[/green] {n_ok}/{n} agents returned "
        f"[dim]({scatter_tokens:,} tokens, {scatter_wall / 1000:.1f}s)[/dim]"
    )

    # Gather
    gathered = gather(
        results,
        wall_clock_ms=scatter_wall,
        n_requested=n,
        output_schema=task.output_schema,
    )

    if raw:
        _show_raw(gathered.texts, False)
        if save:
            model_hint = _model_dir_name(gathered.results)
            _save_raw(gathered.texts, task, output_dir, model_hint=model_hint)
        return

    # --- Synthesis phase ---
    synth_start = time.perf_counter()
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Synthesizing perspectives[/bold blue]"),
        TimeElapsedColumn(),
        console=console,
    )
    with progress:
        ptask = progress.add_task("synthesize", total=None)
        result = await synthesize(
            gathered=gathered,
            strategy=strategy,
            backend=backend,
            backend_kwargs=backend_kwargs,
            output_schema=task.output_schema,
        )
    synth_wall = (time.perf_counter() - synth_start) * 1000
    total_wall = scatter_wall + synth_wall

    console.print(
        f"  [green]\u2713[/green] Synthesis complete "
        f"[dim]({result.synthesis_tokens:,} tokens, {synth_wall / 1000:.1f}s)[/dim]"
    )
    console.print()

    # --- Results ---
    _show_rich(result, total_wall)

    if save:
        _save_results(result, task, output_dir)


async def _run_pipeline_quiet(
    task: Task,
    n: int,
    backend: str,
    backend_kwargs: dict[str, Any],
    strategy: str,
    budget: ScatterBudget | None,
    run_parallel: bool,
    output_dir: Path,
    save: bool,
    raw: bool,
) -> None:
    """JSON output mode — no rich display, just data."""
    import time

    t0 = time.perf_counter()
    results = await scatter(
        task=task,
        n=n,
        backend=backend,
        backend_kwargs=backend_kwargs,
        budget=budget,
        parallel=run_parallel,
    )
    wall_ms = (time.perf_counter() - t0) * 1000

    if not results:
        console.print_json('{"error": "all agents failed"}')
        sys.exit(1)

    gathered = gather(
        results,
        wall_clock_ms=wall_ms,
        n_requested=n,
        output_schema=task.output_schema,
    )

    if raw:
        _show_raw(gathered.texts, True)
        if save:
            model_hint = _model_dir_name(gathered.results)
            _save_raw(gathered.texts, task, output_dir, model_hint=model_hint)
        return

    result = await synthesize(
        gathered=gathered,
        strategy=strategy,
        backend=backend,
        backend_kwargs=backend_kwargs,
        output_schema=task.output_schema,
    )
    _show_json(result)
    if save:
        _save_results(result, task, output_dir)


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

    # Strip metadata fields that aren't part of the Task model
    task_data = {k: v for k, v in data.items() if k != "meta"}
    return Task(**task_data)


def _slugify(text: str, max_len: int = 40) -> str:
    """Turn a prompt into a short filesystem-safe slug.

    "Write a battle plan for a naval ambush" → "write-a-battle-plan-for-a-naval-ambush"
    """
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)  # drop punctuation
    slug = re.sub(r"[\s_]+", "-", slug)  # spaces/underscores → hyphens
    slug = re.sub(r"-+", "-", slug).strip("-")  # collapse runs
    return slug[:max_len].rstrip("-")


def _model_dir_name(results: list[Any]) -> str:
    """Extract model name from results and make it directory-safe.

    "nemotron-3-super:cloud" → "nemotron-3-super-cloud"
    "gpt-oss:120b-cloud" → "gpt-oss-120b-cloud"
    """
    if results:
        model = getattr(results[0], "model", None) or "unknown"
    else:
        model = "unknown"
    return model.replace(":", "-").replace("/", "-")


def _build_run_dir(output_dir: Path, model_name: str, topic: str) -> Path:
    """Build the nested output path: output_dir / model / topic_timestamp.

    Example: broadside_ai_output/gemma3-1b/naval-ambush_20260329_143022/
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{topic}_{stamp}" if topic else stamp
    run_dir = output_dir / model_name / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _save_results(result: Any, task: Task, output_dir: Path) -> None:
    """Save synthesis + raw outputs to nested directories.

    Structure:
        broadside_ai_output/
            gemma3-1b/
                naval-ambush_20260329_143022/
                    result.json
                    synthesis.txt
                    agent_1.txt
                    agent_2.txt
                    agent_3.txt
    """
    from broadside_ai.synthesize import Synthesis

    assert isinstance(result, Synthesis)

    model_dir = _model_dir_name(result.gather.results)
    topic = _slugify(task.prompt)
    run_dir = _build_run_dir(output_dir, model_dir, topic)

    # Full result as JSON (machine-readable)
    # Explicit UTF-8 so Windows doesn't choke on emoji in LLM output
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "prompt": task.prompt,
                "model": model_dir,
                "synthesis": result.result,
                "strategy": result.strategy,
                "raw_outputs": result.raw_outputs,
                "stats": {
                    "n_completed": result.gather.n_completed,
                    "n_failed": result.gather.n_failed,
                    "total_tokens": result.total_tokens(),
                    "scatter_tokens": result.gather.total_tokens,
                    "synthesis_tokens": result.synthesis_tokens,
                    "wall_clock_ms": round(result.gather.wall_clock_ms, 1),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Synthesis as plain text (easy to open and copy)
    (run_dir / "synthesis.txt").write_text(result.result, encoding="utf-8")

    # Each raw agent output
    for i, text in enumerate(result.raw_outputs):
        (run_dir / f"agent_{i + 1}.txt").write_text(text, encoding="utf-8")

    # Relative path for cleaner display
    try:
        display_path = run_dir.relative_to(Path.cwd())
    except ValueError:
        display_path = run_dir
    console.print(f"\n[dim]Saved to {display_path}/[/dim]")


def _save_raw(texts: list[str], task: Task, output_dir: Path, model_hint: str = "unknown") -> None:
    """Save raw outputs (no synthesis) to nested directories."""
    model_dir = model_hint.replace(":", "-").replace("/", "-")
    topic = _slugify(task.prompt)
    run_dir = _build_run_dir(output_dir, model_dir, topic)

    for i, text in enumerate(texts):
        (run_dir / f"agent_{i + 1}.txt").write_text(text, encoding="utf-8")

    (run_dir / "raw.json").write_text(
        json.dumps(
            {"prompt": task.prompt, "model": model_dir, "outputs": texts},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        display_path = run_dir.relative_to(Path.cwd())
    except ValueError:
        display_path = run_dir
    console.print(f"\n[dim]Saved to {display_path}/[/dim]")


def _show_raw(texts: list[str], json_out: bool) -> None:
    if json_out:
        console.print_json(json.dumps({"outputs": texts}))
    else:
        for i, text in enumerate(texts):
            console.print(Panel(text, title=f"Output {i + 1}"))


def _show_json(result: Any) -> None:
    from broadside_ai.synthesize import Synthesis

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


def _show_rich(result: Any, total_wall_ms: float | None = None) -> None:
    from broadside_ai.synthesize import Synthesis

    assert isinstance(result, Synthesis)

    # Synthesis output
    console.print(
        Panel(
            result.result,
            title="[bold green]Synthesis[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    # Stats bar
    wall = total_wall_ms or result.gather.wall_clock_ms
    stats_parts = [
        f"[bold]{result.gather.n_completed}[/bold] agents",
        f"[bold]{result.total_tokens():,}[/bold] tokens",
        f"[bold]{wall / 1000:.1f}s[/bold] total",
        f"strategy: [bold]{result.strategy}[/bold]",
    ]
    sep = " \u2502 "
    console.print(f"\n[dim]{sep.join(stats_parts)}[/dim]")
