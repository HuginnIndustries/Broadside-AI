"""CLI contract tests for Broadside-AI."""

from __future__ import annotations

import json
import shutil
from contextlib import contextmanager
from pathlib import Path

from click.testing import CliRunner

from broadside_ai.cli import main

_TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


@contextmanager
def _isolated_fs(runner: CliRunner):
    _TEST_TEMP_ROOT.mkdir(exist_ok=True)
    with runner.isolated_filesystem(temp_dir=str(_TEST_TEMP_ROOT)) as workspace:
        try:
            yield workspace
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


def test_run_plain_default_stdout_and_no_save():
    runner = CliRunner()
    with _isolated_fs(runner):
        result = runner.invoke(main, ["run", "--prompt", "hello", "--backend", "mock"])
        assert result.exit_code == 0
        assert "mock response" in result.output
        assert not Path("broadside_ai_output").exists()


def test_run_json_output_shape():
    runner = CliRunner()
    with _isolated_fs(runner):
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
    with _isolated_fs(runner):
        result = runner.invoke(main, ["run", "--prompt", "hello", "--backend", "mock", "--save"])
        assert result.exit_code == 0
        assert Path("broadside_ai_output").exists()


def test_validate_task_command():
    runner = CliRunner()
    with _isolated_fs(runner):
        Path("valid.yaml").write_text("prompt: hello")
        Path("invalid.yaml").write_text("context: {}")

        valid = runner.invoke(main, ["validate-task", "valid.yaml"])
        invalid = runner.invoke(main, ["validate-task", "invalid.yaml"])

        assert valid.exit_code == 0
        assert "OK: valid.yaml" in valid.output
        assert invalid.exit_code == 1
        assert "FAIL: invalid.yaml" in invalid.output
