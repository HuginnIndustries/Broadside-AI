"""Task file validator — validates YAML task definitions against the schema.

Usage: python -m broadside_ai.task_validator tasks/my_task.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from broadside_ai.task import Task

VALID_CATEGORIES = {"creative", "analytical", "classification", "summarization", "code_review"}
VALID_STRATEGIES = {"llm", "consensus", "voting"}


def validate_task_file(path: str) -> list[str]:
    """Validate a YAML task file. Returns list of errors (empty = valid)."""
    errors: list[str] = []
    p = Path(path)

    if not p.exists():
        return [f"File not found: {path}"]

    try:
        data = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        return [f"Invalid YAML: {e}"]

    if not isinstance(data, dict):
        return ["Task file must be a YAML mapping"]

    # Validate the Task fields
    if "prompt" not in data:
        errors.append("Missing required field: prompt")
    elif not isinstance(data["prompt"], str) or len(data["prompt"].strip()) == 0:
        errors.append("prompt must be a non-empty string")

    # Try to construct the Task object
    task_fields = {k: v for k, v in data.items() if k != "meta"}
    try:
        Task(**task_fields)
    except Exception as e:
        errors.append(f"Task validation failed: {e}")

    # Validate metadata if present
    meta = data.get("meta", {})
    if meta:
        if "name" not in meta:
            errors.append("meta.name is recommended")
        if "category" in meta and meta["category"] not in VALID_CATEGORIES:
            errors.append(
                f"meta.category '{meta['category']}' not in {VALID_CATEGORIES}"
            )
        if "recommended_strategy" in meta and meta["recommended_strategy"] not in VALID_STRATEGIES:
            errors.append(
                f"meta.recommended_strategy '{meta['recommended_strategy']}' "
                f"not in {VALID_STRATEGIES}"
            )
        if "recommended_n" in meta:
            n = meta["recommended_n"]
            if not isinstance(n, int) or n < 1:
                errors.append("meta.recommended_n must be a positive integer")
            elif n > 10:
                errors.append(
                    f"meta.recommended_n is {n}. Performance plateaus at 3-5. "
                    f"Are you sure?"
                )

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m broadside_ai.task_validator <task_file.yaml> [...]")
        sys.exit(1)

    all_valid = True
    for path in sys.argv[1:]:
        errors = validate_task_file(path)
        if errors:
            print(f"FAIL: {path}")
            for err in errors:
                print(f"  - {err}")
            all_valid = False
        else:
            print(f"OK: {path}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
