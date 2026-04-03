"""Tests for task definition and prompt rendering."""

import pytest

from broadside_ai.task import Task


def test_basic_task():
    task = Task(prompt="Hello world")
    assert task.prompt == "Hello world"
    assert task.context == {}
    assert task.output_schema is None


def test_render_prompt_no_context():
    task = Task(prompt="Write a poem")
    assert task.render_prompt() == "Write a poem"


def test_render_prompt_with_context():
    task = Task(
        prompt="Compare these tools",
        context={"tools": "hammer, screwdriver", "criteria": "durability, cost"},
    )
    rendered = task.render_prompt()
    assert "Compare these tools" in rendered
    assert "tools: hammer, screwdriver" in rendered
    assert "criteria: durability, cost" in rendered


def test_render_prompt_with_schema():
    task = Task(
        prompt="Classify this",
        output_schema={"label": "string", "confidence": "float"},
    )
    rendered = task.render_prompt()
    assert "Expected Output Format" in rendered
    assert "Respond with valid JSON" in rendered
    assert '"label": "string"' in rendered


def test_task_rejects_extra_fields():
    with pytest.raises(Exception):
        Task(prompt="Hello", bogus_field="nope")
