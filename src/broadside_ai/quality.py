"""Quality signals for early termination of scatter branches."""

from __future__ import annotations

import json
from dataclasses import dataclass

from broadside_ai.backends.base import AgentResult
from broadside_ai.parsing import try_parse_json


@dataclass
class EarlyStop:
    """Configuration for early termination of scatter branches."""

    min_complete: int | None = None
    agreement_threshold: float | None = None

    def __post_init__(self) -> None:
        if self.min_complete is not None and self.min_complete < 2:
            raise ValueError("min_complete must be >= 2")
        if self.agreement_threshold is not None and not (0.0 < self.agreement_threshold <= 1.0):
            raise ValueError("agreement_threshold must be in (0, 1]")


def should_stop(results: list[AgentResult], early_stop: EarlyStop) -> bool:
    """Check if quality signals indicate we should cancel remaining branches."""
    n_results = len(results)
    if n_results < 2:
        return False

    if early_stop.min_complete is not None and n_results >= early_stop.min_complete:
        if early_stop.agreement_threshold is None:
            return True
        return _check_agreement(results, early_stop.agreement_threshold)

    if early_stop.agreement_threshold is not None:
        return _check_agreement(results, early_stop.agreement_threshold)

    return False


def _check_agreement(results: list[AgentResult], threshold: float) -> bool:
    signatures = []
    for result in results:
        parsed = result.parsed if result.parsed is not None else try_parse_json(result.text)
        if parsed is not None:
            signatures.append(_dict_signature(parsed))
        else:
            signatures.append(result.text.strip().lower())

    from collections import Counter

    counts = Counter(signatures)
    most_common_count = counts.most_common(1)[0][1]
    return most_common_count / len(results) >= threshold


def _dict_signature(data: dict[str, object]) -> str:
    """Create a canonical signature for structured agreement checks."""
    filtered = {key: value for key, value in sorted(data.items()) if key != "confidence"}
    return json.dumps(filtered, sort_keys=True)
