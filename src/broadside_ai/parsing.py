"""JSON parsing utility — extract structured data from agent outputs.

Agents are asked to return JSON when output_schema is set, but they don't
always comply perfectly. This module handles the common cases:
1. Clean JSON
2. JSON wrapped in markdown code fences
3. JSON with leading/trailing text
"""

from __future__ import annotations

import json
import re
from typing import Any


def try_parse_json(text: str) -> dict[str, Any] | None:
    """Attempt to parse JSON from agent output text.

    Returns the parsed dict on success, None on failure. Never raises.
    """
    if not text or not text.strip():
        return None

    stripped = text.strip()

    # 1. Try direct parse
    result = _try_loads(stripped)
    if result is not None:
        return result

    # 2. Try extracting from markdown code fences
    result = _try_fenced(stripped)
    if result is not None:
        return result

    # 3. Try finding a JSON object in the text
    result = _try_extract_object(stripped)
    if result is not None:
        return result

    return None


def _try_loads(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _try_fenced(text: str) -> dict[str, Any] | None:
    match = _FENCE_RE.search(text)
    if match:
        return _try_loads(match.group(1).strip())
    return None


def _try_extract_object(text: str) -> dict[str, Any] | None:
    """Find the first { ... } block and try to parse it."""
    start = text.find("{")
    if start == -1:
        return None
    # Find matching closing brace by counting nesting
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return _try_loads(text[start : i + 1])
    return None
