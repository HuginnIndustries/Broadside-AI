"""Tests for execution-mode defaults."""

from broadside_ai.execution import is_ollama_cloud_model, resolve_parallel_mode


def test_detects_ollama_cloud_models():
    assert is_ollama_cloud_model("nemotron-3-super:cloud")
    assert is_ollama_cloud_model("gpt-oss-20b-cloud")
    assert not is_ollama_cloud_model("gemma3:1b")


def test_defaults_non_ollama_backends_to_parallel():
    assert resolve_parallel_mode("anthropic") is True
    assert resolve_parallel_mode("openai") is True


def test_defaults_local_ollama_to_sequential():
    assert resolve_parallel_mode("ollama", {"model": "gemma3:1b"}) is False


def test_defaults_cloud_ollama_to_parallel():
    assert resolve_parallel_mode("ollama", {"model": "nemotron-3-super:cloud"}) is True


def test_explicit_mode_overrides_default():
    assert resolve_parallel_mode("ollama", {"model": "gemma3:1b"}, explicit=True) is True
    assert resolve_parallel_mode("anthropic", explicit=False) is False
