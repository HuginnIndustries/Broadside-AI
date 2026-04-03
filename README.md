# Broadside-AI

Broadside-AI is a CLI-first Python tool for parallel LLM aggregation. It fans a
task out to multiple independent runs, gathers the outputs, and produces one
final result that works well in scripts, CI, and other automation.

It is intentionally narrow:

- no inter-agent messaging
- no workflow DAGs
- no persistent multi-step state
- no crew hierarchy or planner/reviewer role system

That constraint is the product. Broadside-AI is for cases where "ask several
times, then combine the signal" is useful, but a full orchestration framework
would be overkill.

## Where it helps

Broadside-AI is strongest when parallel attempts add value:

- code review, where multiple passes catch different issues
- classification and extraction, where structured outputs can be merged
- comparison and analysis, where consensus matters
- generation, where diversity creates better raw material

Committed benchmark snapshots in `benchmarks/results/` currently show:

- `2.52x` average speedup vs sequential with Anthropic Claude Sonnet 4
- `2.26x` average speedup vs sequential with Ollama cloud Nemotron
- `1.07x` average speedup on a modest local CPU with `gemma3:1b`

## Install

Base install includes the Ollama backend:

```bash
pip install broadside-ai
```

Optional extras:

```bash
pip install broadside-ai[anthropic]
pip install broadside-ai[openai]
pip install broadside-ai[all]
```

## Quick start

### Plain CLI output

`run` prints only the synthesized result to stdout by default, which makes it
easy to compose with other tools:

```bash
broadside-ai run --prompt "Write a pitch for a dotfile manager" --n 3
python -m broadside_ai run --prompt "Summarize this changelog" --n 3 > summary.txt
```

Files are written only when you ask for them with `--save` or `--output`.

### Ollama cloud

Install Ollama, sign in, and pull the default cloud model:

```bash
ollama signin
ollama pull nemotron-3-super:cloud
broadside-ai run --prompt "Write a pitch for a dotfile manager" --n 3
```

Execution defaults are tuned for user success:

- cloud backends and Ollama cloud models run in parallel by default
- local Ollama models run sequentially by default

Override with `--parallel` or `--sequential` when needed.

### Ollama local

```bash
ollama pull gemma3:1b
broadside-ai run --prompt "Write a pitch for a dotfile manager" --n 3 --model gemma3:1b
```

### Anthropic

```bash
pip install broadside-ai[anthropic]
export ANTHROPIC_API_KEY=your-key-here
broadside-ai run --prompt "Review this design" --n 3 --backend anthropic
```

### OpenAI-compatible APIs

```bash
pip install broadside-ai[openai]
export OPENAI_API_KEY=your-key-here
broadside-ai run --prompt "Compare these options" --n 3 --backend openai
```

For OpenAI-compatible providers, set `OPENAI_BASE_URL` and pass `--model`.

## CLI for automation

### Stable JSON output

Use `--json-output` for scripts and subprocess integrations:

```bash
broadside-ai run tasks/ticket_classification.yaml --n 5 --synthesis weighted_merge --json-output
```

The JSON payload always includes:

- `status`
- `prompt`
- `backend`
- `model`
- `mode`
- `requested_strategy`
- `strategy`
- `result`
- `parsed_result`
- `raw_outputs`
- `gather`
- `saved_to`

`gather` includes `n_requested`, `n_completed`, `n_failed`, `n_parsed`,
`total_tokens`, and `wall_clock_ms`.

### Save artifacts when you want them

```bash
broadside-ai run tasks/code_review.yaml --n 3 --save
broadside-ai run tasks/code_review.yaml --n 3 --output artifacts/review-run
```

Saved runs go under:

```text
broadside_ai_output/{model}/{topic}_{timestamp}/
```

### Validate task files

```bash
broadside-ai validate-task tasks/ticket_classification.yaml
python -m broadside_ai validate-task tasks/ticket_classification.yaml
```

Validation exits `0` when every file is valid and `1` when any file fails.

## Structured outputs and early stop

If a task provides `output_schema`, Broadside-AI asks every branch to return
valid JSON and parses the results through the full pipeline.

That enables `weighted_merge`, an algorithmic synthesis strategy that:

- makes zero LLM calls on the happy path
- merges numeric fields with weighted averages
- merges strings with majority vote
- merges lists by majority presence
- uses `confidence` as weight metadata, not as an output field

Example:

```bash
broadside-ai run tasks/ticket_classification.yaml --n 5 --synthesis weighted_merge --json-output
```

You can also stop early when enough branches have arrived or agreed:

```bash
broadside-ai run tasks/ticket_classification.yaml --n 5 --early-stop 3 --agreement 0.66
```

## Python API

```python
from broadside_ai import EarlyStop, Task, run_sync

task = Task(
    prompt="Classify this support message.",
    output_schema={
        "label": "string",
        "confidence": "float",
        "reasoning": "string",
    },
)

result = run_sync(
    task,
    n=5,
    backend="ollama",
    synthesis_strategy="weighted_merge",
    early_stop=EarlyStop(min_complete=3, agreement_threshold=0.66),
)

print(result.result)
print(result.parsed_result)
```

Async usage:

```python
from broadside_ai import Task, run

task = Task(prompt="Summarize the tradeoffs of SQLite vs PostgreSQL for analytics.")
result = await run(task, n=3, backend="ollama")
print(result.result)
```

## Core model

```text
Task -> Scatter -> Gather -> Synthesize
```

- `Task`: prompt, optional context, optional output schema
- `scatter()`: run the task across `n` independent branches
- `gather()`: normalize outputs, parse structured results, and compute stats
- `synthesize()`: collapse outputs with `llm`, `consensus`, `voting`, or `weighted_merge`
- `run()`: convenience wrapper for the full pipeline

## Development

```bash
pip install -e ".[dev]"
make test
make lint
make typecheck
make release-check
```

Repository docs:

- [Architecture](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
- [Release process](RELEASE.md)
- [Roadmap](ROADMAP.md)
- [Task library](tasks/README.md)
- [Benchmarks](benchmarks/README.md)

## Status

Broadside-AI is pre-1.0 software, but the repo is intended to be usable and
releasable as-is: package metadata, CLI behavior, task validation, and release
checks are kept in sync in-repo. The markdown docs in this repository are the
source of truth.
