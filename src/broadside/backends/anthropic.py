"""Anthropic backend — requires `pip install broadside[anthropic]`."""

from __future__ import annotations

import time
from typing import Any

try:
    import anthropic
except ImportError as e:
    raise ImportError(
        "Anthropic backend requires the anthropic package. "
        "Install it with: pip install broadside[anthropic]"
    ) from e

from broadside.backends import register
from broadside.backends.base import AgentResult, Backend

_DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicBackend(Backend):
    """Anthropic backend using the Messages API."""

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> None:
        import os

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "Anthropic API key not found. Set it with:\n"
                "  Windows CMD:    set ANTHROPIC_API_KEY=sk-...\n"
                "  PowerShell:     $env:ANTHROPIC_API_KEY=\"sk-...\"\n"
                "  macOS/Linux:    export ANTHROPIC_API_KEY=sk-..."
            )

        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)

    async def complete(self, prompt: str, **kwargs: Any) -> AgentResult:
        t0 = time.perf_counter()

        msg = await self._client.messages.create(
            model=kwargs.pop("model", self.model),
            max_tokens=kwargs.pop("max_tokens", self.max_tokens),
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        latency = (time.perf_counter() - t0) * 1000
        text = msg.content[0].text if msg.content else ""

        return AgentResult(
            text=text,
            tokens_in=msg.usage.input_tokens,
            tokens_out=msg.usage.output_tokens,
            latency_ms=latency,
            model=msg.model,
            backend="anthropic",
        )

    def name(self) -> str:
        return "anthropic"


register("anthropic", AnthropicBackend)
