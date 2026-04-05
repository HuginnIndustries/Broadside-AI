"""Synthesis behavior tests for Broadside-AI."""

from __future__ import annotations

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
from broadside_ai.synthesize import synthesize
from tests.conftest import make_gather


class RecordingBackend(Backend):
    """Backend that records the prompt it receives for assertion."""

    last_prompt: str = ""

    def __init__(self, response: str = "final answer", **kwargs: object) -> None:
        self._response = response

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        type(self).last_prompt = prompt
        return AgentResult(
            text=self._response,
            tokens_in=10,
            tokens_out=20,
            latency_ms=5.0,
            model="recording-model",
            backend="recording",
        )

    def name(self) -> str:
        return "recording"


register("recording", RecordingBackend)


async def test_llm_synthesis_prompt_requests_direct_final_answer():
    gathered = make_gather(
        [
            "DotFlow keeps your shell setup synced across machines.",
            "A dotfile manager should make new-machine setup fast and reliable.",
        ]
    )

    result = await synthesize(gathered, strategy="llm", backend="recording")

    assert result.strategy == "llm"
    assert result.result == "final answer"
    assert "Return one direct final answer" in RecordingBackend.last_prompt
    assert "Lead with the answer or plan itself" in RecordingBackend.last_prompt
    assert (
        "If the task is procedural, return the minimum useful checklist"
        in RecordingBackend.last_prompt
    )
    assert "Do not turn the response into a meta-analysis" in RecordingBackend.last_prompt
    assert "briefly say what context is missing" in RecordingBackend.last_prompt
    assert "Write the best final answer:" in RecordingBackend.last_prompt


async def test_llm_synthesis_prompt_avoids_consensus_report_default():
    gathered = make_gather(
        [
            "Option A is simplest for solo developers.",
            "Option B is safer for teams with strict controls.",
        ]
    )

    await synthesize(gathered, strategy="llm", backend="recording")

    assert "Identify the consensus" not in RecordingBackend.last_prompt
    assert "Flag meaningful outliers" not in RecordingBackend.last_prompt
    assert "Provide your synthesis:" not in RecordingBackend.last_prompt


async def test_consensus_strategy_keeps_analysis_oriented_prompt():
    gathered = make_gather(
        [
            "SQLite is simpler for small apps.",
            "SQLite is simpler, but PostgreSQL scales better for concurrent writes.",
        ]
    )

    await synthesize(gathered, strategy="consensus", backend="recording")

    assert "extract the CONSENSUS" in RecordingBackend.last_prompt
    assert "DISAGREEMENTS:" in RecordingBackend.last_prompt
    assert "UNIQUE CLAIMS:" in RecordingBackend.last_prompt


async def test_consensus_does_not_mutate_backend_kwargs():
    gathered = make_gather(["answer A", "answer B"])
    kwargs: dict[str, object] = {"timeout": 30}
    await synthesize(gathered, strategy="consensus", backend="recording", backend_kwargs=kwargs)
    assert "model" not in kwargs


async def test_voting_does_not_mutate_backend_kwargs():
    gathered = make_gather(["answer A", "answer B"])
    kwargs: dict[str, object] = {"timeout": 30}
    await synthesize(gathered, strategy="voting", backend="recording", backend_kwargs=kwargs)
    assert "model" not in kwargs
