# Benchmarks

The benchmark suite compares Broadside-AI scatter/gather against a sequential
baseline on the same task and model.

## Run the suite

### Ollama cloud

```bash
ollama signin
ollama pull nemotron-3-super:cloud
python benchmarks/suite.py
python benchmarks/suite.py deepseek-v3.2:cloud
```

### Ollama local

```bash
ollama pull gemma3:1b
python benchmarks/suite.py gemma3:1b
```

### Anthropic

```bash
pip install broadside-ai[anthropic]
export ANTHROPIC_API_KEY=your-key-here
python benchmarks/suite.py --backend anthropic
```

### OpenAI

```bash
pip install broadside-ai[openai]
export OPENAI_API_KEY=your-key-here
python benchmarks/suite.py --backend openai --model gpt-4o-mini
```

## What it measures

For each task, the suite runs:

1. one 3-agent scatter/gather execution
2. the same task 3 times sequentially
3. a comparison of latency, token cost, and output diversity

## Output layout

```text
benchmarks/results/
  {model}_{n}agents_{timestamp}/
    results.json
    RESULTS.md
    creative_pitch/
    analytical_comparison/
    classification/
    summarization/
    code_review/
```

Each task directory contains raw scatter outputs, a sequential baseline sample,
and a machine-readable summary.

## Metrics

- `Speedup`: sequential wall-clock / parallel wall-clock
- `Cost vs 1 call`: total scatter+synthesis tokens / one single-call baseline
- `Diversity`: average pairwise Jaccard distance across scatter outputs

## Committed snapshots

This repository intentionally keeps selected benchmark result snapshots under
`benchmarks/results/` so README claims can be audited against real runs.
