"""Broadside quick start — runs against Ollama, no API keys needed.

Prerequisites:
    pip install broadside
    ollama pull llama3.2
    ollama serve  (if not already running)
"""

import asyncio
from broadside import Task, run

task = Task(
    prompt="Write a one-paragraph pitch for a CLI tool that helps developers manage dotfiles.",
)

result = asyncio.run(run(task, n=3, backend="ollama"))

print(f"Synthesized from {result.gather.n_completed} agents "
      f"({result.total_tokens():,} tokens, {result.gather.wall_clock_ms:.0f}ms):\n")
print(result.result)
