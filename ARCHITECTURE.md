# Architecture

This document explains Broadside's design decisions and, more importantly,
what's deliberately out of scope and why. Reference this when evaluating
feature requests.

## The Core Constraint

Every design decision is tested against one question:

> Does this add coordination overhead without a clear benefit?

If yes, it doesn't belong in Broadside.

## Data Flow

```
Task
  │
  ▼
Scatter ──→ Agent 1 ──┐
       ──→ Agent 2 ──┤  (parallel, independent, no shared state)
       ──→ Agent 3 ──┘
                      │
                      ▼
                   Gather (normalize outputs, compute stats)
                      │
                      ▼
                  Synthesize (consensus / voting / LLM)
                      │
                      ▼
                   Output (with cost + diversity metadata)
```

Each step is independently callable. `run()` wires them together for the
common case, but you can call `scatter()`, `gather()`, and `synthesize()`
individually when you need more control.

## Why These Design Decisions

### Functions over classes

The public API is `scatter()`, `gather()`, `synthesize()`, `run()` — functions,
not methods on an orchestrator object. There's no `Pipeline` class or `Workflow`
builder.

Why: the scatter/gather pattern is a pipeline with exactly one shape. A class
would add ceremony without adding capability. The `Task` and `Synthesis`
dataclasses hold state because they need to; the operations on them don't.

### Backends are pluggable but minimal

A backend implements two methods: `complete()` and `name()`. That's it.
No streaming, no tool use, no conversation history.

Why: scatter agents are stateless single-shot calls. They don't need
conversational APIs. Keeping the backend interface thin means adding a new
provider is ~50 lines of code.

### Ollama in base install

The Ollama backend uses only `httpx` (already a dependency). Anthropic and
OpenAI are optional extras.

Why: someone should be able to `pip install broadside` and run the quick start
without an API key. First impressions are permanent.

### Budget circuit breakers are mandatory

Every scatter tracks token usage. You can set `max_tokens` to kill branches
that exceed a budget.

Why: scatter/gather multiplies API costs by N. Without budget controls, a
misconfig with N=20 burns through an API budget in seconds. This is a safety
feature, not an optimization.

### 3–5 agents is the default

`n=3` is the default. We warn (but allow) N > 20.

Why: Google DeepMind's "Towards a Science of Scaling Agent Systems" (Dec 2025)
tested 180 configurations and found performance plateaus beyond 4 agents.
Practitioners (Skywork.ai, n8n) report the same. Higher N has diminishing
returns and increasing merge complexity.

### Three synthesis strategies

- **LLM** (default): general-purpose, works for everything
- **Consensus**: best for knowledge tasks (ACL 2025, Kaesberg et al.)
- **Voting**: best for reasoning/classification (self-consistency sampling)

Why these three: they map to the research on what actually works. We don't
offer "pick the best one" because that requires a quality metric we can't
define generically.

## What's Out of Scope

These aren't temporary omissions — they're architectural decisions.

### Inter-agent communication

Agents don't talk to each other. No shared memory, no message passing, no
blackboard. Each scatter branch is fully independent.

Why: inter-agent communication is the primary source of coordination overhead
in hierarchical frameworks. UC Berkeley's MAST taxonomy (NeurIPS 2025) found
coordination breakdowns were 36.9% of all failures across seven frameworks.
Broadside eliminates this failure mode by design.

If you need agents to communicate, you need a different tool. LangGraph's
state graph or CrewAI's crew model are designed for that.

### Persistent state across scatters

Each scatter/gather cycle is independent. There's no "memory" that carries
forward from one scatter to the next.

Why: persistent state creates coupling. If scatter #2 depends on scatter #1's
output, you're building a DAG, not a scatter/gather. Use the output of one
`run()` call as context for the next — that's explicit and debuggable.

### DAG scheduling

Broadside is one pattern: scatter/gather. It's not a workflow engine.

Why: DAG schedulers (Airflow, Prefect, Temporal) already exist and are
battle-tested. Building another one would be scope creep. If your workflow
has dependencies between steps, use a DAG scheduler and call Broadside for
the parallelizable steps within it.

### Agent roles or personas

There are no "researcher agents" or "reviewer agents." There are tasks and
there are agents that run them.

Why: roles create implicit coordination. A "reviewer" implies it's reviewing
something another agent produced. That's a dependency. Broadside's agents
are anonymous and interchangeable by design.

### Autonomous long-running agents

Broadside doesn't run agents that loop indefinitely, make their own decisions
about what to do next, or manage their own lifecycle.

Why: scatter/gather is a batch pattern. It starts, runs N branches, collects
results, and stops. Long-running autonomous agents need lifecycle management,
error recovery, and persistence — features that pull the framework toward
a different architecture entirely.

## Extending Broadside

The right extension points are:

1. **Synthesis strategies**: new ways to collapse N outputs → 1
2. **Task definitions**: YAML files in `tasks/`, no core code needed
3. **Backends**: new LLM providers via the `Backend` interface
4. **Benchmarks**: measuring how scatter/gather performs on different task types

These are all additive — they extend capability without adding coordination.
