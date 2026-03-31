"""Tests for human-in-the-loop checkpoints."""

from __future__ import annotations

import pytest

from broadside_ai.checkpoints import Checkpoint, CheckpointRejected, TerminalCheckpoint
from broadside_ai.gather import GatherResult
from broadside_ai.run import run
from broadside_ai.synthesize import Synthesis
from broadside_ai.task import Task

# ---------------------------------------------------------------------------
# Mock checkpoint that records calls and returns configurable decisions
# ---------------------------------------------------------------------------


class MockCheckpoint:
    """A checkpoint that approves or rejects based on constructor args."""

    def __init__(
        self,
        pre_scatter: bool = True,
        post_gather: bool = True,
        post_synthesis: bool = True,
    ) -> None:
        self.approve_pre_scatter = pre_scatter
        self.approve_post_gather = post_gather
        self.approve_post_synthesis = post_synthesis
        self.calls: list[str] = []

    async def pre_scatter(self, task: Task, n: int) -> bool:
        self.calls.append("pre_scatter")
        return self.approve_pre_scatter

    async def post_gather(self, gathered: GatherResult) -> bool:
        self.calls.append("post_gather")
        return self.approve_post_gather

    async def post_synthesis(self, synthesis: Synthesis) -> bool:
        self.calls.append("post_synthesis")
        return self.approve_post_synthesis


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_terminal_checkpoint_implements_protocol() -> None:
    assert isinstance(TerminalCheckpoint(), Checkpoint)


def test_mock_checkpoint_implements_protocol() -> None:
    assert isinstance(MockCheckpoint(), Checkpoint)


# ---------------------------------------------------------------------------
# CheckpointRejected exception
# ---------------------------------------------------------------------------


def test_checkpoint_rejected_basic() -> None:
    exc = CheckpointRejected("pre_scatter")
    assert exc.stage == "pre_scatter"
    assert exc.reason == ""
    assert "pre_scatter" in str(exc)


def test_checkpoint_rejected_with_reason() -> None:
    exc = CheckpointRejected("post_gather", "too many failures")
    assert exc.stage == "post_gather"
    assert exc.reason == "too many failures"
    assert "too many failures" in str(exc)


# ---------------------------------------------------------------------------
# Pipeline integration via run()
# ---------------------------------------------------------------------------


async def test_all_checkpoints_approved() -> None:
    """When all checkpoints approve, the full pipeline runs."""
    cp = MockCheckpoint()
    task = Task(prompt="test prompt")

    result = await run(task, n=2, backend="mock", checkpoint=cp)

    assert result.result  # got a synthesis
    assert cp.calls == ["pre_scatter", "post_gather", "post_synthesis"]


async def test_pre_scatter_rejection() -> None:
    """When pre_scatter rejects, scatter never runs."""
    cp = MockCheckpoint(pre_scatter=False)
    task = Task(prompt="test prompt")

    with pytest.raises(CheckpointRejected) as exc_info:
        await run(task, n=2, backend="mock", checkpoint=cp)

    assert exc_info.value.stage == "pre_scatter"
    assert cp.calls == ["pre_scatter"]


async def test_post_gather_rejection() -> None:
    """When post_gather rejects, synthesis never runs."""
    cp = MockCheckpoint(post_gather=False)
    task = Task(prompt="test prompt")

    with pytest.raises(CheckpointRejected) as exc_info:
        await run(task, n=2, backend="mock", checkpoint=cp)

    assert exc_info.value.stage == "post_gather"
    assert cp.calls == ["pre_scatter", "post_gather"]


async def test_post_synthesis_rejection() -> None:
    """When post_synthesis rejects, the result is not returned."""
    cp = MockCheckpoint(post_synthesis=False)
    task = Task(prompt="test prompt")

    with pytest.raises(CheckpointRejected) as exc_info:
        await run(task, n=2, backend="mock", checkpoint=cp)

    assert exc_info.value.stage == "post_synthesis"
    assert cp.calls == ["pre_scatter", "post_gather", "post_synthesis"]


async def test_no_checkpoint_runs_normally() -> None:
    """Without a checkpoint, the pipeline runs end-to-end."""
    task = Task(prompt="test prompt")

    result = await run(task, n=2, backend="mock", checkpoint=None)

    assert result.result  # got a synthesis
