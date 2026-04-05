# Broadside-AI Roadmap

This roadmap tracks the next steps after the Broadside-AI v1 cleanup pass.

## Current baseline

The project now has:

- a CLI-first scatter/gather runtime
- stdout-first default behavior for automation
- stable `--json-output` payloads
- task validation from the main CLI
- structured-output parsing through gather and synthesis
- `weighted_merge` for structured tasks
- early-stop controls for cost and latency
- tests, benchmarks, CI, and release/publish workflows

## Near-term priorities

### 1. First public release

- publish the first package to PyPI
- cut the initial GitHub release notes
- verify Trusted Publishing end to end
- confirm README rendering and metadata on PyPI

### 2. Backend docs and troubleshooting

- add dedicated backend setup docs
- document Ollama local vs cloud troubleshooting
- document OpenAI-compatible provider configuration
- add a "when not to use Broadside-AI" guide

### 3. Integration depth

- add more subprocess and CI examples
- document JSON payload versioning expectations
- add examples for structured extraction and ticket triage
- add benchmark recipes for comparing backends

### 4. Quality and coverage

- add backend contract tests with fake clients
- add more CLI smoke tests in CI
- add release smoke tests for example workflows
- add benchmark-result sanity checks

### 5. Community readiness

- ~~add issue templates and a PR template~~ (done)
- label good first issues
- document benchmark contribution expectations

## Longer-term ideas

- richer conflict detection on structured outputs
- model-diversity scatter strategies
- optional result schema versioning for JSON mode
- hosted documentation site

## Non-goals

These remain out of scope unless the product identity changes:

- inter-agent messaging
- workflow DAG orchestration
- long-running autonomous agents
- crew or role hierarchies
- hidden persistent memory across runs

## Maintainer note

The repository markdown files are part of the product surface. If behavior
changes, update the docs in the same PR.

Last updated: 2026-04-05
