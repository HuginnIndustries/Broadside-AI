"""Task file validator for Broadside-AI."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from broadside_ai.task import Task

VALID_CATEGORIES = {"creative", "analytical", "classification", "summarization", "code_review"}
VALID_STRATEGIES = {"llm", "consensus", "voting", "weighted_merge"}


def validate_task_file(path: str) -> list[str]:
    """Validate a YAML task file. Returns a list of human-readable errors."""
    errors: list[str] = []
    file_path = Path(path)

    if not file_path.exists():
        return [f"File not found: {path}"]

    try:
        data = yaml.safe_load(file_path.read_text())
    except yaml.YAMLError as exc:
        return [f"Invalid YAML: {exc}"]

    if not isinstance(data, dict):
        return ["Task file must be a YAML mapping"]

    if "prompt" not in data:
        errors.append("Missing required field: prompt")
    elif not isinstance(data["prompt"], str) or len(data["prompt"].strip()) == 0:
        errors.append("prompt must be a non-empty string")

    task_fields = {key: value for key, value in data.items() if key != "meta"}
    try:
        Task(**task_fields)
    except Exception as exc:
        errors.append(f"Task validation failed: {exc}")

    meta = data.get("meta", {})
    if meta:
        if "name" not in meta:
            errors.append("meta.name is recommended")
        if "category" in meta and meta["category"] not in VALID_CATEGORIES:
            errors.append(f"meta.category '{meta['category']}' not in {VALID_CATEGORIES}")
        if "recommended_strategy" in meta and meta["recommended_strategy"] not in VALID_STRATEGIES:
            errors.append(
                f"meta.recommended_strategy '{meta['recommended_strategy']}' "
                f"not in {VALID_STRATEGIES}"
            )
        if "recommended_n" in meta:
            recommended_n = meta["recommended_n"]
            if not isinstance(recommended_n, int) or recommended_n < 1:
                errors.append("meta.recommended_n must be a positive integer")
            elif recommended_n > 10:
                errors.append(
                    f"meta.recommended_n is {recommended_n}. "
                    "Performance plateaus at 3-5. Are you sure?"
                )

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: broadside-ai validate-task <task_file.yaml> [...]")
        sys.exit(1)

    all_valid = True
    for path in sys.argv[1:]:
        errors = validate_task_file(path)
        if errors:
            print(f"FAIL: {path}")
            for error in errors:
                print(f"  - {error}")
            all_valid = False
        else:
            print(f"OK: {path}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
