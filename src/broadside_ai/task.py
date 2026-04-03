"""Task definition - the unit of work that gets scattered."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class Task(BaseModel):
    """A tightly scoped unit of work with a clear, verifiable output."""

    prompt: str = Field(description="The instruction each scattered agent receives.")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs injected into the prompt. Grounding data.",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional JSON-schema-like dict describing expected output shape. "
            "Used to validate agent responses and make synthesis tractable."
        ),
    )
    model_config = {"extra": "forbid"}

    def render_prompt(self) -> str:
        """Build the full prompt string sent to each agent."""
        parts = [self.prompt]
        if self.context:
            parts.append("\n--- Context ---")
            for key, value in self.context.items():
                parts.append(f"{key}: {value}")
        if self.output_schema:
            parts.append("\n--- Expected Output Format ---")
            parts.append(
                "Respond with valid JSON matching this schema. "
                "Do not include any text outside the JSON object."
            )
            parts.append(json.dumps(self.output_schema, indent=2))
        return "\n".join(parts)
