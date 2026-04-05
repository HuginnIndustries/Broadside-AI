"""CLI entrypoint for Broadside-AI."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from broadside_ai.budget import ScatterBudget
from broadside_ai.execution import resolve_parallel_mode
from broadside_ai.gather import GatherResult, gather
from broadside_ai.quality import EarlyStop
from broadside_ai.scatter import scatter
from broadside_ai.synthesize import Synthesis, synthesize
from broadside_ai.task import Task
from broadside_ai.task_validator import validate_task_file

console = Console()
_OUTPUT_DIR = Path("broadside_ai_output")
_JSON_OUTPUT_SCHEMA_VERSION = 1


@dataclass
class RunArtifacts:
    """Normalized output of one CLI run."""

    task: Task
    backend: str
    model: str
    mode: str
    requested_strategy: str
    gather: GatherResult
    synthesis: Synthesis | None
    raw: bool
    saved_to: Path | None

    def to_payload(self) -> dict[str, Any]:
        actual_strategy = self.synthesis.strategy if self.synthesis else None
        result_text = self.synthesis.result if self.synthesis else None
        parsed_result = self.synthesis.parsed_result if self.synthesis else None
        raw_outputs = self.synthesis.raw_outputs if self.synthesis else self.gather.texts
        return {
            "schema_version": _JSON_OUTPUT_SCHEMA_VERSION,
            "status": "ok",
            "prompt": self.task.prompt,
            "backend": self.backend,
            "model": self.model,
            "mode": self.mode,
            "requested_strategy": self.requested_strategy,
            "strategy": actual_strategy,
            "result": result_text,
            "parsed_result": parsed_result,
            "raw_outputs": raw_outputs,
            "gather": {
                "n_requested": self.gather.n_requested,
                "n_completed": self.gather.n_completed,
                "n_failed": self.gather.n_failed,
                "n_parsed": self.gather.n_parsed,
                "total_tokens": self.gather.total_tokens,
                "wall_clock_ms": round(self.gather.wall_clock_ms, 1),
            },
            "saved_to": str(self.saved_to) if self.saved_to is not None else None,
        }


@click.group()
@click.version_option(package_name="broadside-ai")
def main() -> None:
    """Broadside-AI - parallel LLM aggregation for CLIs, scripts, and CI."""


@main.command()
@click.argument("task_file", type=click.Path(exists=True), required=False)
@click.option("--prompt", "-p", help="Inline prompt (instead of a task file).")
@click.option("--n", "-n", default=3, show_default=True, help="Number of agents.")
@click.option("--backend", "-b", default="ollama", show_default=True, help="LLM backend.")
@click.option("--model", "-m", help="Model name (backend-specific).")
@click.option("--synthesis", "-s", default="llm", show_default=True, help="Synthesis strategy.")
@click.option("--max-tokens", type=int, help="Per-scatter token budget.")
@click.option(
    "--parallel/--sequential",
    default=None,
    help=(
        "Force parallel or sequential execution. Default: cloud backends "
        "parallel, local Ollama sequential."
    ),
)
@click.option("--output", "-o", type=click.Path(), help="Directory to save run artifacts.")
@click.option("--save", is_flag=True, help="Save run artifacts to the default output directory.")
@click.option("--raw", is_flag=True, help="Emit raw scatter outputs instead of a synthesis.")
@click.option(
    "--context-file",
    "context_files",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Append one or more local files as grounding context for the task.",
)
@click.option("--json-output", "json_out", is_flag=True, help="Emit a stable JSON payload.")
@click.option("--early-stop", type=int, help="Stop after this many results arrive.")
@click.option("--agreement", type=float, help="Stop when this fraction of results agree.")
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
    save: bool,
    raw: bool,
    context_files: tuple[str, ...],
    json_out: bool,
    early_stop: int | None,
    agreement: float | None,
) -> None:
    """Run a scatter/gather cycle on a task."""
    if not task_file and not prompt:
        raise click.UsageError("Provide a task file or --prompt.")

    task = _load_task_file(task_file) if task_file else Task(prompt=prompt or "")
    if context_files:
        task = _merge_task_context(task, _load_context_files(context_files))
    backend_kwargs: dict[str, Any] = {}
    if model:
        backend_kwargs["model"] = model

    budget = ScatterBudget(max_tokens=max_tokens) if max_tokens else None
    early_stop_config = (
        EarlyStop(min_complete=early_stop, agreement_threshold=agreement)
        if early_stop is not None or agreement is not None
        else None
    )
    run_parallel = resolve_parallel_mode(backend, backend_kwargs, explicit=parallel)
    output_dir = Path(output) if output else _OUTPUT_DIR
    save_enabled = save or output is not None
    rich_output = sys.stdout.isatty() and not json_out

    try:
        artifacts = asyncio.run(
            _run_pipeline(
                task=task,
                n=n,
                backend=backend,
                backend_kwargs=backend_kwargs,
                strategy=synthesis,
                budget=budget,
                run_parallel=run_parallel,
                raw=raw,
                save_enabled=save_enabled,
                output_dir=output_dir,
                early_stop=early_stop_config,
                rich_output=rich_output,
            )
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    if json_out:
        click.echo(json.dumps(artifacts.to_payload(), ensure_ascii=False))
        return

    if rich_output:
        _render_human_output(artifacts)
        return

    if artifacts.raw:
        click.echo(_format_plain_raw(artifacts.gather.texts))
    else:
        click.echo(artifacts.synthesis.result if artifacts.synthesis else "")


@main.command(name="validate-task")
@click.argument("task_files", nargs=-1, type=click.Path())
def validate_task(task_files: tuple[str, ...]) -> None:
    """Validate one or more task definition files."""
    if not task_files:
        raise click.UsageError("Provide at least one task file.")

    all_valid = True
    for task_file in task_files:
        errors = validate_task_file(task_file)
        if errors:
            all_valid = False
            click.echo(f"FAIL: {task_file}")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo(f"OK: {task_file}")

    if not all_valid:
        raise SystemExit(1)


async def _run_pipeline(
    task: Task,
    n: int,
    backend: str,
    backend_kwargs: dict[str, Any],
    strategy: str,
    budget: ScatterBudget | None,
    run_parallel: bool,
    raw: bool,
    save_enabled: bool,
    output_dir: Path,
    early_stop: EarlyStop | None,
    rich_output: bool,
) -> RunArtifacts:
    """Execute the run and return normalized artifacts."""
    import time

    mode = "parallel" if run_parallel else "sequential"
    model_display = _resolve_model_display(backend, backend_kwargs)
    if rich_output:
        console.print()
        console.print(
            Panel(
                f"[bold]Prompt:[/bold]  {_truncate_prompt(task.prompt)}\n"
                f"[bold]Model:[/bold]   {model_display}\n"
                f"[bold]Backend:[/bold] {backend}\n"
                f"[bold]Agents:[/bold]  {n}\n"
                f"[bold]Mode:[/bold]    {mode}\n"
                f"[bold]Synth:[/bold]   {strategy}",
                title="[bold cyan]Broadside-AI[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        console.print()

    scatter_start = time.perf_counter()
    if rich_output:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Scattering perspectives[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        )
        with progress:
            progress.add_task("scatter", total=None)
            results = await scatter(
                task=task,
                n=n,
                backend=backend,
                backend_kwargs=backend_kwargs,
                budget=budget,
                parallel=run_parallel,
                early_stop=early_stop,
            )
    else:
        results = await scatter(
            task=task,
            n=n,
            backend=backend,
            backend_kwargs=backend_kwargs,
            budget=budget,
            parallel=run_parallel,
            early_stop=early_stop,
        )
    scatter_wall = (time.perf_counter() - scatter_start) * 1000
    gathered = gather(
        results,
        wall_clock_ms=scatter_wall,
        n_requested=n,
        output_schema=task.output_schema,
    )

    if raw:
        saved_to = (
            _save_raw(gathered.texts, task, output_dir, _model_dir_name(gathered.results))
            if save_enabled
            else None
        )
        return RunArtifacts(
            task=task,
            backend=backend,
            model=_resolve_model_name(gathered, backend, backend_kwargs),
            mode=mode,
            requested_strategy=strategy,
            gather=gathered,
            synthesis=None,
            raw=True,
            saved_to=saved_to,
        )

    if rich_output:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Synthesizing result[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        )
        with progress:
            progress.add_task("synthesize", total=None)
            synthesis_result = await synthesize(
                gathered=gathered,
                strategy=strategy,
                backend=backend,
                backend_kwargs=backend_kwargs,
                output_schema=task.output_schema,
            )
    else:
        synthesis_result = await synthesize(
            gathered=gathered,
            strategy=strategy,
            backend=backend,
            backend_kwargs=backend_kwargs,
            output_schema=task.output_schema,
        )

    saved_to = _save_results(synthesis_result, task, output_dir) if save_enabled else None
    return RunArtifacts(
        task=task,
        backend=backend,
        model=_resolve_model_name(gathered, backend, backend_kwargs),
        mode=mode,
        requested_strategy=strategy,
        gather=gathered,
        synthesis=synthesis_result,
        raw=False,
        saved_to=saved_to,
    )


def _render_human_output(artifacts: RunArtifacts) -> None:
    """Render a human-friendly terminal view."""
    if artifacts.raw:
        for index, text in enumerate(artifacts.gather.texts, start=1):
            console.print(Panel(text, title=f"Output {index}", border_style="blue"))
    else:
        assert artifacts.synthesis is not None
        console.print(
            Panel(
                artifacts.synthesis.result,
                title="[bold green]Synthesis[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )
        stats = [
            f"[bold]{artifacts.gather.n_completed}[/bold] agents",
            (
                f"[bold]{artifacts.gather.total_tokens + artifacts.synthesis.synthesis_tokens:,}"
                "[/bold] tokens"
            ),
            f"[bold]{artifacts.gather.wall_clock_ms / 1000:.1f}s[/bold] scatter",
            f"strategy: [bold]{artifacts.synthesis.strategy}[/bold]",
        ]
        console.print(f"\n[dim]{' | '.join(stats)}[/dim]")

    if artifacts.saved_to is not None:
        try:
            display_path = artifacts.saved_to.relative_to(Path.cwd())
        except ValueError:
            display_path = artifacts.saved_to
        console.print(f"\n[dim]Saved to {display_path}[/dim]")


def _truncate_prompt(prompt: str, max_len: int = 60) -> str:
    if len(prompt) <= max_len:
        return prompt
    return prompt[: max_len - 1].rstrip() + "\u2026"


def _load_task_file(path: str) -> Task:
    file_path = Path(path)
    text = file_path.read_text()
    if file_path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    elif file_path.suffix == ".json":
        data = json.loads(text)
    else:
        return Task(prompt=text.strip())

    task_data = {key: value for key, value in data.items() if key != "meta"}
    return Task(**task_data)


def _merge_task_context(task: Task, extra_context: dict[str, Any]) -> Task:
    if not extra_context:
        return task
    merged_context = dict(task.context)
    merged_context.update(extra_context)
    return Task(prompt=task.prompt, context=merged_context, output_schema=task.output_schema)


def _load_context_files(paths: tuple[str, ...]) -> dict[str, str]:
    context: dict[str, str] = {}
    used_keys: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        key = _context_key(path, used_keys)
        used_keys.add(key)
        context[key] = path.read_text(encoding="utf-8").strip()
    return context


def _context_key(path: Path, used_keys: set[str]) -> str:
    import re

    base = re.sub(r"[^a-zA-Z0-9]+", "_", path.name).strip("_").lower() or "context"
    key = base
    suffix = 2
    while key in used_keys:
        key = f"{base}_{suffix}"
        suffix += 1
    return key


def _resolve_model_display(backend: str, backend_kwargs: dict[str, Any]) -> str:
    requested = backend_kwargs.get("model")
    if requested:
        return str(requested)
    if backend == "ollama":
        from broadside_ai.backends.ollama import _DEFAULT_MODEL

        return f"{_DEFAULT_MODEL} (default)"
    if backend == "anthropic":
        return "claude-sonnet-4-20250514 (default)"
    if backend == "openai":
        return "gpt-4o-mini (default)"
    return "(backend default)"


def _resolve_model_name(
    gathered: GatherResult,
    backend: str,
    backend_kwargs: dict[str, Any],
) -> str:
    if gathered.results:
        return gathered.results[0].model
    requested = backend_kwargs.get("model")
    return str(requested) if requested else _resolve_model_display(backend, backend_kwargs)


def _slugify(text: str, max_len: int = 40) -> str:
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_len].rstrip("-")


def _model_dir_name(results: list[Any]) -> str:
    model = getattr(results[0], "model", None) if results else None
    model_name = model or "unknown"
    return str(model_name).replace(":", "-").replace("/", "-")


def _build_run_dir(output_dir: Path, model_name: str, topic: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{topic}_{stamp}" if topic else stamp
    run_dir = output_dir / model_name / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _save_results(result: Synthesis, task: Task, output_dir: Path) -> Path:
    model_dir = _model_dir_name(result.gather.results)
    run_dir = _build_run_dir(output_dir, model_dir, _slugify(task.prompt))
    payload = {
        "schema_version": _JSON_OUTPUT_SCHEMA_VERSION,
        "prompt": task.prompt,
        "model": model_dir,
        "requested_strategy": result.requested_strategy,
        "strategy": result.strategy,
        "synthesis": result.result,
        "parsed_result": result.parsed_result,
        "raw_outputs": result.raw_outputs,
        "stats": {
            "n_requested": result.gather.n_requested,
            "n_completed": result.gather.n_completed,
            "n_failed": result.gather.n_failed,
            "n_parsed": result.gather.n_parsed,
            "total_tokens": result.total_tokens(),
            "scatter_tokens": result.gather.total_tokens,
            "synthesis_tokens": result.synthesis_tokens,
            "wall_clock_ms": round(result.gather.wall_clock_ms, 1),
        },
    }
    (run_dir / "result.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "synthesis.txt").write_text(result.result, encoding="utf-8")
    for index, text in enumerate(result.raw_outputs, start=1):
        (run_dir / f"agent_{index}.txt").write_text(text, encoding="utf-8")
    return run_dir


def _save_raw(texts: list[str], task: Task, output_dir: Path, model_hint: str = "unknown") -> Path:
    run_dir = _build_run_dir(output_dir, model_hint, _slugify(task.prompt))
    for index, text in enumerate(texts, start=1):
        (run_dir / f"agent_{index}.txt").write_text(text, encoding="utf-8")
    (run_dir / "raw.json").write_text(
        json.dumps(
            {
                "schema_version": _JSON_OUTPUT_SCHEMA_VERSION,
                "prompt": task.prompt,
                "model": model_hint,
                "outputs": texts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return run_dir


def _format_plain_raw(texts: list[str]) -> str:
    chunks = []
    for index, text in enumerate(texts, start=1):
        chunks.append(f"--- Output {index} ---\n{text}")
    return "\n\n".join(chunks)
