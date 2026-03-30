# Broadside-AI

**2.52x faster than sequential on Claude Sonnet 4** — code review hits 2.94x (near the 3.0x theoretical max with 3 agents). Real benchmarks, real numbers. [See full results below.](#benchmarks)

Hierarchical agent frameworks fail 41–86.7% of the time, with coordination breakdowns as the single largest failure category at 36.9%. Broadside takes a different approach: scatter your task to N parallel agents, gather the results, synthesize. No org charts, no inter-agent messaging, no coordination overhead.

## Install

```bash
pip install broadside-ai
```

**From source** (if you cloned the repo):

```bash
git clone https://github.com/HuginnIndustries/Broadside-AI.git
cd Broadside-AI
pip install -e .
```

The `-e` flag installs in editable mode — code changes take effect immediately without reinstalling.

## Quick Start

Install [Ollama](https://ollama.ai), sign in for free cloud access, and run:

```bash
pip install broadside-ai
python -m broadside_ai run --prompt "Write a pitch for a dotfile manager" --n 3
```

The `--n 3` means "scatter to 3 parallel agents." Research shows 3–5 is the sweet spot — beyond that, output quality plateaus while costs scale linearly (DeepMind 2025).

The default model is `nemotron-3-super:cloud`, which runs on Ollama's cloud (free tier, no GPU needed). To use a different cloud model:

```bash
python -m broadside_ai run --prompt "Write a pitch for a dotfile manager" --n 3 --model gpt-oss:120b-cloud
```

**Have a GPU?** Pull a local model and skip the cloud entirely:

```bash
ollama pull gemma3:1b
python -m broadside_ai run --prompt "Write a pitch for a dotfile manager" --n 3 --model gemma3:1b
```

### Python API

```python
from broadside_ai import Task, run_sync

task = Task(
    prompt="Write a one-paragraph pitch for a CLI tool that helps developers manage dotfiles.",
)

result = run_sync(task, n=3, backend="ollama")
print(result.result)
```

For async code, use `run()` directly:

```python
from broadside_ai import Task, run

result = await run(task, n=3, backend="ollama")
```

## How It Works

```
Task → Scatter (N parallel agents) → Gather → Synthesize → Human checkpoint
```

Each agent runs independently — no shared state, no waiting on other agents. The synthesis step identifies consensus, flags outliers, and produces a single actionable output. The gather step is the natural point for human review.

Results are saved to `broadside_ai_output/` organized by model and topic for easy comparison across runs.

## Synthesis Strategies

Broadside ships with three strategies for collapsing N outputs into one:

| Strategy        | Best for        | How it works                                                                                        |
| --------------- | --------------- | --------------------------------------------------------------------------------------------------- |
| `llm` (default) | General tasks   | Sends all outputs to a model that identifies consensus, flags outliers, and writes a unified answer |
| `consensus`     | Knowledge tasks | Extracts agreed-upon claims, disagreements, and unique insights                                     |
| `voting`        | Reasoning tasks | Each output votes on an answer; majority wins                                                       |

Note: the default `llm` strategy calls the model one additional time for synthesis. In practice, synthesis can use as many tokens as the scatter itself. For cost-sensitive workloads, `consensus` or `voting` are lighter alternatives.

```bash
python -m broadside_ai run --prompt "Your task" --n 3 --synthesis voting
```

## Backends

### Ollama (default — no API key)

Ollama is the default backend and ships with the base install. Sign in to the [Ollama](https://ollama.ai) app for free cloud access — no GPU required.

```bash
python -m broadside_ai run --prompt "Your task" --n 3
```

All models run in parallel by default. Use `--sequential` if your hardware can't handle concurrent inference.

Available cloud models:

```
nemotron-3-super:cloud          (default)
mistral-large-3:675b-cloud
deepseek-v3.2:cloud
qwen3.5:cloud
qwen3.5:397b-cloud
qwen3-coder-next:cloud
kimi-k2.5:cloud
gpt-oss:120b-cloud
gpt-oss:20b-cloud
minimax-m2.7:cloud
cogito-2.1:671b-cloud
gemini-3-flash-preview:cloud
```

Full list: `ollama list --cloud`

Have a GPU? Pull a local model instead:

```bash
ollama pull gemma3:1b
python -m broadside_ai run --prompt "Your task" --n 3 --model gemma3:1b
```

### Anthropic

Uses the Anthropic Messages API. Default model: `claude-sonnet-4-20250514`.

```bash
pip install broadside-ai[anthropic]
```

Set your API key:

```bash
# Windows (Command Prompt)
set ANTHROPIC_API_KEY=your-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-key-here"

# macOS / Linux
export ANTHROPIC_API_KEY=your-key-here
```

```bash
python -m broadside_ai run --prompt "Your task" --n 3 --backend anthropic
```

Or specify a model:

```bash
python -m broadside_ai run --prompt "Your task" --n 3 --backend anthropic --model claude-sonnet-4-20250514
```

### OpenAI (and compatible APIs)

Works with OpenAI, Azure OpenAI, and any API that implements the OpenAI chat completions interface (vLLM, Together, Groq, etc.). Default model: `gpt-4o-mini`.

```bash
pip install broadside-ai[openai]
```

Set your API key:

```bash
# Windows (Command Prompt)
set OPENAI_API_KEY=your-key-here

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-key-here"

# macOS / Linux
export OPENAI_API_KEY=your-key-here
```

```bash
python -m broadside_ai run --prompt "Your task" --n 3 --backend openai
```

For OpenAI-compatible providers, pass `--model` and set `OPENAI_BASE_URL` the same way to point at your provider.

### All backends at once

```bash
pip install broadside-ai[all]
```

## Benchmarks

Real numbers, 3 agents, parallel vs sequential on the same tasks:

### Anthropic (claude-sonnet-4-20250514)

| Task                  | Parallel | Sequential | Speedup   | Cost vs 1 call | Diversity |
| --------------------- | -------- | ---------- | --------- | -------------- | --------- |
| creative_pitch        | 8.4s     | 19.8s      | 2.36x     | 8.6x           | 0.767     |
| analytical_comparison | 35.3s    | 78.8s      | 2.23x     | 6.8x           | 0.734     |
| classification        | 4.6s     | 11.4s      | 2.48x     | 6.5x           | 0.640     |
| summarization         | 10.7s    | 27.9s      | 2.59x     | 7.2x           | 0.735     |
| code_review           | 17.3s    | 50.8s      | 2.94x     | 5.4x           | 0.651     |
| **Average**           |          |            | **2.52x** | **6.9x**       | **0.705** |

### Ollama Cloud (nemotron-3-super:cloud)

| Task                  | Parallel | Sequential | Speedup   | Cost vs 1 call | Diversity |
| --------------------- | -------- | ---------- | --------- | -------------- | --------- |
| creative_pitch        | 6.3s     | 30.1s      | 4.80x     | 10.1x          | 0.827     |
| analytical_comparison | 56.9s    | 54.4s      | 0.96x     | 7.1x           | 0.764     |
| classification        | 4.0s     | 13.8s      | 3.45x     | 7.0x           | 0.603     |
| summarization         | 10.3s    | 11.9s      | 1.15x     | 8.9x           | 0.801     |
| code_review           | 108.6s   | 102.3s     | 0.94x     | 7.3x           | 0.737     |
| **Average**           |          |            | **2.26x** | **8.1x**       | **0.746** |

### Ollama Cloud (deepseek-v3.2:cloud)

| Task                  | Parallel | Sequential | Speedup   | Cost vs 1 call | Diversity |
| --------------------- | -------- | ---------- | --------- | -------------- | --------- |
| creative_pitch        | 16.8s    | 28.3s      | 1.68x     | 7.6x           | 0.840     |
| analytical_comparison | 70.5s    | 119.7s     | 1.70x     | 4.6x           | 0.731     |
| classification        | 22.0s    | 32.7s      | 1.48x     | 4.3x           | 0.600     |
| summarization         | 29.6s    | 26.8s      | 0.91x     | 6.6x           | 0.812     |
| code_review           | 115.0s   | 175.3s     | 1.52x     | 5.2x           | 0.674     |
| **Average**           |          |            | **1.46x** | **5.7x**       | **0.731** |

### Ollama Local (gemma3:1b)

> Tested on: Intel i7-1165G7 @ 2.80GHz, 16GB RAM, no discrete GPU

| Task                  | Parallel | Sequential | Speedup   | Cost vs 1 call | Diversity |
| --------------------- | -------- | ---------- | --------- | -------------- | --------- |
| creative_pitch        | 17.3s    | 16.1s      | 0.93x     | 9.2x           | 0.755     |
| analytical_comparison | 158.1s   | 190.3s     | 1.20x     | 6.3x           | 0.732     |
| classification        | 12.0s    | 10.4s      | 0.87x     | 7.1x           | 0.750     |
| summarization         | 30.6s    | 42.9s      | 1.40x     | 6.8x           | 0.803     |
| code_review           | 187.9s   | 182.6s     | 0.97x     | 6.6x           | 0.735     |
| **Average**           |          |            | **1.07x** | **7.2x**       | **0.755** |

Local inference on modest hardware still shows gains on longer tasks (1.40x summarization, 1.20x analytical). Short tasks lose to overhead. Better hardware = better parallelism — this is the floor, not the ceiling.

In early testing, Anthropic showed the most consistent speedups — every task benefited from parallelism, with code review hitting 2.94x (near the 3.0x theoretical max). Ollama cloud results (free tier) were more variable — Nemotron showed strong gains on short tasks while DeepSeek was more moderate but consistent. Local inference on modest hardware (no discrete GPU) showed the smallest gains — parallelism helps most when the bottleneck is network latency, not local compute.
