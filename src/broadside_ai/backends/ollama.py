"""Ollama backend - local-first, zero API keys."""

from __future__ import annotations

import time
from typing import Any

import httpx

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend

_DEFAULT_MODEL = "nemotron-3-super:cloud"  # cloud model; use --model for local
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
        if kwargs:
            payload["options"] = kwargs

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError:
                    raise RuntimeError(
                        f"Invalid response from Ollama at {self.base_url}. "
                        "The server may be overloaded or returning an error page."
                    ) from None
        except httpx.ConnectError:
            raise ConnectionError(
                f"Can't connect to Ollama at {self.base_url}.\n\n"
                "Make sure Ollama is installed and running:\n"
                "  1. Install: https://ollama.com\n"
                f"  2. Pull a model: ollama pull {self.model}\n"
                "  3. Start the server: ollama serve\n\n"
                "Or sign in for cloud access with:\n"
                "  ollama signin\n"
            ) from None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                model_name = payload["model"]
                hint = f"Pull it first: ollama pull {model_name}"
                if not (model_name.endswith("-cloud") or ":cloud" in model_name):
                    hint += (
                        "\n\nOr try the cloud version:\n"
                        f"  ollama pull {model_name.split(':')[0]}:cloud"
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


register("ollama", OllamaBackend)
