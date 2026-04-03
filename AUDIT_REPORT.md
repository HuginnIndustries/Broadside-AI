# Broadside-AI Project Audit Report

**Date:** 2026-04-03
**Version Audited:** 0.1.0 (pre-release alpha)
**Repository:** HuginnIndustries/Broadside-AI

---

## 1. Executive Summary

Broadside-AI is a CLI-first Python tool for **parallel LLM orchestration using a scatter/gather architecture**. It fans a prompt out to N independent LLM calls, collects the results, and synthesizes them into a single output. The project targets automation and CI/CD scenarios where running a task multiple times and aggregating signal is valuable without the overhead of a full workflow framework.

**Overall Assessment:** The project demonstrates strong engineering fundamentals for an alpha-stage tool. Architecture is clean and intentionally scoped, code quality tooling is strict, security posture is solid, and CI/CD is comprehensive. A handful of minor issues and missing features are noted below.

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Architecture | Strong | Clean scatter/gather pipeline, well-separated concerns |
| Code Quality | Strong | Strict mypy, Ruff, no dead code, consistent patterns |
| Security | Strong | No hardcoded secrets, safe parsing, validated inputs |
| Testing | Adequate | 39 tests cover core paths; no coverage reporting |
| CI/CD | Strong | Multi-platform matrix, smoke tests, package validation |
| Documentation | Strong | 6 markdown docs, task library, examples |
| Dependencies | Good | Minimal core deps, optional extras, modern build system |

---

## 2. Architecture & Design

### Core Pipeline

```
Task  ->  Scatter  ->  [Agent 1, Agent 2, ..., Agent N]  ->  Gather  ->  Synthesize  ->  Output
```

- **Task** (`task.py`, 43 lines) - Pydantic model: prompt + optional context + optional output_schema
- **Scatter** (`scatter.py`, 120 lines) - Fans task to N independent calls (parallel or sequential)
- **Gather** (`gather.py`, 74 lines) - Normalizes results, parses JSON, computes stats
- **Synthesize** (`synthesize.py`, 103 lines) - Merges results via pluggable strategies
- **Run** (`run.py`, 94 lines) - Convenience orchestrator for the full pipeline

### Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| Strategy | `strategies/` | Pluggable synthesis algorithms (llm, consensus, voting, weighted_merge) |
| Plugin/Registry | `backends/__init__.py` | Dynamic backend loading with `register()` / `get_backend()` |
| Stateless Pipeline | Core modules | No shared state between stages or runs |
| Circuit Breaker | `budget.py` | Token budget enforcement with thread-safe tracking |

### Scope Boundaries (By Design)

The project explicitly excludes: inter-agent messaging, workflow DAGs, persistent state, crew/role hierarchies, and autonomous long-running agents. This is documented in `ARCHITECTURE.md` and enforced in `CONTRIBUTING.md` (what-won't-be-merged section).

### Codebase Size

- **Source:** ~2,400 lines across 24 files in `src/broadside_ai/`
- **Tests:** ~500 lines across 9 test files + 79-line conftest
- **Total repository:** Compact and navigable

---

## 3. Code Quality

### Tooling

| Tool | Configuration | Status |
|------|--------------|--------|
| **mypy** | `strict = true`, Python 3.10 target | Enabled, CI-enforced |
| **Ruff** | Line length 99, select E/F/I/N/W/UP | Enabled, CI-enforced |
| **Type hints** | Throughout all source files | Consistent |

### Observations

- **No dead code detected.** All modules are used in the pipeline.
- **No TODO/FIXME/HACK comments** in the source.
- **No hardcoded secrets** anywhere in the codebase.
- **Consistent naming conventions** across all modules.
- **Clean async patterns** using `asyncio.gather()` for parallel execution.
- **Pydantic validation** with `extra = "forbid"` prevents silent misconfiguration.
- **Thread-safe budget tracking** using `threading.Lock`.

### Minor Style Notes

- Backend constructors contain long multi-line error messages with shell commands (`backends/anthropic.py:36-41`, `backends/openai.py:37-42`). Functional but could use `textwrap.dedent` for readability.

---

## 4. Security

### Strengths

| Area | Implementation | Risk |
|------|---------------|------|
| API key handling | Environment variables only (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), never logged | Low |
| YAML parsing | `yaml.safe_load()` used exclusively (prevents code injection) | Low |
| Input validation | Pydantic with `extra: forbid`; `n >= 1` enforced; budget limits | Low |
| Code injection surface | No `eval()`, `exec()`, `pickle`, or shell command construction | Low |
| HTTP requests | Via httpx and official SDK clients only | Low |
| Dependency surface | 5 core deps, all well-maintained libraries | Low |

### Minor Observations

1. **Model name path construction** (`cli.py:419`): Model names are sanitized with `.replace(":", "-").replace("/", "-")` before use in directory paths. Adequate for the threat model (CLI user controls input), but a `pathlib` canonicalization would be more defensive.

2. **Prompt injection via task context**: Context is directly interpolated into prompts (`task.py:28-42`). This is expected behavior for a CLI tool where the caller controls all inputs, not a vulnerability.

3. **Conflict detection severity** (`conflicts.py:84-92`): Always returns `severity: "hard"` regardless of LLM classification. Not a security issue, but the feature is incomplete.

---

## 5. Testing

### Overview

| Metric | Value |
|--------|-------|
| Test framework | pytest + pytest-asyncio |
| Test files | 9 |
| Test cases | 39 |
| Test LOC | ~500 |
| Async mode | Auto |
| Mock infrastructure | MockBackend, JsonMockBackend in conftest.py |

### Coverage by Module

| Test File | Module Tested | Tests |
|-----------|--------------|-------|
| `test_budget.py` | Budget circuit breaker | 4 |
| `test_cli.py` | CLI commands and output contracts | 4 |
| `test_execution.py` | Parallel/sequential mode resolution | 5 |
| `test_gather.py` | Result normalization and stats | 4 |
| `test_integration.py` | Full scatter-gather-synthesize pipeline | 2 |
| `test_quality.py` | Early stop and agreement detection | 6 |
| `test_synthesize.py` | Synthesis strategy routing | 3 |
| `test_task.py` | Task model validation | 5 |
| `test_weighted_merge.py` | Weighted merge algorithm | 6 |

### Gaps

- **No coverage reporting** - `pytest-cov` is not in dev dependencies. No way to measure untested paths.
- **Integration tests are minimal** - Only 2 tests cover the full pipeline.
- **Backend implementations untested directly** - Covered only via mocks. This is acceptable given they wrap SDK clients, but edge cases (network errors, rate limits) are not exercised.

---

## 6. CI/CD

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push to main, all PRs | Full quality gate |
| `publish.yml` | GitHub Release event | PyPI publication (Trusted Publishing) |
| `publish-testpypi.yml` | Manual dispatch | TestPyPI dry-run |

### CI Pipeline (`ci.yml`)

1. Checkout code
2. Setup Python (matrix: **3.10 + 3.13** on **Ubuntu + Windows**)
3. Install package with dev dependencies
4. Run pytest
5. Run Ruff lint + format checks
6. Run mypy type checking
7. CLI smoke tests (`--help`, `validate-task`)
8. Build package with `build`
9. Validate distribution with `twine check`
10. Smoke-test built package (Python 3.13 only)

**Assessment:** Comprehensive. Multi-platform matrix catches OS-specific issues (a recent Windows fix confirms this catches real bugs). Package build validation prevents broken releases.

---

## 7. Documentation

### Files

| File | Size | Purpose |
|------|------|---------|
| `README.md` | 10 KB | Install, quickstart, CLI/API examples, dev setup |
| `ARCHITECTURE.md` | 4.3 KB | Design philosophy, data flow, extension points, non-goals |
| `CONTRIBUTING.md` | 2.3 KB | Dev setup, contribution rules, what won't be merged |
| `RELEASE.md` | 2.1 KB | Release process, PyPI Trusted Publishing setup |
| `ROADMAP.md` | 2.1 KB | v1 priorities, longer-term ideas, non-goals |
| `SECURITY.md` | 565 B | Security policy, vulnerability reporting |
| `tasks/README.md` | - | Task library documentation |
| `benchmarks/README.md` | - | Benchmark documentation |
| `.github/PULL_REQUEST_TEMPLATE.md` | - | PR template |

**Assessment:** Unusually thorough for an alpha project. Architecture decisions are well-documented, contribution boundaries are explicit, and the release process is step-by-step.

### Missing

- **CHANGELOG.md** - No changelog file. Git history is clean but a changelog is standard practice before public release.

---

## 8. Dependencies

### Core (Required)

| Package | Version | Purpose |
|---------|---------|---------|
| httpx | >=0.27.0 | Async HTTP client (Ollama backend) |
| pydantic | >=2.0.0 | Data validation and serialization |
| rich | >=13.0.0 | Terminal formatting |
| click | >=8.0.0 | CLI framework |
| pyyaml | >=6.0 | YAML task parsing |

### Optional (Backend Extras)

| Package | Extra | Purpose |
|---------|-------|---------|
| anthropic | `[anthropic]` | >=0.40.0, Claude API |
| openai | `[openai]` | >=1.50.0, OpenAI-compatible APIs |

### Dev

| Package | Purpose |
|---------|---------|
| pytest >=8.0.0 | Testing |
| pytest-asyncio >=0.24.0 | Async test support |
| ruff >=0.8.0 | Linting and formatting |
| mypy >=1.13.0 | Static type checking |
| build >=1.2.2 | Package building |
| twine >=6.1.0 | Distribution validation |

### Notes

- **No lock file** - Acceptable for a library (applications pin, libraries don't).
- **Build system:** Hatchling (modern, PEP 517 compliant).
- **Python support:** 3.10, 3.11, 3.12, 3.13 (tested in CI for 3.10 and 3.13).

---

## 9. Issues & Recommendations

### Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | PDF file checked into repository | Low | Root directory |
| 2 | Conflict detection incomplete - always returns `severity: "hard"` | Low | `conflicts.py:84-92` |
| 3 | Voting strategy makes N extra LLM calls for label extraction | Low | `strategies/voting.py:53-62` |
| 4 | No test coverage reporting configured | Low | `pyproject.toml` |
| 5 | Benchmark results committed to repo could bloat wheel builds | Low | `benchmarks/results/` |
| 6 | No CHANGELOG.md | Low | Root directory |

### Recommendations

1. **Add the PDF to `.gitignore`** or move it to an external location. Binary files in Git repos increase clone size permanently.

2. **Add `pytest-cov`** to dev dependencies and configure a coverage target. This provides visibility into untested code paths and can be enforced in CI.

3. **Add a `CHANGELOG.md`** before the first public PyPI release. Even a simple keep-a-changelog format helps users track breaking changes.

4. **Exclude `benchmarks/results/`** from the wheel distribution via `pyproject.toml` build configuration to keep package size minimal.

5. **Consider batching voting label extraction** into a single LLM call to reduce cost and latency of the voting strategy.

6. **Finish or remove conflict detection** (`conflicts.py`). The current implementation is partially functional - it should either be completed with proper severity parsing or explicitly marked as experimental.

---

## 10. Summary

Broadside-AI is a well-engineered, narrowly-scoped tool that does one thing cleanly: parallel LLM scatter/gather with synthesis. For a v0.1.0 alpha, the project demonstrates mature engineering practices:

- **Architecture** is clean, documented, and deliberately constrained
- **Code quality** is enforced by strict tooling (mypy strict, Ruff)
- **Security** posture is solid with no identified vulnerabilities
- **CI/CD** is comprehensive with multi-platform testing
- **Documentation** is thorough and includes design rationale

The issues identified are all low-severity and relate to missing features or polish rather than fundamental problems. The project is well-positioned for a public release after addressing the recommendations above.
