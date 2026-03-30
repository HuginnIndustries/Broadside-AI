"""Synthesize — collapse N scatter outputs into a single actionable result.

Aggregation is the hard problem, not scatter. This module provides synthesis
strategies that match the research:
- Consensus: best for knowledge tasks (ACL 2025, Kaesberg et al.)
- Voting: best for reasoning/classification tasks
- LLM: a model reads all outputs and produces a synthesis

The default is LLM synthesis — it's the most general.
Consensus and voting are available for task-appropriate use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from broadside.backends import get_backend
from broadside.backends.base import AgentResult
from broadside.gather import GatherResult


@dataclass
class Synthesis:
    """The final output of a scatter/gather cycle."""

    result: str
    strategy: str
    gather: GatherResult

    # For transparency — show what the synthesizer saw
    raw_outputs: list[str] = field(default_factory=list)

    # Tokens consumed by the synthesis step itself
    synthesis_tokens: int = 0

    def total_tokens(self) -> int:
        """Total cost: scatter + synthesis."""
        return self.gather.total_tokens + self.synthesis_tokens


async def synthesize(
    gathered: GatherResult,
    strategy: str = "llm",
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    model: str | None = None,
) -> Synthesis:
    """Synthesize gathered results into a single output.

    Args:
        gathered: The GatherResult from the scatter phase.
        strategy: Synthesis strategy. Currently supported: "llm".
        backend: Which backend to use for LLM synthesis.
        backend_kwargs: Passed to the backend constructor.
        model: Override model for synthesis (often you want a stronger
               model here than in the scatter phase).
    """
    if strategy == "llm":
        return await _synthesize_llm(gathered, backend, backend_kwargs, model)
    elif strategy == "consensus":
        from broadside.strategies.consensus import synthesize_consensus

        return await synthesize_consensus(gathered, backend, backend_kwargs, model)
    elif strategy == "voting":
        from broadside.strategies.voting import synthesize_voting

        return await synthesize_voting(gathered, backend, backend_kwargs, model)
    else:
        raise ValueError(
            f"Unknown synthesis strategy '{strategy}'. "
            f"Available: 'llm', 'consensus', 'voting'."
        )


async def _synthesize_llm(
    gathered: GatherResult,
    backend: str,
    backend_kwargs: dict[str, Any] | None,
    model: str | None,
) -> Synthesis:
    """Use an LLM to read all outputs and produce a synthesis."""
    bk = backend_kwargs or {}
    if model:
        bk["model"] = model

    llm = get_backend(backend, **bk)

    # Build the synthesis prompt — show the LLM all scatter outputs
    numbered = "\n\n".join(
        f"--- Output {i + 1} ---\n{text}" for i, text in enumerate(gathered.texts)
    )

    prompt = (
        "You are synthesizing the outputs of multiple independent agents who "
        "were given the same task. Your job:\n"
        "1. Identify the consensus — what do most outputs agree on?\n"
        "2. Flag meaningful outliers — where did outputs diverge significantly?\n"
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
    )
