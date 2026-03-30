"""Standard benchmark suite — run with `python benchmarks/suite.py`.

Requires Ollama signed in for cloud access (default: nemotron-3-super:cloud), or a local model pulled.
Results are written to benchmarks/results/.

Task types chosen to cover the scatter/gather sweet spot:
1. Creative: multiple valid outputs, diversity is the point
2. Analytical: structured comparison, consensus matters
3. Classification: right/wrong answer, voting should help
4. Summarization: information compression, synthesis adds value
5. Code review: finding issues in parallel, gather catches more
"""

import asyncio
import json
from pathlib import Path

from broadside.benchmark import run_benchmark_suite
from broadside.task import Task

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


async def main() -> None:
    print("Running Broadside benchmark suite...")
    print(f"Tasks: {len(TASKS)}")
    print(f"Backend: ollama (nemotron-3-super:cloud)")
    print(f"Agents per scatter: 3")
    print()

    results = await run_benchmark_suite(
        tasks=TASKS,
        n=3,
        backend="ollama",
        output_dir="benchmarks/results",
    )

    # Print summary table
    print(f"{'Task':<25} {'Speedup':>8} {'Tokens':>8} {'Diversity':>10}")
    print("-" * 55)
    for r in results:
        print(
            f"{r.task_name:<25} "
            f"{r.speedup:>7.2f}x "
            f"{r.token_multiplier:>7.1f}x "
            f"{r.diversity_score:>9.3f}"
        )
    print()
    print(f"Results saved to benchmarks/results/results.json")


if __name__ == "__main__":
    asyncio.run(main())
