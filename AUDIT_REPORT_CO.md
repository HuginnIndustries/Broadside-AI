# Broadside-AI Audit Report

Audit date: 2026-04-03

## Executive summary

Broadside-AI is a well-scoped, CLI-first Python project with a clear product thesis, a readable core pipeline, solid packaging hygiene, and working quality gates. The repository currently presents as release-aware pre-1.0 software rather than a rough prototype. During this audit, the local quality gates all passed: `py -3 -m pytest tests -q` reported `39 passed`, `py -3 -m ruff check src tests benchmarks examples` passed cleanly, `py -3 -m ruff format --check src tests benchmarks examples` reported files already formatted, `py -3 -m mypy src/broadside_ai` succeeded with no issues, and `py -3 -m build` produced both sdist and wheel artifacts successfully.

The main concerns are not general code quality problems. They are contract-level mismatches between the behavior documented for automation users and the behavior actually enforced in the runtime. The three most important findings are:

1. Parallel budget enforcement behaves like a soft cap, not the hard upper bound described in architecture and exception messaging.
2. `output_schema` currently drives JSON parsing and prompting, but not true schema validation of types or extra fields.
3. `weighted_merge` list behavior does not fully match the README claim of "majority presence" in tie cases.

Overall assessment: strong project foundation, good release posture, and good evaluator-facing documentation, but some machine-contract claims should be tightened before this should be treated as fully trustworthy infrastructure for strict automation pipelines.

## Project overview

Broadside-AI positions itself as a narrow scatter/gather engine for CLI automation rather than a general agent framework. The README defines that boundary clearly and consistently: no inter-agent messaging, no DAG workflows, no persistent multi-step state, and no role hierarchy (`README.md:3-16`). The architecture document reinforces the same thesis and keeps the dominant flow small and understandable: `Task -> Scatter -> Gather -> Synthesize -> Output` (`ARCHITECTURE.md:14-25`).

This focus is a strength. The repo is small, cohesive, and aligned around a single product shape:

- Primary package: `src/broadside_ai/`
- Focused docs: `README.md`, `ARCHITECTURE.md`, `RELEASE.md`, `SECURITY.md`, `ROADMAP.md`
- Example task library: `tasks/`
- Benchmarks with committed snapshots: `benchmarks/`
- Test suite centered on public behavior: `tests/`

The project is already set up like something intended to ship, not just to demonstrate ideas.

## Architecture review

### What is working well

- The architecture is coherent and intentionally narrow. The system explicitly avoids workflow-engine complexity and preserves branch independence (`ARCHITECTURE.md:3-12`, `ARCHITECTURE.md:25-27`).
- The function-first API is appropriate for the product shape. Exposing `scatter()`, `gather()`, `synthesize()`, and `run()` keeps the public surface small and easy to understand (`ARCHITECTURE.md:28-42`).
- The backend abstraction is minimal and healthy. Backends only need `complete()` and `name()`, which is enough for the product without introducing lifecycle complexity (`ARCHITECTURE.md:70-79`).
- The CLI contract is thoughtfully designed for scripts. `run` defaults to stdout, artifacts are opt-in, and a JSON mode is available for automation (`ARCHITECTURE.md:44-55`, `src/broadside_ai/cli.py:47-72`, `src/broadside_ai/cli.py:82-103`).
- Execution defaults are sensible. The code distinguishes between cloud and local Ollama usage, defaulting cloud backends to parallel execution and local Ollama to sequential (`ARCHITECTURE.md:81-89`, `src/broadside_ai/execution.py` reviewed during audit).

### Risks or gaps

- The documented budget model is stronger than the actual runtime behavior. The architecture says `ScatterBudget` provides an upper bound on token usage (`ARCHITECTURE.md:91-97`), but parallel scatter launches all branches before token usage is recorded (`src/broadside_ai/scatter.py:41-67`).
- Structured-output handling is described as part of the main automation path (`ARCHITECTURE.md:57-68`), but the runtime only parses JSON dictionaries rather than validating them against `output_schema` (`src/broadside_ai/gather.py:52-60`, `src/broadside_ai/task.py:19-24`).
- The architecture is intentionally simple, but that simplicity also means some higher-trust contracts are currently implemented as conventions rather than enforced invariants.

### Evidence

- Product boundary and flow: `ARCHITECTURE.md:3-12`, `ARCHITECTURE.md:14-25`
- Function-first API: `ARCHITECTURE.md:28-42`
- CLI contract: `ARCHITECTURE.md:44-55`, `src/broadside_ai/cli.py:47-72`
- Budget claim: `ARCHITECTURE.md:91-97`
- Parallel scatter implementation: `src/broadside_ai/scatter.py:41-67`

## Code quality review

### What is working well

- The core code is small and readable. The main CLI and orchestration paths are easy to follow, with limited indirection.
- Type hygiene is good for a pre-1.0 project. The repository uses strict mypy mode (`pyproject.toml:93-99`) and passed `py -3 -m mypy src/broadside_ai` during this audit.
- Modules are sensibly separated by responsibility: task definition, scatter, gather, synthesis, backends, validation, benchmarking, and CLI.
- The package surface is clean and predictable. `pyproject.toml` defines a straightforward console script, base dependencies, extras, and build exclusions (`pyproject.toml:28-78`).

### Risks or gaps

- Some code and docstrings imply guarantees that the implementation does not enforce. The clearest case is `Task.output_schema`, which is described as "Used to validate agent responses" (`src/broadside_ai/task.py:19-24`) even though gather only parses JSON objects (`src/broadside_ai/gather.py:52-60`).
- `weighted_merge` accepts and merges any parsed dictionary keys, including keys not declared in `output_schema`, because the schema parameter is not used in the merge logic (`src/broadside_ai/strategies/weighted_merge.py:12-40`, `src/broadside_ai/strategies/weighted_merge.py:58-82`).
- Budget accounting is thread-safe in isolation (`src/broadside_ai/budget.py:24-56`) but not protective enough to uphold a true hard limit in parallel mode because accounting happens after completions return (`src/broadside_ai/scatter.py:52-56`).

### Evidence

- Strict typing: `pyproject.toml:93-99`
- CLI payload model: `src/broadside_ai/cli.py:33-72`
- Output schema description: `src/broadside_ai/task.py:19-24`
- Gather parsing behavior: `src/broadside_ai/gather.py:52-60`
- Weighted merge ignoring schema: `src/broadside_ai/strategies/weighted_merge.py:12-40`, `src/broadside_ai/strategies/weighted_merge.py:58-82`

## Security review

### What is working well

- The repository includes a clear security policy with private disclosure instructions and a supported-version statement (`SECURITY.md:1-26`).
- Provider credentials are expected from environment variables rather than checked into config files. Anthropic and OpenAI backends explicitly require `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` (`src/broadside_ai/backends/anthropic.py:25-45`, `src/broadside_ai/backends/openai.py:25-49`).
- The base dependency set is small and appropriate for the product (`pyproject.toml:28-48`).
- Build exclusions intentionally omit caches, benchmark result snapshots, and generated artifacts from published distributions (`pyproject.toml:63-78`), reducing accidental package leakage.
- Ollama defaults to local-first behavior with explicit helpful connection errors (`src/broadside_ai/backends/ollama.py:13-29`, `src/broadside_ai/backends/ollama.py:41-66`).

### Risks or gaps

- There is no dependency-vulnerability scanning or SBOM generation in CI. The CI workflow runs tests, Ruff, mypy, build, `twine check`, and wheel smoke tests, but no `pip-audit`, `safety`, or similar step (`.github/workflows/ci.yml:25-52`).
- Prompt and context content are forwarded directly to providers without redaction or sensitive-data screening. This is not inherently wrong for a CLI tool, but it is an important trust boundary for users handling proprietary material.
- The project does not yet offer explicit safeguards around prompt injection or untrusted context in structured tasks. Given the product's purpose, some guidance in docs would help.
- Security posture is adequate for an alpha CLI tool, but not yet especially mature beyond credential handling and disclosure process.

### Evidence

- Security policy: `SECURITY.md:1-26`
- Anthropic key handling: `src/broadside_ai/backends/anthropic.py:34-45`
- OpenAI key handling: `src/broadside_ai/backends/openai.py:35-49`
- Minimal dependency set and package exclusions: `pyproject.toml:28-78`
- CI workflow scope: `.github/workflows/ci.yml:25-52`

## Testing review

### What is working well

- The current suite exercises the main product paths: CLI behavior, execution defaults, gather behavior, budget primitives, early stop behavior, synthesis, integration, and weighted merge.
- Test feedback is fast. During this audit, `py -3 -m pytest tests -q` completed successfully with `39 passed in 1.07s`.
- The test suite does a good job of validating public contracts rather than only internals. Examples include CLI JSON output, validate-task behavior, and end-to-end synthesis (`tests/test_cli.py`, `tests/test_integration.py:12-40`).
- Weighted merge has direct tests for numeric aggregation, confidence weighting, list merging, and LLM fallback (`tests/test_weighted_merge.py:33-111`).

### Risks or gaps

- The budget tests validate the `ScatterBudget` class in isolation, but they do not validate the actual behavior of parallel `scatter()` under a low token budget (`tests/test_budget.py:8-40`).
- The weighted-merge tests cover the happy path but do not cover schema-invalid JSON, extra fields, or two-way list ties (`tests/test_weighted_merge.py:33-111`).
- There is no coverage reporting or minimum threshold enforced in CI (`.github/workflows/ci.yml:28-52`).
- The existing integration coverage confirms that weighted merge works when upstream JSON is well-formed, but not when it is malformed or partially invalid (`tests/test_integration.py:20-40`).

### Evidence

- Budget unit tests: `tests/test_budget.py:8-40`
- Weighted merge tests: `tests/test_weighted_merge.py:33-111`
- Integration test scope: `tests/test_integration.py:12-40`
- CI test scope: `.github/workflows/ci.yml:28-52`
- Observed local result:

```text
py -3 -m pytest tests -q
.......................................                                  [100%]
39 passed in 1.07s
```

## CI/CD and release review

### What is working well

- CI is practical and release-oriented. It runs on both Ubuntu and Windows across Python 3.10 and 3.13 (`.github/workflows/ci.yml:9-16`).
- The workflow covers tests, lint, format, typing, CLI smoke checks, build, metadata validation, and built-wheel smoke testing (`.github/workflows/ci.yml:25-52`).
- Release documentation is unusually thorough for a project at this stage. It includes local release gates, pre-publish review, TestPyPI guidance, publish flow, and post-publish verification (`RELEASE.md:18-87`).
- The publish workflow follows a good two-stage pattern: build and validate artifacts first, then publish via PyPI trusted publishing (`.github/workflows/publish.yml:8-56`).
- The built-wheel smoke script validates both console-script and module entrypoints in a clean venv (`tools/smoke_dist_install.py:37-50`).

### Risks or gaps

- CI is strong on packaging correctness but currently weaker on supply-chain and dependency audit checks.
- Publish automation assumes release publication rather than enforcing any additional post-build policy checks beyond what build/test already did.
- Release docs explicitly warn that `README.md` must match runtime behavior (`RELEASE.md:45-54`), and the current structured-output and budget issues show why that warning matters.

### Evidence

- CI matrix and steps: `.github/workflows/ci.yml:9-52`
- Release checklist: `RELEASE.md:18-54`, `RELEASE.md:66-87`
- Publish workflow: `.github/workflows/publish.yml:8-56`
- Clean-venv smoke test: `tools/smoke_dist_install.py:37-50`
- Observed local results:

```text
py -3 -m ruff check src tests benchmarks examples
All checks passed!

py -3 -m ruff format --check src tests benchmarks examples
37 files already formatted

py -3 -m mypy src/broadside_ai
Success: no issues found in 24 source files

py -3 -m build
Successfully built broadside_ai-0.1.0.tar.gz and broadside_ai-0.1.0-py3-none-any.whl
```

## Documentation review

### What is working well

- Documentation quality is a strong point. The README is clear about product scope, install paths, workflows, structured output, and JSON automation use cases (`README.md:1-40`, `README.md:223-325`).
- Architecture and release docs are aligned with the project's intended audience: users automating CLI workflows and maintainers preparing packages for distribution.
- The repository includes supporting docs beyond the minimum expected set: contributing guidance, roadmap, benchmarks, release process, and security policy.

### Risks or gaps

- The most important documentation issue is doc/code drift, not lack of content.
- The README says `weighted_merge` merges lists by majority presence and that `confidence` is only metadata (`README.md:288-294`), but implementation details can include tied list items and accept undeclared keys during merge (`src/broadside_ai/strategies/weighted_merge.py:58-118`).
- The architecture doc says budget provides an upper bound (`ARCHITECTURE.md:91-97`), which is stronger than what parallel execution currently guarantees (`src/broadside_ai/scatter.py:63-67`, `src/broadside_ai/budget.py:35-40`).
- `Task.output_schema` is described as validation-oriented in code comments (`src/broadside_ai/task.py:19-24`) and implied similarly in docs, but runtime enforcement is parsing-only (`src/broadside_ai/gather.py:52-60`).

### Evidence

- README scope and automation framing: `README.md:1-40`, `README.md:223-325`
- Architecture claims: `ARCHITECTURE.md:44-68`, `ARCHITECTURE.md:91-97`
- Weighted merge docs: `README.md:288-294`
- Weighted merge code: `src/broadside_ai/strategies/weighted_merge.py:58-118`
- Schema description vs runtime: `src/broadside_ai/task.py:19-24`, `src/broadside_ai/gather.py:52-60`

## Dependencies and packaging review

### What is working well

- The dependency set is lean: `httpx`, `pydantic`, `rich`, `click`, and `pyyaml` in the base install, with Anthropic/OpenAI separated into extras (`pyproject.toml:28-48`).
- Packaging metadata is complete enough for an alpha release: project URLs, supported Python versions, console script, and build backend are all defined (`pyproject.toml:1-58`).
- Build exclusions are thoughtful and reduce the chance of shipping transient or bulky non-package files (`pyproject.toml:63-78`).
- The project successfully builds both sdist and wheel artifacts locally.

### Risks or gaps

- Dependencies use lower bounds but no upper bounds, and there is no lockfile. This is common for libraries but increases exposure to upstream breaking changes.
- Optional dependency imports are handled cleanly, but compatibility will depend on continued API stability in provider SDKs.
- There is no automated dependency-review or vulnerability-scanning gate in CI.

### Evidence

- Build and dependency config: `pyproject.toml:1-99`
- Publish and smoke build verification: `.github/workflows/ci.yml:44-52`, `tools/smoke_dist_install.py:30-50`

## Prioritized findings

### P1: Parallel budget enforcement is softer than documented

Impact: High for automation users who interpret `max_tokens` as a hard safety boundary for provider cost.

The architecture document says `ScatterBudget` provides an upper bound on token usage (`ARCHITECTURE.md:91-97`), and the exception text says remaining branches are cancelled (`src/broadside_ai/budget.py:18-20`). In practice, parallel scatter instantiates all branch tasks before any token usage is recorded (`src/broadside_ai/scatter.py:63-67`). That means a budget exceed can be detected only after multiple calls have already been launched.

Audit reproduction:

```text
Observed with a local reproduction backend:
{'completed_results': 1, 'budget_used': 300, 'calls': 3}
```

This was produced with a 150-token budget and three parallel branches returning 100 tokens each. The runtime kept the result list short, but actual recorded usage still doubled the configured cap.

### P1: `output_schema` is parse-oriented, not validation-oriented

Impact: High for downstream tools relying on typed or schema-constrained structured output.

`Task.output_schema` is described as validating responses (`src/broadside_ai/task.py:19-24`), but gather only attempts to parse a JSON object (`src/broadside_ai/gather.py:52-60`). `weighted_merge` then merges any parsed dictionaries and ignores its `output_schema` argument (`src/broadside_ai/strategies/weighted_merge.py:12-40`).

Audit reproduction:

```text
Observed with schema {'label': 'string', 'tags': 'list'}:
{
  'n_parsed': 2,
  'parsed_outputs': [
    {'label': 123, 'tags': ['a'], 'unexpected': 'x'},
    {'label': 'spam', 'tags': ['b']}
  ],
  'merged': {'label': '123', 'tags': ['a', 'b'], 'unexpected': 'x'}
}
```

This shows three problems:

- wrong types are accepted as parsed
- undeclared keys are accepted and merged
- merge output can drift away from the declared schema

### P2: List merging does not strictly implement majority presence

Impact: Medium, because it changes the semantics of structured aggregation in ambiguous cases.

The README claims list merging works by majority presence (`README.md:288-294`). The implementation uses `counts[key] >= len(values) / 2` (`src/broadside_ai/strategies/weighted_merge.py:108-117`), which includes tied items for even-numbered result sets.

Audit reproduction:

```text
_merge_lists([['a'], ['b']]) -> ['a', 'b']
```

This is not a strict majority. It is a "half or more" rule.

### P3: Test coverage is good for healthy-path behavior but thin on contract regressions

Impact: Medium, because the current suite gives confidence in general stability but not in the exact contracts most important to automation users.

The current tests are strong enough to keep the project stable day-to-day, but they do not yet pin the most important contract mismatches found in this audit. In particular, there is no regression test for parallel budget overshoot, no test proving extra schema keys are rejected, and no tie-case test for list merging (`tests/test_budget.py:8-40`, `tests/test_weighted_merge.py:33-111`).

## Actionable recommendations

### Immediate contract fixes

1. Reclassify budget behavior honestly.
   - Either implement true hard-cap semantics or update docs and error messaging to describe best-effort/soft-cap behavior in parallel mode.
   - Minimum acceptable fix: align `ARCHITECTURE.md`, README wording, and `BudgetExceeded` messaging with actual runtime semantics.

2. Add real schema validation for structured outputs.
   - Validate types and reject unexpected keys after JSON parse.
   - Exclude invalid parsed outputs from `n_parsed`, early-stop structured agreement checks, and `weighted_merge`.

3. Bring list merge semantics in line with documentation.
   - If "majority presence" is the intended contract, change the threshold to strict majority.
   - If current behavior is intentional, update docs to say "half or more" instead.

### Near-term reliability improvements

1. Add regression tests for the identified contract issues.
   - Parallel scatter under a low budget
   - Schema-invalid structured outputs
   - Extra keys in structured outputs
   - Two-way list ties in weighted merge

2. Extend CI with a dependency-audit step.
   - `pip-audit` is the obvious starting point for this repository.

3. Strengthen machine-readable status reporting.
   - Consider including whether structured outputs were fully validated, partially valid, or fell back to freeform synthesis in JSON output.

4. Add lightweight security guidance to the README.
   - Warn users that prompts and context may be sent directly to third-party providers.
   - Recommend caution with secrets, proprietary code, and sensitive datasets.

### Lower-priority polish and future enhancements

1. Add coverage reporting or at least track coverage locally in CI artifacts.
2. Consider documenting provider timeout/retry expectations more explicitly.
3. Add a small compatibility matrix for supported provider SDK versions as the project matures.
4. If structured outputs become a core selling point, consider moving from "JSON-schema-like dict" wording to a fully defined internal schema contract.

## Verification appendix

### Workspace and branch state before writing

```text
git branch --show-current
codex/Audit

git status --short
(no output)

Test-Path AUDIT_REPORT_CO.md
False
```

### Quality gates observed during this audit

```text
py -3 -m pytest tests -q
.......................................                                  [100%]
39 passed in 1.07s
```

```text
py -3 -m ruff check src tests benchmarks examples
All checks passed!
```

```text
py -3 -m ruff format --check src tests benchmarks examples
37 files already formatted
```

```text
py -3 -m mypy src/broadside_ai
Success: no issues found in 24 source files
```

```text
py -3 -m build
Successfully built broadside_ai-0.1.0.tar.gz and broadside_ai-0.1.0-py3-none-any.whl
```

### Files reviewed directly during the audit

- `README.md`
- `ARCHITECTURE.md`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/publish.yml`
- `RELEASE.md`
- `SECURITY.md`
- `src/broadside_ai/cli.py`
- `src/broadside_ai/scatter.py`
- `src/broadside_ai/gather.py`
- `src/broadside_ai/task.py`
- `src/broadside_ai/budget.py`
- `src/broadside_ai/strategies/weighted_merge.py`
- `src/broadside_ai/backends/ollama.py`
- `src/broadside_ai/backends/anthropic.py`
- `src/broadside_ai/backends/openai.py`
- `tools/smoke_dist_install.py`
- `tests/test_budget.py`
- `tests/test_weighted_merge.py`
- `tests/test_integration.py`

### Scope note

This audit was evidence-based and static-analysis-heavy, with local quality gates and targeted runtime reproductions. It did not include live calls to Anthropic, OpenAI, or Ollama services, external dependency vulnerability scanning, or dynamic fuzz testing against untrusted prompts.
