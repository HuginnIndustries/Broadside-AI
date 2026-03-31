"""Quality signals for early termination of scatter branches.

When running N parallel agents, we can cancel remaining branches once we
have enough signal. This saves cost without sacrificing output quality.

Two signals are implemented:
1. Sufficient results: got `min_complete` results, cancel the rest.
2. Agreement: first K results converge, extra branches won't add value.
"""

from __future__ import annotations

from dataclasses import dataclass

from broadside_ai.backends.base import AgentResult
from broadside_ai.parsing import try_parse_json


@dataclass
class EarlyStop:
    """Configuration for early termination of scatter branches.

    Args:
        min_complete: Stop after this many results arrive. Must be >= 2.
            Set to None to require all N branches (default behavior).
        agreement_threshold: If this fraction of completed results agree,
            stop early. E.g., 1.0 means unanimous, 0.67 means 2/3 agreement.
            Set to None to disable agreement checking.
    """

    min_complete: int | None = None
    agreement_threshold: float | None = None

    def __post_init__(self) -> None:
        if self.min_complete is not None and self.min_complete < 2:
            raise ValueError("min_complete must be >= 2")
        if self.agreement_threshold is not None:
            if not (0.0 < self.agreement_threshold <= 1.0):
                raise ValueError("agreement_threshold must be in (0, 1]")


def should_stop(results: list[AgentResult], early_stop: EarlyStop) -> bool:
    """Check if quality signals indicate we should cancel remaining branches.

    Called after each result arrives during parallel scatter.
    """
    n = len(results)
    if n < 2:
        return False

    # Check minimum completions
    if early_stop.min_complete is not None and n >= early_stop.min_complete:
        if early_stop.agreement_threshold is None:
            return True
        # If agreement is also set, check both
        return _check_agreement(results, early_stop.agreement_threshold)

    # Check agreement even before min_complete
    if early_stop.agreement_threshold is not None:
        return _check_agreement(results, early_stop.agreement_threshold)

    return False


def _check_agreement(results: list[AgentResult], threshold: float) -> bool:
    """Check if results agree above the threshold.

    Agreement is measured by comparing normalized outputs. For structured
    outputs (JSON), we compare parsed dicts. For text, we compare by
    looking for the most common response.
    """
    n = len(results)
    if n < 2:
        return False

    # Try structured comparison first
    signatures = []
    for r in results:
        parsed = r.parsed if r.parsed is not None else try_parse_json(r.text)
        if parsed is not None:
            # Use sorted JSON as a canonical form for comparison
            signatures.append(_dict_signature(parsed))
        else:
            # Fall back to normalized text
            signatures.append(r.text.strip().lower())

    # Find the most common signature
    from collections import Counter

    counts = Counter(signatures)
    most_common_count = counts.most_common(1)[0][1]

    return most_common_count / n >= threshold


def _dict_signature(d: dict[str, object]) -> str:
    """Create a canonical string from a dict for comparison.

    Ignores 'confidence' fields since those are expected to vary.
    """
    import json

    filtered = {k: v for k, v in sorted(d.items()) if k != "confidence"}
    return json.dumps(filtered, sort_keys=True)
