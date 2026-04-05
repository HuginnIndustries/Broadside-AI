"""Conflict detection - flag contradictions between scatter outputs.

The hardest part of aggregation is when agents disagree on facts. Rather than
silently picking one answer, Broadside-AI flags conflicts explicitly so a human
(or synthesis strategy) can make an informed call.

Skywork.ai reported about 7% fact conflicts and 11% duplication in parallel
outputs. This module exists to surface that 7%.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from broadside_ai.backends import get_backend


@dataclass
class Conflict:
    """A detected contradiction between two or more outputs."""

    description: str
    agents_involved: list[int]  # indices into the outputs list
    severity: str  # "hard" = factual contradiction, "soft" = different emphasis


@dataclass
class ConflictReport:
    """Summary of conflicts found across scatter outputs."""

    conflicts: list[Conflict]
    n_hard: int = 0
    n_soft: int = 0
    analysis_tokens: int = 0

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


async def detect_conflicts(
    texts: list[str],
    backend: str = "ollama",
    backend_kwargs: dict[str, Any] | None = None,
    model: str | None = None,
) -> ConflictReport:
    """Use an LLM to detect factual contradictions between outputs.

    This is a separate step from synthesis - you can run it independently
    to audit outputs before deciding how to synthesize.
    """
    bk = dict(backend_kwargs or {})
    if model:
        bk["model"] = model
    llm = get_backend(backend, **bk)

    numbered = "\n\n".join(f"--- Output {i + 1} ---\n{text}" for i, text in enumerate(texts))

    prompt = (
        "Compare these agent outputs and identify any CONTRADICTIONS - places "
        "where two or more outputs make claims that cannot both be true.\n\n"
        "For each contradiction found, provide:\n"
        "- DESCRIPTION: What the contradiction is\n"
        "- AGENTS: Which agent numbers are involved (e.g., 1 and 3)\n"
        "- SEVERITY: 'hard' if it's a factual contradiction, 'soft' if it's "
        "just different emphasis or framing\n\n"
        "If there are NO contradictions, say 'NO CONFLICTS DETECTED'.\n\n"
        f"There are {len(texts)} outputs to compare:\n\n"
        f"{numbered}\n\n"
        "Contradiction analysis:"
    )

    result = await llm.complete(prompt)

    no_conflicts = "no conflicts detected" in result.text.lower()

    if no_conflicts:
        return ConflictReport(
            conflicts=[],
            analysis_tokens=result.total_tokens,
        )

    return ConflictReport(
        conflicts=[
            Conflict(
                description=result.text,
                agents_involved=list(range(len(texts))),
                severity="hard",
            )
        ],
        n_hard=1,
        analysis_tokens=result.total_tokens,
    )
