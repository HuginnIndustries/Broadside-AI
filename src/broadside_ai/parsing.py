"""JSON parsing helpers for structured Broadside-AI outputs."""

from __future__ import annotations

import json
import re
from typing import Any


def try_parse_json(text: str) -> dict[str, Any] | None:
    """Attempt to parse JSON from agent output text."""
    if not text or not text.strip():
        return None

    stripped = text.strip()
    result = _try_loads(stripped)
    if result is not None:
        return result

    result = _try_fenced(stripped)
    if result is not None:
        return result

    return _try_extract_object(stripped)


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
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return _try_loads(text[start : index + 1])
    return None
