# Benchmarks

Measures parallel scatter/gather vs sequential baseline on the same tasks, same model.

## Run the suite

### Ollama cloud (default, no API key)

```bash
python benchmarks/suite.py
python benchmarks/suite.py deepseek-v3.2:cloud
python benchmarks/suite.py qwen3.5:cloud
```

### Ollama local (needs GPU)

```bash
python benchmarks/suite.py gemma3:1b
```

### Anthropic

```bash
pip install broadside-ai[anthropic]
set ANTHROPIC_API_KEY=your-key-here
python benchmarks/suite.py --backend anthropic
python benchmarks/suite.py --backend anthropic --model claude-sonnet-4-20250514
```

### OpenAI

```bash
pip install broadside-ai[openai]
set OPENAI_API_KEY=your-key-here
python benchmarks/suite.py --backend openai
python benchmarks/suite.py --backend openai --model gpt-4o
```

The suite runs 5 task types (creative, analytical, classification, summarization, code review) and for each one:

1. Scatters to 3 agents in parallel, gathers, synthesizes
2. Runs the same task 3 times sequentially (the baseline)
3. Measures wall-clock time, token counts, and output diversity

## What you'll see

A live table that fills in as each task completes, showing speedup, cost, and diversity. Results are saved to `benchmarks/results/` in a timestamped folder:

```
benchmarks/results/
  nemotron-3-super_3agents_20260330_050000/
    results.json              # machine-readable, all tasks
    RESULTS.md                # formatted report, paste into docs
    creative_pitch/
      agent_1.txt             # raw scatter output
      agent_2.txt
      agent_3.txt
      sequential_baseline.txt # what you'd get without Broadside
      summary.json            # metrics for this task
    analytical_comparison/
      ...
```

## Metrics

**Speedup** = sequential wall-clock / parallel wall-clock. With 3 agents, theoretical max is 3.0x. Longer tasks benefit more.

**Cost vs 1 call** = total tokens (scatter + synthesis) / tokens for a single LLM call. This is what you actually pay for scatter/gather vs just prompting once. Scatter alone is ~3x; the LLM synthesis strategy adds more on top.

**Diversity** = average pairwise Jaccard distance (word-level). 0.0 = identical outputs, 1.0 = completely different. Higher means the scatter is producing genuinely different perspectives, not just rephrasing the same answer.

## Contributing benchmarks

Run the suite against a different model and open a PR with your results. The more models and hardware configurations represented, the more useful the benchmarks are.

```bash
python benchmarks/suite.py qwen3.5:cloud
```
