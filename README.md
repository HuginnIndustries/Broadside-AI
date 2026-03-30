# Broadside

**A Python framework for parallel LLM agent orchestration using scatter/gather instead of hierarchy.**

Hierarchical agent frameworks fail 41–86.7% of the time, with coordination breakdowns as the single largest failure category at 36.9%. Broadside takes a different approach: scatter your task to N parallel agents, gather the results, synthesize. No org charts, no inter-agent messaging, no coordination overhead.

## Install

```bash
pip install broadside
```

## Quick Start

Requires [Ollama](https://ollama.ai) running locally (`ollama pull llama3.2 && ollama serve`):

```python
import asyncio
from broadside import Task, run

task = Task(
    prompt="Write a one-paragraph pitch for a CLI tool that helps developers manage dotfiles.",
)

result = asyncio.run(run(task, n=3, backend="ollama"))

print(f"Synthesized from {result.gather.n_completed} agents "
      f"({result.total_tokens():,} tokens, {result.gather.wall_clock_ms:.0f}ms):\n")
print(result.result)
```

Or from the CLI:

```bash
broadside run --prompt "Write a pitch for a dotfile manager" --n 3
```

## How It Works

```
Task → Scatter (N parallel agents) → Gather → Synthesize → Human checkpoint
```

Each agent runs independently — no shared state, no waiting on other agents. The synthesis step identifies consensus, flags outliers, and produces a single actionable output. The gather step is the natural point for human review.

## Backends

| Backend | Install | API Key Required |
|---------|---------|-----------------|
| Ollama | `pip install broadside` | No |
| Anthropic | `pip install broadside[anthropic]` | Yes |
| OpenAI | `pip install broadside[openai]` | Yes |

## When To Use Broadside

**Good fit:** bounded tasks with verifiable outputs, problems where variance is informative (creative, analytical, research), any situation where you'd manually prompt an LLM multiple times and compare.

**Poor fit:** long-running stateful tasks, real-time inter-agent coordination, single-correct-answer problems that can be cheaply verified.

## License

MIT
