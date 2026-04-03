"""Broadside-AI quick start - runs against Ollama, no API keys needed.

Before running:
    1. Install Broadside-AI:  pip install broadside-ai
    2. Install Ollama:        https://ollama.com
    3. Sign in:               ollama signin
    4. Enable the default cloud model:
                              ollama pull nemotron-3-super:cloud

Default model is nemotron-3-super:cloud (runs on Ollama cloud, no GPU needed).
Have a GPU? Use a local model instead:
    result = run_sync(task, n=3, backend="ollama", backend_kwargs={"model": "gemma3:1b"})

Run with:
    python examples/quickstart.py
"""

from broadside_ai import Task, run_sync

task = Task(
    prompt="Write a one-paragraph pitch for a CLI tool that helps developers manage dotfiles.",
)

result = run_sync(task, n=3, backend="ollama")

print(result.result)
