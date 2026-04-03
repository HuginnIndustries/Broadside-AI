"""Standard benchmark suite - run with `python benchmarks/suite.py`.

Results are written to benchmarks/results/.

Usage:
    python benchmarks/suite.py                                          # Ollama cloud (default)
    python benchmarks/suite.py deepseek-v3.2:cloud                      # alternate cloud model
    python benchmarks/suite.py gemma3:1b                                # local Ollama model
    python benchmarks/suite.py --backend anthropic                      # Anthropic
    python benchmarks/suite.py --backend anthropic --model claude-sonnet-4-20250514
    python benchmarks/suite.py --backend openai                         # OpenAI
    python benchmarks/suite.py --backend openai --model gpt-4o          # specific OpenAI model
"""

import asyncio
import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from broadside_ai.task import Task

console = Console()

TASKS = [
    (
        "creative_pitch",
        Task(
            prompt=(
                "Write a one-paragraph pitch for a developer tool that "
                "automatically generates changelog entries from git commits. "
                "Make it compelling and specific."
            ),
        ),
    ),
    (
        "analytical_comparison",
        Task(
            prompt=(
                "Compare SQLite, PostgreSQL, and DuckDB for a read-heavy "
                "analytics workload processing 10M rows. Cover: query speed, "
                "memory usage, operational complexity, and ecosystem maturity. "
                "Return a structured comparison."
            ),
        ),
    ),
    (
        "classification",
        Task(
            prompt=(
                "Classify the following customer message as one of: "
                "billing_issue, technical_support, feature_request, praise, spam.\n\n"
                "Message: 'I've been trying to export my data for three days "
                "now and the CSV download just hangs at 99%. I need this for "
                "a board meeting tomorrow. Please help urgently.'"
            ),
            output_schema={"label": "string", "confidence": "float", "reasoning": "string"},
        ),
    ),
    (
        "summarization",
        Task(
            prompt=(
                "Summarize the key tradeoffs of microservices vs monolith "
                "architecture for a startup with 5 engineers building a B2B "
                "SaaS product. Keep it under 200 words and be opinionated."
            ),
        ),
    ),
    (
        "code_review",
        Task(
            prompt=(
                "Review this Python function for bugs, performance issues, "
                "and style problems:\n\n"
                "```python\n"
                "def get_users(db, filters={}):\n"
                "    query = f'SELECT * FROM users WHERE 1=1'\n"
                "    for key, val in filters.items():\n"
                "        query += f\" AND {key} = '{val}'\"\n"
                "    results = db.execute(query)\n"
                "    users = []\n"
                "    for row in results:\n"
                "        user = dict(row)\n"
                "        user['password'] = decrypt(user['password'])\n"
                "        users.append(user)\n"
                "    return users\n"
                "```\n"
                "List every issue you find with severity (critical/high/medium/low)."
            ),
        ),
    ),
]


def _build_results_table(completed: list, task_names: list[str], current_idx: int) -> Table:
    """Build a rich table showing benchmark progress."""
    table = Table(
        title="Benchmark Results",
        show_lines=True,
        title_style="bold cyan",
        border_style="blue",
    )
    table.add_column("Task", style="bold", min_width=22)
    table.add_column("Scatter", justify="right", min_width=9)
    table.add_column("Sequential", justify="right", min_width=11)
    table.add_column("Speedup", justify="right", min_width=8)
    table.add_column("Cost", justify="right", min_width=7)
    table.add_column("Diversity", justify="right", min_width=9)
    table.add_column("Status", justify="center", min_width=10)

    for i, name in enumerate(task_names):
        if i < len(completed):
            r = completed[i]
            spd = r.speedup
            if spd >= 2.5:
                spd_style = "bold green"
            elif spd >= 1.5:
                spd_style = "green"
            else:
                spd_style = "yellow"

            table.add_row(
                name,
                f"{r.scatter_wall_ms / 1000:.1f}s",
                f"{r.sequential_wall_ms / 1000:.1f}s",
                Text(f"{spd:.2f}x", style=spd_style),
                f"{r.token_multiplier:.1f}x",
                f"{r.diversity_score:.3f}",
                Text("Done", style="bold green"),
            )
        elif i == current_idx:
            table.add_row(
                name,
                "",
                "",
                "",
                "",
                "",
                Text("Running...", style="bold yellow"),
            )
        else:
            table.add_row(
                name,
                Text("-", style="dim"),
                Text("-", style="dim"),
                Text("-", style="dim"),
                Text("-", style="dim"),
                Text("-", style="dim"),
                Text("Pending", style="dim"),
            )

    if completed:
        avg_spd = sum(r.speedup for r in completed) / len(completed)
        avg_cost = sum(r.token_multiplier for r in completed) / len(completed)
        avg_div = sum(r.diversity_score for r in completed) / len(completed)
        table.add_row(
            Text("Average", style="bold"),
            "",
            "",
            Text(f"{avg_spd:.2f}x", style="bold"),
            Text(f"{avg_cost:.1f}x", style="bold"),
            Text(f"{avg_div:.3f}", style="bold"),
            f"{len(completed)}/{len(task_names)}",
            style="on grey15",
        )

    return table


def _parse_args() -> tuple[str, dict]:
    """Parse CLI args: positional model, --backend, --model flags."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the Broadside-AI benchmark suite.",
        epilog=(
            "examples:\n"
            "  python benchmarks/suite.py                              # Ollama cloud (default)\n"
            "  python benchmarks/suite.py deepseek-v3.2:cloud          # Ollama cloud model\n"
            "  python benchmarks/suite.py --backend anthropic          # Anthropic\n"
            "  python benchmarks/suite.py --backend openai --model gpt-4o\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("model", nargs="?", default=None, help="Model name (shortcut for --model)")
    parser.add_argument("--backend", "-b", default="ollama", help="LLM backend (default: ollama)")
    parser.add_argument("--model", "-m", dest="model_flag", default=None, help="Model name")

    args = parser.parse_args()

    model = args.model_flag or args.model
    backend = args.backend
    bk = {"model": model} if model else {}

    return backend, bk


async def main() -> None:
    backend, bk = _parse_args()
    n = 3

    model_name = bk.get("model", "")
    if not model_name:
        if backend == "ollama":
            model_display = "nemotron-3-super:cloud (default)"
        elif backend == "anthropic":
            model_display = "claude-sonnet-4-20250514 (default)"
        elif backend == "openai":
            model_display = "gpt-4o-mini (default)"
        else:
            model_display = "(backend default)"
    else:
        model_display = model_name

    mode = "parallel"

    console.print()
    console.print(
        Panel(
            f"[bold]Model:[/bold]   {model_display}\n"
            f"[bold]Backend:[/bold] {backend}\n"
            f"[bold]Agents:[/bold]  {n}\n"
            f"[bold]Tasks:[/bold]   {len(TASKS)}\n"
            f"[bold]Mode:[/bold]    {mode}",
            title="[bold cyan]Broadside-AI Benchmark Suite[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()

    task_names = [name for name, _ in TASKS]
    completed = []
    current_idx = 0
    suite_start = time.perf_counter()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("{task.completed}/{task.total} tasks"),
        TimeElapsedColumn(),
        console=console,
    )
    overall_task = progress.add_task("Benchmarking", total=len(TASKS))

    def on_task_start(name, idx, total):
        nonlocal current_idx
        current_idx = idx

    def on_task_done(result, idx, total):
        completed.append(result)
        progress.update(overall_task, advance=1)

    with Live(
        _build_results_table(completed, task_names, current_idx),
        console=console,
        refresh_per_second=4,
    ) as live:

        async def run_with_live():
            results = []
            total = len(TASKS)
            for i, (name, task) in enumerate(TASKS):
                on_task_start(name, i, total)
                live.update(_build_results_table(completed, task_names, current_idx))

                from broadside_ai.benchmark import benchmark_task

                r = await benchmark_task(
                    task=task,
                    task_name=name,
                    n=n,
                    backend=backend,
                    backend_kwargs=bk,
                )
                on_task_done(r, i, total)
                live.update(_build_results_table(completed, task_names, current_idx))
                results.append(r)
            return results

        results = await run_with_live()

    suite_elapsed = time.perf_counter() - suite_start

    from broadside_ai.benchmark import _build_run_dir, _save_benchmark_results

    run_dir = _build_run_dir("benchmarks/results", results, backend, bk)
    _save_benchmark_results(results, run_dir, n, backend, bk)

    console.print()
    avg_spd = sum(r.speedup for r in results) / len(results)
    avg_cost = sum(r.token_multiplier for r in results) / len(results)
    avg_div = sum(r.diversity_score for r in results) / len(results)
    best = max(results, key=lambda r: r.speedup)

    console.print(
        Panel(
            f"[bold green]Suite completed in {suite_elapsed:.1f}s[/bold green]\n\n"
            f"  Average speedup:    [bold]{avg_spd:.2f}x[/bold] (parallel vs sequential)\n"
            f"  Average cost:       [bold]{avg_cost:.1f}x[/bold] (vs single call)\n"
            f"  Average diversity:  [bold]{avg_div:.3f}[/bold]\n"
            "  Best speedup:       "
            f"[bold green]{best.speedup:.2f}x[/bold green] ({best.task_name})\n\n"
            f"  Saved to: [blue]{run_dir}[/blue]",
            title="[bold cyan]Summary[/bold cyan]",
            border_style="green",
            padding=(1, 2),
        )
    )

    console.print()
    console.print("[dim]Run with a different backend or model:[/dim]")
    console.print("[dim]  python benchmarks/suite.py deepseek-v3.2:cloud[/dim]")
    console.print("[dim]  python benchmarks/suite.py --backend anthropic[/dim]")
    console.print("[dim]  python benchmarks/suite.py --backend openai --model gpt-4o[/dim]")
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
