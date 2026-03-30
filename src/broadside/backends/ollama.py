"""Ollama backend — local-first, zero API keys.

This is in the base install intentionally. Someone should be able to
`pip install broadside` and run the quick start with just Ollama running.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from broadside.backends import register
from broadside.backends.base import AgentResult, Backend

# Sensible default — small, fast, available on most Ollama installs
_DEFAULT_MODEL = "llama3.2"
_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaBackend(Backend):
    """Ollama backend using the /api/generate endpoint."""

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 120.0,
        **kwargs: Any,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, prompt: str, **kwargs: Any) -> AgentResult:
        t0 = time.perf_counter()

        payload: dict[str, Any] = {
            "model": kwargs.pop("model", self.model),
            "prompt": prompt,
            "stream": False,
        }
        # Pass through Ollama-specific options (temperature, num_predict, etc.)
        if kwargs:
            payload["options"] = kwargs

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.perf_counter() - t0) * 1000

        return AgentResult(
            text=data.get("response", ""),
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_ms=latency,
            model=data.get("model", self.model),
            backend="ollama",
        )

    def name(self) -> str:
        return "ollama"


# Auto-register when this module is imported
register("ollama", OllamaBackend)
