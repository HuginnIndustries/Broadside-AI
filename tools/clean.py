"""Cross-platform cleanup for local build and test artifacts."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DIRECTORIES = [
    ROOT / "build",
    ROOT / "dist",
    ROOT / ".pytest_cache",
    ROOT / ".ruff_cache",
    ROOT / ".mypy_cache",
    ROOT / "broadside_ai_output",
    ROOT / "python",
]

GLOB_PATTERNS = [
    "*.egg-info",
    "src/*.egg-info",
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "pytest-cache-files-*",
]


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


def main() -> None:
    for path in DIRECTORIES:
        _remove_path(path)

    for pattern in GLOB_PATTERNS:
        for path in ROOT.glob(pattern):
            _remove_path(path)


if __name__ == "__main__":
    main()
