# Broadside-AI

[![CI](https://github.com/HuginnIndustries/Broadside-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/HuginnIndustries/Broadside-AI/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/broadside-ai)](https://pypi.org/project/broadside-ai/)
[![Python](https://img.shields.io/pypi/pyversions/broadside-ai)](https://pypi.org/project/broadside-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

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

```bash
pip install broadside-ai
```

Or, to install it as an isolated CLI tool:

```bash
pipx install broadside-ai
```

Optional extras for cloud backends:

```bash
pip install "broadside-ai[anthropic]"
pip install "broadside-ai[openai]"
pip install "broadside-ai[all]"
```

After installing, verify the CLI works:

```bash
broadside-ai --help
```

<details>
<summary>Windows: if <code>broadside-ai</code> is not on PATH</summary>

Use the module entrypoint instead:

```cmd
py -3.11 -m broadside_ai --help
```

Use the same Python launcher version you installed Broadside-AI into. On
machines with multiple Python installs, `py -3` may point at a different
interpreter and fail to find the package.

If you prefer the console-script form, install with `pipx` so the command is
added to a CLI-friendly location.

</details>

<details>
<summary>Install from source</summary>

Clone the repo or download the GitHub ZIP, then install:

```bash
cd Broadside-AI
pip install .
```

To install backend extras from a source checkout:

```bash
pip install ".[anthropic]"
pip install ".[openai]"
pip install ".[all]"
```

</details>

## Quick start

### Guided tour

Broadside-AI needs a real backend before `run` can do useful work. The easiest
way to avoid a frustrating first try is:

1. Confirm the install worked.
2. Set up one backend.
3. Run a single prompt.

#### Step 1: Confirm the install worked

```bash
broadside-ai --help
```

#### Step 2: Pick one backend

Broadside-AI supports Ollama, Anthropic, and OpenAI-compatible APIs. For a
first run, Ollama local is the least setup-heavy option.

#### Step 3: Run your first prompt with Ollama local

Install Ollama, then pull a local model:

```bash
ollama pull gemma3:1b
```

Now run Broadside-AI:

```bash
broadside-ai run --prompt "Write a pitch for a dotfile manager" --n 3 --model gemma3:1b
```

That should print one synthesized result to stdout.

Examples below that reference repository files such as `RELEASE.md`,
`tasks/...`, or `benchmarks/...` assume you are in a checkout of this repo.
A plain `pip install broadside-ai` does not place those files in your current
working directory, so use your own local files or create a task YAML first.

### Plain CLI output

`run` prints only the synthesized result to stdout by default, which makes it
easy to compose with other tools:

```bash
broadside-ai run --prompt "Summarize this changelog" --n 3 > summary.txt
broadside-ai run --prompt "Write a pitch for a dotfile manager" --n 3 --model gemma3:1b
```

Files are written only when you ask for them with `--save` or `--output`.

### Ground inline prompts with local files

For project-specific tasks, pass the source material in with `--context-file`
instead of relying on a bare prompt. Broadside will append those files to the
task sent to every branch.

Only UTF-8 text files are supported. Binary files (images, PDFs, etc.) will
produce a clear error message.

```bash
broadside-ai run \
  --prompt "Plan Broadside-AI's next PyPI release as a concise checklist" \
  --context-file RELEASE.md \
  --context-file pyproject.toml \
  --context-file .github/workflows/publish.yml
```

That works much better for repo operations than an ungrounded prompt like
`"Plan out a PyPI project release"`, which usually produces a generic tutorial.

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

The default Ollama model is `nemotron-3-super:cloud` (a cloud model). If you
run `broadside-ai run` without `--model` and don't have Ollama cloud
configured, you will get a connection error. Either sign in with `ollama
signin` or pass a local model with `--model`.

Override with `--parallel` or `--sequential` when needed.

### Ollama local

```bash
ollama pull gemma3:1b
broadside-ai run --prompt "Write a pitch for a dotfile manager" --n 3 --model gemma3:1b
```

### Anthropic

Set `ANTHROPIC_API_KEY` in your shell first, then run:

```bash
pip install "broadside-ai[anthropic]"
broadside-ai run --prompt "Review this design" --n 3 --backend anthropic
```

### OpenAI-compatible APIs

Set `OPENAI_API_KEY` in your shell first, then run:

```bash
pip install "broadside-ai[openai]"
broadside-ai run --prompt "Compare these options" --n 3 --backend openai
```

For OpenAI-compatible providers, set `OPENAI_BASE_URL` and pass `--model`.

## CLI for automation

Choose the synthesis strategy based on the kind of output you want:

- `llm`: one direct final answer for the user or downstream tool
- `consensus`: an analysis of agreements, disagreements, and unique claims
- `voting`: aggregation for discrete answers or majority positions
- `weighted_merge`: algorithmic merge for structured JSON-like outputs

### Stable JSON output

Use `--json-output` for scripts and subprocess integrations:

```bash
broadside-ai run tasks/ticket_classification.yaml --n 5 --synthesis weighted_merge --json-output
```

The JSON payload always includes:

- `schema_version`
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

`schema_version` is included so other tools can depend on the payload shape.

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
broadside-ai validate-task my_task.yaml
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

## Common workflows

### Code review aggregation

```bash
broadside-ai run tasks/code_review.yaml --n 3 --synthesis consensus --save
```

### Structured ticket triage for another tool

```bash
broadside-ai run tasks/ticket_classification.yaml --n 5 --synthesis weighted_merge --json-output > ticket.json
```

### CI validation for task files

```bash
broadside-ai validate-task tasks/_template.yaml
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

`run_sync` works outside any event loop (plain scripts) and inside one
(Jupyter, IPython) by spawning a background thread. For cleaner error handling
in interactive environments, use the async `run` directly. `Task.context`
values are rendered with `str()`; prefer plain strings, numbers, or small
text blocks — large dicts or lists will render as their Python `repr`, which
is rarely useful in a prompt.

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
- `synthesize()`: collapse outputs with `llm` for a direct answer, `consensus` for analysis, `voting` for discrete choices, or `weighted_merge` for structured data
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

Broadside-AI is at **v0.1.0** (first public release). The CLI interface,
JSON output schema, and Python API (`run`, `run_sync`, `Task`, `EarlyStop`)
are considered stable for this release. Synthesis strategies and backend
options may expand in future versions. Breaking changes before v1.0 will
be noted in [release notes](https://github.com/HuginnIndustries/Broadside-AI/releases).
