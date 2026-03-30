"""Tests for voting synthesis strategy."""

import pytest

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
from broadside_ai.strategies.voting import synthesize_voting
from tests.conftest import make_gather


class VotingMockBackend(Backend):
    """Mock that returns different labels for extraction testing."""

    def __init__(self, labels: list[str] | None = None, **kwargs: object) -> None:
        self._labels = labels or ["yes"]
        self._call_count = 0

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        text = self._labels[self._call_count % len(self._labels)]
        self._call_count += 1
        return AgentResult(
            text=text,
            tokens_in=10,
            tokens_out=5,
            latency_ms=3.0,
            model="vote-mock",
            backend="vote-mock",
        )

    def name(self) -> str:
        return "vote-mock"


register("vote-mock", VotingMockBackend)


@pytest.mark.asyncio
async def test_voting_with_extraction():
    """Voting with label extraction produces WINNER and CONFIDENCE."""
    gathered = make_gather(["I think yes", "Definitely yes", "No way"])
    # The mock returns "yes" for every extraction call
    result = await synthesize_voting(gathered, backend="vote-mock", extract_labels=True)
    assert result.strategy == "voting"
    assert "WINNER" in result.result
    assert "CONFIDENCE" in result.result
    assert result.synthesis_tokens > 0


@pytest.mark.asyncio
async def test_voting_unanimous():
    """Unanimous vote should show 100% confidence."""
    gathered = make_gather(["yes", "yes", "yes"])
    result = await synthesize_voting(gathered, backend="vote-mock", extract_labels=True)
    assert "100%" in result.result
    assert "3/3" in result.result


@pytest.mark.asyncio
async def test_voting_split_warns():
    """Split vote (no majority) should include a warning."""
    # Mock returns cycling labels: a, b, c — no majority
    register(
        "split-mock",
        type(
            "SplitMock",
            (VotingMockBackend,),
            {
                "__init__": lambda self, **kw: VotingMockBackend.__init__(
                    self, labels=["a", "b", "c"], **kw
                )
            },
        ),
    )
    gathered = make_gather(["option a", "option b", "option c"])
    result = await synthesize_voting(gathered, backend="split-mock", extract_labels=True)
    assert "WARNING" in result.result or "1/3" in result.result


@pytest.mark.asyncio
async def test_voting_holistic():
    """Holistic voting (no label extraction) returns a valid synthesis."""
    gathered = make_gather(["output 1", "output 2", "output 3"])
    result = await synthesize_voting(gathered, backend="mock", extract_labels=False)
    assert result.strategy == "voting"
    assert result.result  # non-empty


@pytest.mark.asyncio
async def test_voting_with_model_override():
    """Model override is passed through without error."""
    gathered = make_gather(["a", "b"])
    result = await synthesize_voting(gathered, backend="vote-mock", model="custom-model")
    assert result.strategy == "voting"
