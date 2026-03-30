"""Voting synthesis — best for reasoning and classification tasks.

When agents are choosing from discrete options (labels, yes/no, rankings),
voting gives you a principled way to aggregate. Majority vote is the simplest
and most robust approach.

This is the right strategy when:
- The task has discrete answers (classification, yes/no, multiple choice)
- You want the most common answer, not a blend
- Self-consistency sampling applies (Wang et al. 2022)
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from broadside.backends import get_backend
from broadside.gather import GatherResult
from broadside.synthesize import Synthesis


async def synthesize_voting(
    gathered: GatherResult,
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    model: str | None = None,
    extract_labels: bool = True,
) -> Synthesis:
    """Aggregate outputs by voting.

    Two modes:
    1. extract_labels=True (default): Use an LLM to extract the core
       answer/label from each output, then vote on those.
    2. extract_labels=False: Treat each full output as a "vote" and
       use the LLM to identify the majority position.

    The first mode is better for classification; the second for reasoning
    where the "answer" isn't a single label.
    """
    bk = backend_kwargs or {}
    if model:
        bk["model"] = model
    llm = get_backend(backend, **bk)

    if extract_labels:
        return await _vote_with_extraction(llm, gathered)
    else:
        return await _vote_holistic(llm, gathered)


async def _vote_with_extraction(llm: Any, gathered: GatherResult) -> Synthesis:
    """Extract a label from each output, then count votes."""
    # Step 1: Extract the core answer from each output
    labels = []
    extraction_tokens = 0

    for i, text in enumerate(gathered.texts):
        prompt = (
            "Extract the single core answer, label, or conclusion from this text. "
            "Return ONLY the answer — no explanation, no reasoning, just the answer.\n\n"
            f"Text:\n{text}\n\n"
            "Core answer:"
        )
        result = await llm.complete(prompt)
        labels.append(result.text.strip().lower())
        extraction_tokens += result.total_tokens

    # Step 2: Vote
    vote_counts = Counter(labels)
    winner, winner_count = vote_counts.most_common(1)[0]
    total = len(labels)
    confidence = winner_count / total

    # Build result
    vote_summary = "\n".join(
        f"  {label}: {count}/{total} votes ({count/total:.0%})"
        for label, count in vote_counts.most_common()
    )

    result_text = (
        f"WINNER: {winner}\n"
        f"CONFIDENCE: {confidence:.0%} ({winner_count}/{total} agents)\n\n"
        f"VOTE BREAKDOWN:\n{vote_summary}"
    )

    if confidence < 0.5:
        result_text += (
            "\n\nWARNING: No majority — agents are split. "
            "This task may be ambiguous or under-specified."
        )

    return Synthesis(
        result=result_text,
        strategy="voting",
        gather=gathered,
        raw_outputs=gathered.texts,
        synthesis_tokens=extraction_tokens,
    )


async def _vote_holistic(llm: Any, gathered: GatherResult) -> Synthesis:
    """Use an LLM to identify the majority position across full outputs."""
    numbered = "\n\n".join(
        f"--- Agent {i + 1} ---\n{text}" for i, text in enumerate(gathered.texts)
    )

    prompt = (
        "Multiple agents answered the same question independently. "
        "Identify which answer the MAJORITY agrees on.\n\n"
        "Your response must include:\n"
        "1. WINNER: The majority answer\n"
        "2. CONFIDENCE: What fraction of agents supported it\n"
        "3. DISSENT: What the minority said (if any)\n\n"
        f"Agent outputs:\n\n{numbered}\n\n"
        "Majority analysis:"
    )

    result = await llm.complete(prompt)

    return Synthesis(
        result=result.text,
        strategy="voting",
        gather=gathered,
        raw_outputs=gathered.texts,
        synthesis_tokens=result.total_tokens,
    )
