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
from rich.table import Table

from broadside.budget import ScatterBudget
from broadside.gather import gather
from broadside.scatter import scatter
from broadside.synthesize import synthesize
from broadside.task import Task

console = Console()

# Default output directory — created alongside the user's working directory
_OUTPUT_DIR = Path("broadside_output")


@click.group()
@click.version_option(package_name="broadside")
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
    help="Force parallel or sequential execution. Default: auto-detected by backend.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output directory. Default: broadside_output/",
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

    from broadside.scatter import _LOCAL_BACKENDS

    # Determine execution mode for display
    is_local = backend in _LOCAL_BACKENDS
    model_name = backend_kwargs.get("model", "")
    model_lower = str(model_name).lower()
    is_cloud_model = model_lower.endswith("-cloud") or ":cloud" in model_lower
    if parallel is None:
        run_parallel = (not is_local) or is_cloud_model
    else:
        run_parallel = parallel

    if run_parallel:
        mode_label = f"Scattering to {n} agents in parallel"
    else:
        mode_label = f"Running {n} agents sequentially"

    # Scatter
    if not run_parallel and not json_out:
        # Sequential mode: show per-agent progress
        t0 = time.perf_counter()
        results = []
        for i in range(n):
            with console.status(f"[bold blue]Agent {i + 1}/{n}...[/bold blue]"):
                try:
                    from broadside.backends import get_backend

                    llm = get_backend(backend, **backend_kwargs)
                    prompt = task.render_prompt()
                    result = await llm.complete(prompt)
                    results.append(result)
                except Exception as exc:
                    console.print(f"  [yellow]Agent {i + 1} failed: {exc}[/yellow]")
        wall_ms = (time.perf_counter() - t0) * 1000
    else:
        with console.status(f"[bold blue]{mode_label}...[/bold blue]"):
            t0 = time.perf_counter()
            results = await scatter(
                task=task,
                n=n,
                backend=backend,
                backend_kwargs=backend_kwargs,
                budget=budget,
                parallel=parallel,
            )
            wall_ms = (time.perf_counter() - t0) * 1000

    if not results:
        console.print(f"[red]All {n} agents failed.[/red] Check that {backend} is running.")
        sys.exit(1)

    # Gather
    gathered = gather(results, wall_clock_ms=wall_ms, n_requested=n)

    if raw:
        _show_raw(gathered.texts, json_out)
        if save:
            hint = _model_dir_name(gathered.results)
            _save_raw(gathered.texts, task, output_dir, model_hint=hint)
        return

    # Synthesize
    with console.status("[bold blue]Synthesizing...[/bold blue]"):
        result = await synthesize(
            gathered=gathered,
            strategy=strategy,
            backend=backend,
            backend_kwargs=backend_kwargs,
        )

    # Display
    if json_out:
        _show_json(result)
    else:
        _show_rich(result)

    # Save to files
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

    "Write a one-paragraph pitch for a CLI tool" → "write-a-one-paragraph-pitch-for-a-cli-tool"
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

    Example: broadside_output/gemma3-1b/dotfile-pitch_20260329_143022/
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{topic}_{stamp}" if topic else stamp
    run_dir = output_dir / model_name / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _save_results(result: Any, task: Task, output_dir: Path) -> None:
    """Save synthesis + raw outputs to nested directories.

    Structure:
        broadside_output/
            gemma3-1b/
                dotfile-pitch_20260329_143022/
                    result.json
                    synthesis.txt
                    agent_1.txt
                    agent_2.txt
                    agent_3.txt
    """
    from broadside.synthesize import Synthesis

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
