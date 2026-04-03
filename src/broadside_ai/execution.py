"""Execution mode helpers for Broadside-AI."""

from __future__ import annotations

from typing import Any


def is_ollama_cloud_model(model: str) -> bool:
    """Return True when the Ollama model name targets cloud execution."""
    normalized = model.strip().lower()
    return normalized.endswith(":cloud") or normalized.endswith("-cloud")


def resolve_parallel_mode(
    backend: str,
    backend_kwargs: dict[str, Any] | None = None,
    explicit: bool | None = None,
) -> bool:
    """Resolve whether a run should execute in parallel.

    Explicit user choice always wins. Otherwise:
    - Anthropic and OpenAI default to parallel execution
    - Ollama cloud models default to parallel execution
    - Ollama local models default to sequential execution
    """
    if explicit is not None:
        return explicit

    if backend != "ollama":
        return True

    model = str((backend_kwargs or {}).get("model") or "").strip()
    if not model:
        from broadside_ai.backends.ollama import _DEFAULT_MODEL

        model = _DEFAULT_MODEL

    return is_ollama_cloud_model(model)
