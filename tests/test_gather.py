"""Tests for gather result normalization."""

from broadside_ai.gather import gather
from tests.conftest import make_result


def test_gather_basic():
    results = [make_result("a"), make_result("b"), make_result("c")]
    gathered = gather(results, wall_clock_ms=150.0, n_requested=3)
    assert gathered.n_requested == 3
    assert gathered.n_completed == 3
    assert gathered.n_failed == 0
    assert gathered.texts == ["a", "b", "c"]
    assert gathered.total_tokens == 600


def test_gather_with_failures():
    gathered = gather([make_result("a")], wall_clock_ms=100.0, n_requested=3)
    assert gathered.n_completed == 1
    assert gathered.n_failed == 2


def test_gather_parses_structured_outputs():
    schema = {"label": "string"}
    results = [make_result('{"label": "spam"}'), make_result("not json")]
    gathered = gather(results, wall_clock_ms=100.0, n_requested=2, output_schema=schema)
    assert gathered.n_parsed == 1
    assert gathered.parsed_outputs[0] == {"label": "spam"}
    assert gathered.parsed_outputs[1] is None


def test_gather_summary():
    gathered = gather([make_result()], wall_clock_ms=100.0, n_requested=1)
    summary = gathered.summary()
    assert summary["n_requested"] == 1
    assert summary["completed"] == 1
    assert summary["n_parsed"] == 0
