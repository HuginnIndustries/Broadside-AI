# Contributing to Broadside

Broadside is early-stage and welcomes contributions. The fastest path from
clone to merged PR is through the task library — you can contribute a YAML
file without touching core code.

## Quick Start (5 minutes)

```bash
git clone https://github.com/huginnindustries/broadside.git
cd broadside
pip install -e ".[dev]"
make test
```

All 12 tests should pass. If they don't, open an issue.

## Ways to Contribute

### 1. Task Library (easiest — no core code needed)

Add a YAML file to `tasks/`. A task is a well-scoped prompt with optional
context and output schema. See `tasks/README.md` for the schema.

```bash
# Add your task
cp tasks/_template.yaml tasks/my_task.yaml
# Edit it
# Validate
python -m broadside_ai.task_validator tasks/my_task.yaml
# Open a PR — no issue required for task contributions
```

### 2. Synthesis Strategies

New ways to collapse N outputs into one. Look at
`src/broadside_ai/strategies/consensus.py` for the pattern. Ideas:

- Weighted merge (scored recommendations)
- Structured extraction (pull specific fields from each output)
- Embedding-based clustering (group similar outputs, pick representative)

Open an issue first to discuss the approach.

### 3. Benchmarks

Run the benchmark suite against a different model and contribute your results:

```bash
python benchmarks/suite.py deepseek-v3.2:cloud
```

Results are saved to `benchmarks/results/` in a timestamped folder with full
reproduction data. See `benchmarks/README.md` for details on metrics and output
structure.

### 4. Backend Integrations

Add support for a new LLM provider. Implement the `Backend` interface in
`src/broadside_ai/backends/base.py`. Current backends (Ollama, Anthropic, OpenAI)
are good reference implementations.

Open an issue first.

## Development

```bash
make test        # Run tests
make lint        # Run ruff linter
make typecheck   # Run mypy
```

## Code Style

- Comments explain WHY, not what
- Simple and readable over clever
- Functions first, classes when state demands it
- Type hints on all public functions

## PR Guidelines

- Keep PRs focused — one feature or fix per PR
- Task library contributions: no issue required, just open the PR
- Core code changes: open an issue first to discuss
- Include tests for new functionality
- Run `make test && make lint` before opening

## What We Won't Merge

Broadside has a clear scope. These are out of bounds (see `ARCHITECTURE.md`):

- Inter-agent communication or messaging
- Persistent state across scatter operations
- DAG scheduling or workflow orchestration
- Agent roles, personas, or org charts
- Autonomous long-running agents

If you're unsure whether something fits, open an issue and ask.
