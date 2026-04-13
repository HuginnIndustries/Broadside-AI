"""Conflict detection - flag contradictions between scatter outputs.

.. warning::

   This module is **experimental**. The LLM response is parsed into structured
   ``Conflict`` objects using a best-effort regex extractor. The detection
   quality depends heavily on the model's ability to follow the structured
   output format. For production use, prefer the ``consensus`` synthesis
   strategy, which handles disagreements as part of its normal flow.

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
        "Respond using this exact format for each contradiction found:\n\n"
        "CONTRADICTION:\n"
        "DESCRIPTION: <what the contradiction is>\n"
        "AGENTS: <agent numbers, e.g. 1, 3>\n"
        "SEVERITY: <hard or soft>\n\n"
        "Use 'hard' for factual contradictions and 'soft' for different emphasis "
        "or framing.\n\n"
        "If there are NO contradictions, respond with exactly:\n"
        "NO CONFLICTS DETECTED\n\n"
        f"There are {len(texts)} outputs to compare:\n\n"
        f"{numbered}\n\n"
        "Contradiction analysis:"
    )

    result = await llm.complete(prompt)

    if _no_conflicts_sentinel(result.text):
        return ConflictReport(
            conflicts=[],
            analysis_tokens=result.total_tokens,
        )

    conflicts = _parse_conflicts(result.text, n_outputs=len(texts))
    n_hard = sum(1 for conflict in conflicts if conflict.severity == "hard")
    n_soft = len(conflicts) - n_hard

    return ConflictReport(
        conflicts=conflicts,
        n_hard=n_hard,
        n_soft=n_soft,
        analysis_tokens=result.total_tokens,
    )


def _no_conflicts_sentinel(text: str) -> bool:
    """Check if the LLM response indicates no conflicts."""
    return "no conflicts detected" in text.lower()


def _parse_conflicts(text: str, n_outputs: int) -> list[Conflict]:
    """Parse structured contradiction blocks from the LLM response.

    Expects blocks in the form::

        CONTRADICTION:
        DESCRIPTION: <what the contradiction is>
        AGENTS: <agent numbers, e.g. 1, 3>
        SEVERITY: <hard or soft>

    Falls back to a single catch-all Conflict when parsing fails.
    """
    import re

    blocks = re.split(r"CONTRADICTION:\s*", text)
    conflicts: list[Conflict] = []

    for block in blocks[1:]:  # skip text before first CONTRADICTION:
        description = _extract_field(block, "DESCRIPTION")
        agents_str = _extract_field(block, "AGENTS")
        severity_str = _extract_field(block, "SEVERITY")

        if description is None:
            continue

        agents = _parse_agent_numbers(agents_str, n_outputs)
        severity = "hard" if severity_str is None or "soft" not in severity_str.lower() else "soft"

        conflicts.append(
            Conflict(
                description=description,
                agents_involved=agents,
                severity=severity,
            )
        )

    # Fallback: if no structured blocks were parsed but the model clearly
    # found contradictions, create a single catch-all conflict.
    if not conflicts and not _no_conflicts_sentinel(text):
        conflicts.append(
            Conflict(
                description=text.strip(),
                agents_involved=list(range(n_outputs)),
                severity="hard",
            )
        )

    return conflicts


def _extract_field(block: str, field_name: str) -> str | None:
    """Extract the value of a named field from a contradiction block."""
    import re

    pattern = rf"{field_name}:\s*(.+?)(?=\n(?:DESCRIPTION|AGENTS|SEVERITY|CONTRADICTION):|$)"
    match = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Single-line fallback
    pattern = rf"{field_name}:\s*(.+)"
    match = re.search(pattern, block, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _parse_agent_numbers(text: str | None, n_outputs: int) -> list[int]:
    """Parse agent numbers from a string like '1, 3' or '1 and 3'."""
    import re

    if text is None:
        return list(range(n_outputs))

    numbers = [int(n) - 1 for n in re.findall(r"\d+", text)]
    # Clamp to valid range
    numbers = [n for n in numbers if 0 <= n < n_outputs]
    return numbers if numbers else list(range(n_outputs))
