"""CLI contract tests for Broadside-AI."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner

from broadside_ai.backends import register
from broadside_ai.backends.base import AgentResult, Backend
from broadside_ai.cli import main

_TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


class EchoPromptBackend(Backend):
    """Backend that echoes prompts for CLI prompt-shaping assertions."""

    async def complete(self, prompt: str, **kwargs: object) -> AgentResult:
        return AgentResult(
            text=prompt,
            tokens_in=10,
            tokens_out=20,
            latency_ms=5.0,
            model="echo-prompt-model",
            backend="echo-prompt",
        )

    def name(self) -> str:
        return "echo-prompt"


register("echo-prompt", EchoPromptBackend)


@contextmanager
def _isolated_fs():
    _TEST_TEMP_ROOT.mkdir(exist_ok=True)
    workspace = _TEST_TEMP_ROOT / f"tmp{uuid.uuid4().hex}"
    workspace.mkdir()
    previous_cwd = Path.cwd()
    try:
        os.chdir(workspace)
        yield str(workspace)
    finally:
        os.chdir(previous_cwd)
        shutil.rmtree(workspace, ignore_errors=True)


def test_run_plain_default_stdout_and_no_save():
    runner = CliRunner()
    with _isolated_fs():
        result = runner.invoke(main, ["run", "--prompt", "hello", "--backend", "mock"])
        assert result.exit_code == 0
        assert "mock response" in result.output
        assert not Path("broadside_ai_output").exists()


def test_run_json_output_shape():
    runner = CliRunner()
    with _isolated_fs():
        result = runner.invoke(
            main,
            ["run", "--prompt", "hello", "--backend", "mock", "--json-output"],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["schema_version"] == 1
        assert payload["status"] == "ok"
        assert payload["backend"] == "mock"
        assert payload["requested_strategy"] == "llm"
        assert payload["gather"]["n_requested"] == 3
        assert payload["saved_to"] is None


def test_run_save_flag_creates_output_tree():
    runner = CliRunner()
    with _isolated_fs():
        result = runner.invoke(main, ["run", "--prompt", "hello", "--backend", "mock", "--save"])
        assert result.exit_code == 0
        assert Path("broadside_ai_output").exists()


def test_run_context_file_injects_local_file_into_prompt():
    runner = CliRunner()
    with _isolated_fs():
        Path("RELEASE.md").write_text("Step one\nStep two", encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "run",
                "--prompt",
                "Plan the release",
                "--backend",
                "echo-prompt",
                "--raw",
                "--n",
                "1",
                "--context-file",
                "RELEASE.md",
            ],
        )

        assert result.exit_code == 0
        assert "Plan the release" in result.output
        assert "release_md:" in result.output
        assert "Step one" in result.output
        assert "Step two" in result.output


def test_validate_task_command():
    runner = CliRunner()
    with _isolated_fs():
        Path("valid.yaml").write_text("prompt: hello")
        Path("invalid.yaml").write_text("context: {}")

        valid = runner.invoke(main, ["validate-task", "valid.yaml"])
        invalid = runner.invoke(main, ["validate-task", "invalid.yaml"])

        assert valid.exit_code == 0
        assert "OK: valid.yaml" in valid.output
        assert invalid.exit_code == 1
        assert "FAIL: invalid.yaml" in invalid.output
