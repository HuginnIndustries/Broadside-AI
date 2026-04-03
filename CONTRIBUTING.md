# Contributing to Broadside-AI

Broadside-AI is a small, opinionated project. Contributions are welcome, but
the bar is clarity, correctness, and fit with the product shape.

## Development setup

```bash
git clone https://github.com/HuginnIndustries/Broadside-AI.git
cd Broadside-AI
pip install -e ".[dev]"
make test
```

All tests and checks should pass locally before you open a PR.

## Development commands

```bash
make test
make lint
make typecheck
make release-check
make clean
```

`make release-check` runs the full local release gate:

- tests
- Ruff lint and formatting checks
- mypy
- package build
- `twine check`

## Good first contributions

### Task library additions

Add a YAML task under `tasks/` and validate it:

```bash
broadside-ai validate-task tasks/my_task.yaml
python -m broadside_ai validate-task tasks/my_task.yaml
```

Task-library changes are the easiest way to contribute without touching runtime
code.

### Synthesis improvements

Look at:

- `src/broadside_ai/strategies/consensus.py`
- `src/broadside_ai/strategies/voting.py`
- `src/broadside_ai/strategies/weighted_merge.py`

New strategies should improve aggregation quality without introducing branch
coordination.

### Benchmarks

Run the benchmark suite against another model or hardware profile and contribute
the results:

```bash
python benchmarks/suite.py
python benchmarks/suite.py gemma3:1b
python benchmarks/suite.py --backend anthropic
```

## Contribution rules

- keep PRs focused
- include tests for behavior changes
- update docs when behavior or defaults change
- prefer source-of-truth changes over one-off fixes
- do not expand scope past scatter/gather

## What will not be merged

Broadside-AI intentionally excludes:

- inter-agent communication
- DAG orchestration
- persistent multi-step agent memory
- role-based crew systems
- autonomous long-running agents

See `ARCHITECTURE.md` if you are unsure whether an idea fits.

## Release-sensitive changes

If a change affects any of the following, update the corresponding docs in the
same PR:

- install or quick-start behavior
- default models or backend behavior
- CLI flags, JSON payloads, or output paths
- package metadata or extras
- benchmark claims in `README.md`

For release work, follow `RELEASE.md`.
