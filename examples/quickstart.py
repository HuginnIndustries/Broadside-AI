"""Broadside quick start — runs against Ollama, no API keys needed.

Before running:
    1. Install Broadside:  pip install broadside
    2. Install Ollama:     https://ollama.ai
    3. Sign in to the Ollama app (free cloud access)

Default model is nemotron-3-super:cloud (runs on Ollama's cloud, no GPU needed).
Have a GPU? Use a local model instead:
    result = run_sync(task, n=3, backend="ollama", backend_kwargs={"model": "gemma3:1b"})

Run with:
    python examples/quickstart.py
"""

from broadside import Task, run_sync

# Define what you want — be specific about the output
task = Task(
    prompt="Compare the tactics of Nelson at Trafalgar vs Yi Sun-sin at Myeongnyang.",
)

# Scatter to 3 agents, gather results, synthesize into one answer
result = run_sync(task, n=3, backend="ollama")

print(result.result)
