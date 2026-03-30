"""Tests for conflict detection."""

import pytest

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
from broadside_ai.conflicts import Conflict, ConflictReport, detect_conflicts


class NoConflictMock(Backend):
    """Returns a response indicating no conflicts."""

    def __init__(self, **kwargs: object) -> None:
        pass

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        return AgentResult(
            text="NO CONFLICTS DETECTED",
            tokens_in=10,
            tokens_out=5,
            latency_ms=3.0,
            model="nc-mock",
            backend="nc-mock",
        )

    def name(self) -> str:
        return "nc-mock"


class HasConflictMock(Backend):
    """Returns a response indicating conflicts exist."""

    def __init__(self, **kwargs: object) -> None:
        pass

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        return AgentResult(
            text="CONTRADICTION: Agent 1 says X, Agent 2 says Y. These cannot both be true.",
            tokens_in=10,
            tokens_out=20,
            latency_ms=3.0,
            model="hc-mock",
            backend="hc-mock",
        )

    def name(self) -> str:
        return "hc-mock"


register("nc-mock", NoConflictMock)
register("hc-mock", HasConflictMock)


@pytest.mark.asyncio
async def test_no_conflicts_detected():
    """When the LLM says no conflicts, report should be empty."""
    report = await detect_conflicts(
        ["Paris is in France", "Paris is in France"],
        backend="nc-mock",
    )
    assert not report.has_conflicts
    assert len(report.conflicts) == 0
    assert report.analysis_tokens > 0


@pytest.mark.asyncio
async def test_conflicts_detected():
    """When the LLM finds contradictions, report should have conflicts."""
    report = await detect_conflicts(
        ["The population is 1 million", "The population is 5 million"],
        backend="hc-mock",
    )
    assert report.has_conflicts
    assert len(report.conflicts) == 1
    assert report.n_hard == 1
    assert report.analysis_tokens > 0


@pytest.mark.asyncio
async def test_conflict_report_with_model_override():
    """Model override passes through without error."""
    report = await detect_conflicts(
        ["a", "b"],
        backend="nc-mock",
        model="custom-model",
    )
    assert isinstance(report, ConflictReport)


def test_conflict_dataclass():
    """Conflict and ConflictReport dataclasses work as expected."""
    c = Conflict(description="test", agents_involved=[0, 1], severity="hard")
    assert c.severity == "hard"

    report = ConflictReport(conflicts=[c], n_hard=1, n_soft=0)
    assert report.has_conflicts
    assert report.n_hard == 1


def test_empty_conflict_report():
    """Empty ConflictReport has no conflicts."""
    report = ConflictReport(conflicts=[])
    assert not report.has_conflicts
