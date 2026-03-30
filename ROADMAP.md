# Broadside Roadmap

Living document. Updated as work lands. Phases are sequential but items within
a phase can land in any order.

---

## Phase 0 — Foundation (launch blocker)

Goal: `pip install broadside && python quickstart.py` works on first try, no API keys.

- [ ] Package structure (`pyproject.toml`, src layout, extras for backends)
- [ ] Core primitives: `Task`, `ScatterConfig`, `gather()`, `synthesize()`
- [ ] Ollama backend (base install, no API key required)
- [ ] Anthropic backend (`pip install broadside[anthropic]`)
- [ ] OpenAI-compatible backend (`pip install broadside[openai]`)
- [ ] CLI entrypoint (`broadside run`)
- [ ] Budget circuit breaker (per-scatter cost limit + global kill switch)
- [ ] Quick start example (copy-pasteable, under 15 lines, runs against Ollama)
- [ ] CI pipeline that runs quick start as a test
- [ ] README (follows research structure: tagline → problem → quick start → architecture)
- [ ] `llms.txt` for AI-friendly project description

## Phase 1 — Credibility (first two weeks post-launch)

Goal: real numbers that back up the README's claims.

- [ ] Benchmark harness (latency, token cost, output diversity)
- [ ] Benchmark suite: 3–5 task types (creative, analytical, classification, summarization, code review)
- [ ] Broadside vs. sequential baseline on same tasks
- [ ] Broadside vs. LangGraph fan-out on same tasks (if feasible without misrepresenting)
- [ ] Published benchmark results in `benchmarks/` with reproduction instructions
- [ ] Synthesis strategies beyond basic LLM aggregation:
  - [ ] Consensus (best for knowledge tasks — ACL 2025 Kaesberg et al.)
  - [ ] Voting (best for reasoning tasks)
  - [ ] Weighted merge (scored recommendations)
- [ ] Structured output schemas for synthesis (make merging tractable)
- [ ] Conflict detection between scatter outputs
- [ ] Early termination with quality signals (kill branches that aren't adding value)

## Phase 2 — Community (first month)

Goal: a contributor can go from clone to merged PR in under an hour.

- [ ] `CONTRIBUTING.md` with dev setup, `make test`, PR workflow
- [ ] Task library (`tasks/` directory, YAML schema, no core code knowledge needed)
- [ ] 5–10 seed task definitions covering different scatter patterns
- [ ] "Good first issue" labels: new synthesis strategy, new task template, new backend
- [ ] `ARCHITECTURE.md` or ADR explaining why features are out of scope
- [ ] Design philosophy doc (why no inter-agent communication, why no DAG scheduler)

## Phase 3 — Documentation (first month, parallel with Phase 2)

Goal: docs keep people after the README gets them in the door.

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

- [ ] Terminal GIF showing scatter/gather execution
- [ ] Hacker News launch post (honest numbers, working demo)
- [ ] r/LocalLLaMA post (emphasize Ollama-first, local-friendly)
- [ ] AI newsletter pitches (Ben's Bites, The Batch, etc.)
- [ ] `llms.txt` badge in README

## Phase 5 — Hardening (month 2+)

Goal: production-grade reliability.

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

*Last updated: 2026-03-29*
