"""Task definition — the unit of work that gets scattered."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Task(BaseModel):
    """A tightly scoped unit of work with a clear, verifiable output.

    A good task passes the "can you tell if it's done?" test. Not "research
    community platforms" but "compare these 10 platforms across 5 dimensions
    and return a structured table."
    """

    prompt: str = Field(
        description="The instruction each scattered agent receives."
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs injected into the prompt. Agents see these as grounding data.",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON-schema-like dict describing expected output shape. "
        "Used to validate agent responses and make synthesis tractable.",
    )
    model_config = {"extra": "forbid"}

    def render_prompt(self) -> str:
        """Build the full prompt string sent to each agent.

        Context is appended as a structured block so agents can reference it
        without the caller needing to do string formatting.
        """
        parts = [self.prompt]
        if self.context:
            parts.append("\n--- Context ---")
            for key, value in self.context.items():
                parts.append(f"{key}: {value}")
        if self.output_schema:
            parts.append("\n--- Expected Output Format ---")
            parts.append(str(self.output_schema))
        return "\n".join(parts)
