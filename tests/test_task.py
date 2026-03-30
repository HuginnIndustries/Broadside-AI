"""Tests for task definition and prompt rendering."""

from broadside_ai.task import Task


def test_basic_task():
    t = Task(prompt="Hello world")
    assert t.prompt == "Hello world"
    assert t.context == {}
    assert t.output_schema is None


def test_render_prompt_no_context():
    t = Task(prompt="Write a poem")
    assert t.render_prompt() == "Write a poem"


def test_render_prompt_with_context():
    t = Task(
        prompt="Compare these tools",
        context={"tools": "hammer, screwdriver", "criteria": "durability, cost"},
    )
    rendered = t.render_prompt()
    assert "Compare these tools" in rendered
    assert "tools: hammer, screwdriver" in rendered
    assert "criteria: durability, cost" in rendered


def test_render_prompt_with_schema():
    t = Task(
        prompt="Classify this",
        output_schema={"label": "string", "confidence": "float"},
    )
    rendered = t.render_prompt()
    assert "Expected Output Format" in rendered


def test_task_rejects_extra_fields():
    import pytest

    with pytest.raises(Exception):
        Task(prompt="Hello", bogus_field="nope")
