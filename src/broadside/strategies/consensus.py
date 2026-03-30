"""Consensus synthesis — best for knowledge tasks.

Identifies what most agents agree on and flags disagreements. Works by
having an LLM read all outputs and extract the consensus, rather than
trying to do text-matching (which breaks on paraphrasing).

This is the right strategy when:
- The task has factual answers (comparisons, analyses, summaries)
- You want to know what the "average" response looks like
- Disagreement signals the task is ambiguous or under-specified
"""

from __future__ import annotations

from typing import Any

from broadside.backends import get_backend
from broadside.gather import GatherResult
from broadside.synthesize import Synthesis


async def synthesize_consensus(
    gathered: GatherResult,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    model: str | None = None,
) -> Synthesis:
    """Extract consensus from gathered outputs.

    Returns a synthesis that clearly separates:
    1. What all/most agents agreed on
    2. Where agents disagreed (and what each side said)
    3. Any facts that only one agent mentioned (potential hallucination or insight)
    """
    bk = backend_kwargs or {}
    if model:
        bk["model"] = model
    llm = get_backend(backend, **bk)

    numbered = "\n\n".join(
        f"--- Agent {i + 1} ---\n{text}" for i, text in enumerate(gathered.texts)
    )

    prompt = (
        "You are analyzing outputs from multiple independent agents who received "
        "the same task. Your job is to extract the CONSENSUS — what they agree on.\n\n"
        "Structure your response as:\n\n"
        "CONSENSUS:\n"
        "Points that all or most agents agree on.\n\n"
        "DISAGREEMENTS:\n"
        "Points where agents gave conflicting answers. State what each side claimed.\n\n"
        "UNIQUE CLAIMS:\n"
        "Facts or points mentioned by only one agent. These could be insights "
        "the others missed, or hallucinations. Flag them for human review.\n\n"
        f"There are {len(gathered.texts)} agent outputs:\n\n"
        f"{numbered}\n\n"
        "Provide your consensus analysis:"
    )

    result = await llm.complete(prompt)

    return Synthesis(
        result=result.text,
        strategy="consensus",
        gather=gathered,
        raw_outputs=gathered.texts,
        synthesis_tokens=result.total_tokens,
    )
