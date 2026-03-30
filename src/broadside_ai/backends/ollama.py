"""Ollama backend — local-first, zero API keys.

This is in the base install intentionally. Someone should be able to
`pip install broadside-ai` and run the quick start with just Ollama running.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend

# Cloud by default — works without a GPU, free tier on Ollama.
# Users with local hardware can override to a local model (e.g. gemma3:1b).
_DEFAULT_MODEL = "nemotron-3-super:cloud"
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Can't connect to Ollama at {self.base_url}.\n\n"
                f"Make sure Ollama is installed and running:\n"
                f"  1. Install: https://ollama.ai\n"
                f"  2. Pull a model: ollama pull {self.model}\n"
                f"  3. Start the server: ollama serve\n\n"
                f"Or sign in to the Ollama app for free cloud access.\n"
                f"  The default model (nemotron-3-super:cloud) runs in the cloud.\n"
                f"  See all cloud models: ollama list --cloud\n"
            ) from None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                model_name = payload["model"]
                hint = f"Pull it first: ollama pull {model_name}"
                if not (model_name.endswith("-cloud") or ":cloud" in model_name):
                    hint += (
                        f"\n\nOr try the cloud version (no download, free tier):"
                        f"\n  ollama run {model_name.split(':')[0]}:cloud"
                    )
                raise RuntimeError(f"Model '{model_name}' not found in Ollama.\n{hint}") from None
            raise

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
