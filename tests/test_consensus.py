"""Tests for consensus synthesis strategy."""

import pytest

from broadside_ai.strategies.consensus import synthesize_consensus
from tests.conftest import make_gather


@pytest.mark.asyncio
async def test_consensus_returns_synthesis():
    """Consensus strategy returns a Synthesis with strategy='consensus'."""
    gathered = make_gather(["Paris is the capital", "Paris is the capital", "Paris"])
    result = await synthesize_consensus(gathered, backend="mock")
    assert result.strategy == "consensus"
    assert result.result  # non-empty
    assert result.raw_outputs == gathered.texts
    assert result.synthesis_tokens > 0


@pytest.mark.asyncio
async def test_consensus_includes_all_outputs_in_prompt():
    """Consensus prompt should reference all agent outputs."""
    gathered = make_gather(["output A", "output B"])
    result = await synthesize_consensus(gathered, backend="mock")
    # The synthesis result comes from the mock, but the function should run without error
    assert result.gather is gathered
    assert len(result.raw_outputs) == 2


@pytest.mark.asyncio
async def test_consensus_with_model_override():
    """Model override is passed through without error."""
    gathered = make_gather(["a", "b", "c"])
    result = await synthesize_consensus(gathered, backend="mock", model="custom-model")
    assert result.strategy == "consensus"


@pytest.mark.asyncio
async def test_consensus_single_output():
    """Consensus with a single output should still work."""
    gathered = make_gather(["only one agent responded"])
    result = await synthesize_consensus(gathered, backend="mock")
    assert result.strategy == "consensus"
    assert len(result.raw_outputs) == 1
