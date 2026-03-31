"""Tests for JSON parsing utility."""

from broadside_ai.parsing import try_parse_json


def test_valid_json():
    assert try_parse_json('{"key": "value"}') == {"key": "value"}


def test_json_with_whitespace():
    assert try_parse_json('  {"a": 1}  ') == {"a": 1}


def test_json_in_markdown_fence():
    text = '```json\n{"label": "spam", "confidence": 0.9}\n```'
    assert try_parse_json(text) == {"label": "spam", "confidence": 0.9}


def test_json_in_bare_fence():
    text = '```\n{"x": 1}\n```'
    assert try_parse_json(text) == {"x": 1}


def test_json_with_surrounding_text():
    text = 'Here is the result:\n{"answer": 42}\nHope that helps!'
    assert try_parse_json(text) == {"answer": 42}


def test_nested_json():
    text = '{"outer": {"inner": [1, 2, 3]}}'
    result = try_parse_json(text)
    assert result == {"outer": {"inner": [1, 2, 3]}}


def test_plain_text_returns_none():
    assert try_parse_json("This is not JSON at all") is None


def test_empty_string_returns_none():
    assert try_parse_json("") is None


def test_none_like_input():
    assert try_parse_json("   ") is None


def test_invalid_json_returns_none():
    assert try_parse_json("{bad json}") is None


def test_json_array_returns_none():
    """Only dicts are valid structured outputs, not arrays."""
    assert try_parse_json("[1, 2, 3]") is None


def test_numeric_returns_none():
    assert try_parse_json("42") is None
