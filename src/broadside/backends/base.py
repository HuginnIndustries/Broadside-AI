"""Abstract backend interface — what every LLM provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentResult:
    """Single agent's output from one scatter branch."""

    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    model: str
    backend: str

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


class Backend(ABC):
    """Interface for LLM backends.

    Each backend wraps a single provider's API. Backends are stateless —
    all config is passed at init, all calls are independent.
    """

    @abstractmethod
    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        """Send a prompt and return the result.

        kwargs are backend-specific (temperature, max_tokens, etc.) and
        passed through to the underlying API.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Short identifier for this backend (e.g. 'ollama', 'anthropic')."""
        ...
