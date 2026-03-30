"""OpenAI-compatible backend — requires `pip install broadside-ai[openai]`.

Works with OpenAI, Azure OpenAI, and any API that implements the
OpenAI chat completions interface (vLLM, Together, Groq, etc.).
"""

from __future__ import annotations

import time
from typing import Any

try:
    import openai
except ImportError as e:
    raise ImportError(
        "OpenAI backend requires the openai package. "
        "Install it with: pip install broadside-ai[openai]"
    ) from e

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend

_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIBackend(Backend):
    """OpenAI-compatible backend using the chat completions API."""

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> None:
        import os

        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "OpenAI API key not found. Set it with:\n"
                "  Windows CMD:    set OPENAI_API_KEY=sk-...\n"
                "  PowerShell:     $env:OPENAI_API_KEY=\"sk-...\"\n"
                "  macOS/Linux:    export OPENAI_API_KEY=sk-..."
            )

        self.model = model
        self.max_tokens = max_tokens
        client_kwargs: dict[str, Any] = {"api_key": resolved_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**client_kwargs)

    async def complete(self, prompt: str, **kwargs: Any) -> AgentResult:
        t0 = time.perf_counter()

        resp = await self._client.chat.completions.create(
            model=kwargs.pop("model", self.model),
            max_tokens=kwargs.pop("max_tokens", self.max_tokens),
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        latency = (time.perf_counter() - t0) * 1000
        choice = resp.choices[0] if resp.choices else None
        text = choice.message.content or "" if choice else ""

        usage = resp.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        return AgentResult(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency,
            model=resp.model or self.model,
            backend="openai",
        )

    def name(self) -> str:
        return "openai"


register("openai", OpenAIBackend)
