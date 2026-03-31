"""Tests for gather — result normalization."""

from broadside_ai.backends.base import AgentResult
from broadside_ai.gather import gather


def _make_result(text: str = "hello", tokens: int = 100) -> AgentResult:
    return AgentResult(
        text=text,
        tokens_in=tokens,
        tokens_out=tokens,
        latency_ms=50.0,
        model="test-model",
        backend="test",
    )


def test_gather_basic():
    results = [_make_result("a"), _make_result("b"), _make_result("c")]
    g = gather(results, wall_clock_ms=150.0, n_requested=3)
    assert g.n_completed == 3
    assert g.n_failed == 0
    assert g.texts == ["a", "b", "c"]
    assert g.total_tokens == 600  # 3 * (100 in + 100 out)


def test_gather_with_failures():
    results = [_make_result("a")]
    g = gather(results, wall_clock_ms=100.0, n_requested=3)
    assert g.n_completed == 1
    assert g.n_failed == 2


def test_gather_summary():
    results = [_make_result()]
    g = gather(results, wall_clock_ms=100.0)
    s = g.summary()
    assert "completed" in s
    assert "total_tokens" in s


def test_gather_without_schema_no_parsing():
    """Without output_schema, parsed_outputs stays empty."""
    results = [_make_result('{"key": "val"}')]
    g = gather(results, wall_clock_ms=100.0)
    assert g.parsed_outputs == []
    assert g.n_parsed == 0


def test_gather_with_schema_parses_json():
    """With output_schema, JSON outputs are parsed."""
    results = [
        _make_result('{"label": "spam", "confidence": 0.9}'),
        _make_result('{"label": "ham", "confidence": 0.3}'),
    ]
    schema = {"label": "string", "confidence": "float"}
    g = gather(results, wall_clock_ms=100.0, n_requested=2, output_schema=schema)
    assert g.n_parsed == 2
    assert g.parsed_outputs[0] == {"label": "spam", "confidence": 0.9}
    assert g.parsed_outputs[1] == {"label": "ham", "confidence": 0.3}
    # Also stored on AgentResult
    assert g.results[0].parsed == {"label": "spam", "confidence": 0.9}


def test_gather_with_schema_unparseable():
    """Non-JSON outputs get None in parsed_outputs."""
    results = [
        _make_result('{"label": "spam"}'),
        _make_result("just plain text"),
    ]
    schema = {"label": "string"}
    g = gather(results, wall_clock_ms=100.0, n_requested=2, output_schema=schema)
    assert g.n_parsed == 1
    assert g.parsed_outputs[0] == {"label": "spam"}
    assert g.parsed_outputs[1] is None


def test_gather_summary_includes_parsed():
    """Summary includes n_parsed when parsing was done."""
    results = [_make_result('{"x": 1}')]
    g = gather(results, wall_clock_ms=100.0, output_schema={"x": "int"})
    s = g.summary()
    assert "n_parsed" in s
    assert s["n_parsed"] == 1
