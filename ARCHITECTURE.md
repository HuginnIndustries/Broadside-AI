# Architecture

Broadside-AI is intentionally opinionated. It is a scatter/gather engine for
CLI automation, not a general agent framework.

## Design rule

Every feature proposal gets filtered through one question:

> Does this improve scriptability or result quality without adding orchestration overhead?

If the answer is no, it probably does not belong here.

## Data flow

```text
Task
  |
  v
Scatter -> Agent 1 --
        -> Agent 2 --+-> Gather -> Synthesize -> Output
        -> Agent 3 --
```

Each scatter branch is independent. There is no shared state, no mid-flight
coordination, and no dependency between branches.

## Why the API is function-first

Broadside-AI exposes:

- `scatter()`
- `gather()`
- `synthesize()`
- `run()`

There is no `Pipeline`, `Workflow`, or orchestration object because the system
has one dominant shape. A builder API would add ceremony without adding real
capability.

`Task`, `GatherResult`, and `Synthesis` are data models. The orchestration
steps are plain functions.

## CLI contract

The CLI is designed for use inside other tools:

- `run` writes the final result to stdout by default
- artifacts are written only with `--save` or `--output`
- `--json-output` emits a stable machine-readable payload
- rich terminal output is shown only when stdout is a TTY
- `validate-task` gives a simple success/failure contract for CI
- `--context-file` only supports UTF-8 text files; binary files produce
  a clear error message

That contract matters as much as the Python API. Broadside-AI is intended to be
easy to call from shell scripts, build systems, and subprocess wrappers.

## Structured output pipeline

When `Task.output_schema` is present:

- prompts explicitly require valid JSON
- scatter outputs are parsed during gather
- parsed outputs are stored alongside raw text
- synthesis can use structured strategies such as `weighted_merge`
- early-stop agreement checks ignore `confidence`

Structured-output handling is not bolted on after the fact. It is part of the
main path for automation-oriented use cases.

## Backend model

A backend only needs to implement:

- `complete()`
- `name()`

That interface stays intentionally small because Broadside-AI is built around
single-shot prompts. There is no conversation manager, tool loop, or agent
lifecycle in the hot path.

## Synchronous wrapper

`run_sync()` is a convenience wrapper for scripts, notebooks, and other
contexts where calling the async `run()` directly is inconvenient.

When called from outside any running event loop, it uses `asyncio.run()`
directly.  When called from inside an already-running loop (e.g. Jupyter or
IPython), it spawns a background thread to avoid the "cannot nest event loops"
error. Exception tracebacks are preserved via ``raise ... from ...`` chaining,
but the thread boundary will appear in the raw traceback. For interactive
environments, prefer the async `run()` directly for cleaner error handling.

## Execution defaults

Broadside-AI defaults to:

- parallel execution for Anthropic, OpenAI, and Ollama cloud models
- sequential execution for local Ollama models

This default is meant to help users succeed without tuning. Cloud models benefit
from parallel fan-out. Local models on modest hardware often do not.

## Budget and early stop

Scatter/gather multiplies cost by design, so budget tracking is part of the
core contract, not an optional add-on.

`ScatterBudget` provides an upper bound on token usage. The budget object is
mutated in-place during scatter: each branch's token usage is recorded against
it. Create a fresh `ScatterBudget` for each call if you need independent
tracking across runs.

`EarlyStop` lets callers end a run once enough useful signal has arrived.

## Conflict detection

The `conflicts` module can detect factual contradictions between scatter outputs
as a separate audit step before synthesis. It is **experimental**: the LLM
response is parsed into structured `Conflict` objects using a best-effort regex
extractor, and the detection quality depends heavily on the model's ability to
follow the structured output format.

For production use, prefer the `consensus` synthesis strategy, which handles
disagreements as part of its normal flow.

## Supported extension points

Broadside-AI is designed to grow in a few narrow places:

1. New synthesis strategies
2. New task definitions in `tasks/`
3. New LLM backends
4. Benchmark coverage for more models and workloads
5. Better machine-readable integration examples

These are additive without introducing cross-branch coordination.

## Out of scope

These are deliberate boundaries, not postponed work.

### Inter-agent communication

Agents do not message each other. No inboxes, no shared memory, no blackboard.

Why: once outputs depend on one another, the system stops being scatter/gather
and starts becoming a workflow engine.

### Persistent multi-step state

Each run is independent. If a later run should depend on an earlier one, pass
the earlier result in explicitly as context.

Why: explicit composition is easier to debug than hidden memory.

### DAG scheduling

Broadside-AI is not Airflow, Prefect, or Temporal.

Why: workflow scheduling is a different product with different failure modes.

### Agent roles and crew structure

There are no built-in researcher, reviewer, or planner roles.

Why: role systems imply coordination and dependency. Broadside-AI treats
branches as interchangeable independent attempts.

### Autonomous long-running agents

Broadside-AI does not run self-directed agents that plan, loop, and persist
state over time.

Why: that requires lifecycle management, persistence, and recovery semantics
that would pull the project away from its core pattern.
