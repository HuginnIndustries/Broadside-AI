"""Human-in-the-loop checkpoints for the scatter/gather/synthesize pipeline.

Checkpoints let a human review and approve/reject at three points:
1. Pre-scatter — review the task before scattering to N agents
2. Post-gather — review raw results before synthesis
3. Post-synthesis — review the final output before accepting

Usage::

    from broadside_ai.checkpoints import TerminalCheckpoint
    from broadside_ai import Task, run_sync

    result = run_sync(task, n=3, checkpoint=TerminalCheckpoint())
"""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

from broadside_ai.gather import GatherResult
from broadside_ai.synthesize import Synthesis
from broadside_ai.task import Task


class CheckpointRejected(Exception):
    """Raised when a human rejects at a checkpoint."""

    def __init__(self, stage: str, reason: str = "") -> None:
        self.stage = stage
        self.reason = reason
        msg = f"Rejected at {stage}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


@runtime_checkable
class Checkpoint(Protocol):
    """Protocol for human-in-the-loop checkpoints.

    Implement this to create custom checkpoint handlers (Slack bots,
    web UIs, approval queues, etc.). Each method returns True to proceed
    or False to reject.
    """

    async def pre_scatter(self, task: Task, n: int) -> bool:
        """Review the task before scattering. Return True to proceed."""
        ...

    async def post_gather(self, gathered: GatherResult) -> bool:
        """Review gathered results before synthesis. Return True to synthesize."""
        ...

    async def post_synthesis(self, synthesis: Synthesis) -> bool:
        """Review the final synthesis. Return True to accept."""
        ...


class TerminalCheckpoint:
    """Interactive terminal checkpoint — prompts via stdin.

    Displays a summary at each stage and asks the user to approve or reject.
    Uses asyncio.to_thread so it doesn't block the event loop.
    """

    async def pre_scatter(self, task: Task, n: int) -> bool:
        """Show task details and ask for approval."""
        prompt_preview = task.prompt[:200]
        if len(task.prompt) > 200:
            prompt_preview += "..."

        print("\n--- Pre-Scatter Checkpoint ---")
        print(f"Task: {prompt_preview}")
        print(f"Agents: {n}")
        if task.output_schema:
            print(f"Output schema: {task.output_schema}")
        print()

        return await self._ask("Proceed with scatter?")

    async def post_gather(self, gathered: GatherResult) -> bool:
        """Show gather summary and ask for approval."""
        print("\n--- Post-Gather Checkpoint ---")
        print(f"Completed: {gathered.n_completed}/{gathered.n_completed + gathered.n_failed}")
        print(f"Tokens used: {gathered.total_tokens:,}")
        print(f"Wall clock: {gathered.wall_clock_ms / 1000:.1f}s")

        for i, text in enumerate(gathered.texts, 1):
            preview = text[:150].replace("\n", " ")
            if len(text) > 150:
                preview += "..."
            print(f"\n  Agent {i}: {preview}")
        print()

        return await self._ask("Proceed with synthesis?")

    async def post_synthesis(self, synthesis: Synthesis) -> bool:
        """Show synthesis result and ask for approval."""
        print("\n--- Post-Synthesis Checkpoint ---")
        print(f"Strategy: {synthesis.strategy}")
        print(f"Synthesis tokens: {synthesis.synthesis_tokens:,}")

        result_preview = synthesis.result[:300]
        if len(synthesis.result) > 300:
            result_preview += "..."
        print(f"\nResult:\n{result_preview}")
        print()

        return await self._ask("Accept this result?")

    async def _ask(self, question: str) -> bool:
        """Prompt user and return True for yes, False for no."""
        response = await asyncio.to_thread(input, f"{question} [Y/n] ")
        return response.strip().lower() in ("", "y", "yes")


__all__ = ["Checkpoint", "CheckpointRejected", "TerminalCheckpoint"]
