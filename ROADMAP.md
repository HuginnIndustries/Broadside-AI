# Broadside Roadmap

Living document. Updated as work lands. Phases are sequential but items within
a phase can land in any order.

> **Project status: v0.1.0 alpha** — Core scatter/gather/synthesize pipeline
> works across 3 backends (Ollama, Anthropic, OpenAI). Two synthesis strategies
> (consensus, voting) and conflict detection are implemented. CI and test
> coverage are the primary gaps.

---

## Phase 0 — Foundation (launch blocker)

Goal: `pip install broadside-ai && python quickstart.py` works on first try, no API keys.

**Status: ~85% complete.** All core functionality works. Two items remain: CI pipeline and model catalog discovery.

- [x] Package structure (`pyproject.toml`, src layout, extras for backends)
- [x] Core primitives: `Task`, `ScatterConfig`, `gather()`, `synthesize()`
- [x] Ollama backend (base install, no API key required)
- [x] Anthropic backend (`pip install broadside-ai[anthropic]`)
- [x] OpenAI-compatible backend (`pip install broadside-ai[openai]`)
- [x] CLI entrypoint (`broadside-ai run` + `python -m broadside_ai` for Windows)
- [x] Budget circuit breaker (per-scatter cost limit + global kill switch)
- [x] Quick start example (copy-pasteable, under 15 lines, runs against Ollama)
- [ ] CI pipeline that runs quick start as a test
- [x] README (follows research structure: tagline → problem → quick start → architecture)
- [x] `llms.txt` for AI-friendly project description
- [x] Nested output directory structure (`broadside_ai_output/model/topic_timestamp/`)
- [x] Sequential/parallel auto-detection (local Ollama sequential, cloud parallel)
- [x] Cloud model support (`:cloud` tag detection for Ollama cloud models)
- [ ] Model listing / discovery for Anthropic and OpenAI (their catalogs change with releases)

## Phase 1 — Credibility (first two weeks post-launch)

Goal: real numbers that back up the README's claims.

**Status: ~55% complete.** Benchmark harness, results, consensus/voting strategies, and conflict detection are done. Weighted merge, structured output schemas, early termination, and LangGraph comparison remain.

- [x] Benchmark harness (latency, token cost, output diversity)
- [x] Benchmark suite: 3–5 task types (creative, analytical, classification, summarization, code review)
- [x] Broadside vs. sequential baseline on same tasks (1.75x avg speedup, 2.88x peak)
- [ ] Broadside vs. LangGraph fan-out on same tasks (if feasible without misrepresenting)
- [x] Published benchmark results in `benchmarks/results/` with reproduction instructions
- [x] Synthesis strategies beyond basic LLM aggregation:
  - [x] Consensus (best for knowledge tasks — ACL 2025 Kaesberg et al.)
  - [x] Voting (best for reasoning tasks)
  - [ ] Weighted merge (scored recommendations)
- [ ] Structured output schemas for synthesis (make merging tractable)
- [x] Conflict detection between scatter outputs
- [ ] Early termination with quality signals (kill branches that aren't adding value)

## Phase 2 — Community (first month)

Goal: a contributor can go from clone to merged PR in under an hour.

**Status: ~80% complete.** Core contributor infrastructure is in place. Only "good first issue" labels remain.

- [x] `CONTRIBUTING.md` with dev setup, `make test`, PR workflow
- [x] Task library (`tasks/` directory, YAML schema, no core code knowledge needed)
- [x] 5 seed task definitions covering different scatter patterns
- [ ] "Good first issue" labels: new synthesis strategy, new task template, new backend
- [x] `ARCHITECTURE.md` explaining why features are out of scope
- [x] Design philosophy doc (why no inter-agent communication, why no DAG scheduler)

## Phase 3 — Documentation (first month, parallel with Phase 2)

Goal: docs keep people after the README gets them in the door.

**Status: Not started.**

- [ ] MkDocs site with GitHub Pages
- [ ] Scatter/gather pattern explainer (don't assume reader knowledge)
- [ ] API reference (auto-generated from docstrings)
- [ ] Guide: writing custom synthesis strategies
- [ ] Guide: adding a new backend
- [ ] Guide: when NOT to use Broadside (honest poor-fit cases)
- [ ] Progressive examples: simple → intermediate → real-world use case
- [ ] Architecture diagram (visual scatter/gather flow)

## Phase 4 — Launch visibility (launch week)

Goal: initial awareness in the right channels.

**Status: Not started.**

- [ ] Terminal GIF showing scatter/gather execution
- [ ] Hacker News launch post (honest numbers, working demo)
- [ ] r/LocalLLaMA post (emphasize Ollama-first, local-friendly)
- [ ] AI newsletter pitches (Ben's Bites, The Batch, etc.)
- [ ] `llms.txt` badge in README

## Phase 5 — Hardening (month 2+)

Goal: production-grade reliability.

**Status: Not started.** `checkpoints/` module exists as a stub only.

- [ ] Model diversity across backends (not just temperature variation)
- [ ] Three-stage budget circuit breaker: throttle → isolate → hard trip
- [ ] Human-in-the-loop: pre-scatter review
- [ ] Human-in-the-loop: gather-point review
- [ ] Human-in-the-loop: per-tool approval
- [ ] Agent-initiated escalation (uncertainty-based, not mandated checkpoints)
- [ ] Input partitioning scatter strategy
- [ ] Seeded variation scatter strategy
- [ ] Quality benchmarks (output quality vs. single-agent baseline)
- [ ] Web UI for synthesis review (stretch)

---

## Cross-cutting gaps

These items cut across phases and should be addressed before advancing further:

| Gap | Impact | Effort |
|---|---|---|
| **No CI pipeline** | Can't verify PRs; regressions go unnoticed | Low (GitHub Actions + `make test`) |
| **Thin test coverage** | Only 3 unit test files (`test_task.py`, `test_budget.py`, `test_gather.py`); no tests for CLI, backends, synthesis strategies, or conflicts | Medium |
| **No strategy tests** | Consensus and voting strategies are untested | Low–Medium |

## Recommended next steps

Priorities ordered by impact-to-effort ratio.

### Tier 1 — Unblock everything else

1. **CI pipeline (Phase 0 leftover).** Minimal GitHub Actions workflow: run
   `make test` on push/PR against Python 3.10+. Add ruff linting in the same
   workflow. Single highest-leverage item — gates quality for every future
   change.

2. **Test coverage for existing code.** Before building new features, cover
   what exists:
   - Synthesis strategies: unit tests for `consensus.py` and `voting.py`
   - CLI: test that `broadside-ai run` parses args and invokes the pipeline
     (mock the backends)
   - Conflict detection: test `conflicts.py`
   - Integration test: end-to-end scatter/gather/synthesize with a mock backend

3. **"Good first issue" labels (Phase 2 leftover).** Unlocks community
   contributions. Suggested issues: "add a new synthesis strategy," "add a new
   task template," "add a new backend."

### Tier 2 — Phase 1 feature completion

4. **Structured output schemas.** Makes synthesis tractable and is a
   prerequisite for weighted merge. Define JSON schemas for scatter outputs so
   strategies can operate on structured data rather than raw text.

5. **Weighted merge strategy.** Third synthesis strategy; depends on structured
   output schemas.

6. **Early termination with quality signals.** Requires defining a quality
   metric first. Can prototype with simple heuristics (response length,
   confidence keywords).

### Tier 3 — Documentation and visibility

7. **MkDocs site (Phase 3).** Start with auto-generated API reference from
   docstrings, then add the scatter/gather explainer and strategy guide.

8. **Terminal GIF (Phase 4).** Low effort, high impact for README and launch.

---

## Design constraints (non-negotiable)

These come from the research and project philosophy. Reference this section
when evaluating feature requests or PRs.

1. **Default scatter to 3–5 agents.** Performance plateaus beyond 4 (DeepMind 2025). Allow higher N, but the sweet spot is the default.
2. **Aggregation is the hard problem.** Consensus for knowledge tasks, voting for reasoning tasks. Design synthesis strategies around this distinction.
3. **Budget circuit breakers are mandatory.** Scatter/gather multiplies costs by ~15x. Per-scatter cost budget > global circuit breaker.
4. **No inter-agent communication in the hot path.** Each agent runs independently. This is the core architectural constraint.
5. **Human checkpoints are first-class.** The gather step is the natural HITL point — architecturally cleaner than interrupting mid-hierarchy.
6. **Ollama backend stays in base install.** Zero API keys needed on first contact.

## Out of scope (and why)

| Feature | Why it's out |
|---|---|
| Inter-agent messaging | Adds coordination overhead — the exact thing scatter/gather eliminates |
| Persistent state across scatters | Makes each scatter non-independent; use a database if you need persistence |
| DAG scheduler | Broadside is one pattern (scatter/gather), not a workflow engine |
| Agent roles / personas | No org charts. Tasks in, outputs out. |
| Autonomous long-running agents | Poor fit for scatter/gather; recommend Temporal or similar |

---

*Last updated: 2026-03-30*
