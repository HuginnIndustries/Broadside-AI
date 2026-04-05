# Changelog

## 0.1.0

Initial public release.

- CLI-first scatter/gather with `broadside-ai run` and `broadside-ai validate-task`
- Backends: Ollama (base install), Anthropic, OpenAI-compatible
- Synthesis strategies: llm, consensus, voting, weighted_merge
- Structured output parsing with `output_schema`
- Early-stop controls (`--early-stop`, `--agreement`)
- Stable JSON output mode (`--json-output`, schema version 1)
- Context file support (`--context-file`)
- Python API: `run()`, `run_sync()`, `Task`, `EarlyStop`
- Task library with community-contributed YAML definitions
- Benchmark suite with committed result snapshots
