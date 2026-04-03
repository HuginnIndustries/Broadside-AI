"""Synthesize - collapse N scatter outputs into a single actionable result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from broadside_ai.backends import get_backend
from broadside_ai.gather import GatherResult


@dataclass
class Synthesis:
    """The final output of a scatter/gather cycle."""

    result: str
    strategy: str
    gather: GatherResult
    raw_outputs: list[str] = field(default_factory=list)
    synthesis_tokens: int = 0
    parsed_result: dict[str, Any] | None = None
    requested_strategy: str = "llm"

    def total_tokens(self) -> int:
        return self.gather.total_tokens + self.synthesis_tokens


async def synthesize(
    gathered: GatherResult,
    strategy: str = "llm",
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    model: str | None = None,
    output_schema: dict[str, Any] | None = None,
) -> Synthesis:
    """Synthesize gathered results into a single output."""
    if strategy == "llm":
        return await _synthesize_llm(gathered, backend, backend_kwargs, model)
    if strategy == "consensus":
        from broadside_ai.strategies.consensus import synthesize_consensus

        return await synthesize_consensus(gathered, backend, backend_kwargs, model)
    if strategy == "voting":
        from broadside_ai.strategies.voting import synthesize_voting

        return await synthesize_voting(gathered, backend, backend_kwargs, model)
    if strategy == "weighted_merge":
        from broadside_ai.strategies.weighted_merge import synthesize_weighted_merge

        return await synthesize_weighted_merge(
            gathered,
            output_schema=output_schema,
            backend=backend,
            backend_kwargs=backend_kwargs,
            model=model,
        )
    raise ValueError(
        f"Unknown synthesis strategy '{strategy}'. "
        "Available: 'llm', 'consensus', 'voting', 'weighted_merge'."
    )


async def _synthesize_llm(
    gathered: GatherResult,
    backend: str,
    backend_kwargs: dict[str, Any] | None,
    model: str | None,
) -> Synthesis:
    """Use an LLM to read all outputs and produce a synthesis."""
    bk = dict(backend_kwargs or {})
    if model:
        bk["model"] = model

    llm = get_backend(backend, **bk)
    numbered = "\n\n".join(
        f"--- Output {i + 1} ---\n{text}" for i, text in enumerate(gathered.texts)
    )
    prompt = (
        "You are synthesizing the outputs of multiple independent agents who "
        "were given the same task. Your job:\n"
        "1. Identify the consensus - what do most outputs agree on?\n"
        "2. Flag meaningful outliers - where did outputs diverge significantly?\n"
        "3. Produce a single, clear synthesis that captures the best signal "
        "from all outputs.\n"
        "4. If outputs contradict each other on facts, flag the contradiction "
        "explicitly rather than silently picking one.\n\n"
        f"There are {len(gathered.texts)} outputs to synthesize:\n\n"
        f"{numbered}\n\n"
        "Provide your synthesis:"
    )

    result = await llm.complete(prompt)
    return Synthesis(
        result=result.text,
        strategy="llm",
        gather=gathered,
        raw_outputs=gathered.texts,
        synthesis_tokens=result.total_tokens,
        requested_strategy="llm",
    )
