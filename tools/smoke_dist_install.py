"""Install the built wheel in a clean venv and smoke test the CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SMOKE_ROOT = ROOT / ".smoke-dist"


def _run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd or ROOT, check=True)


def _venv_paths(venv_dir: Path) -> tuple[Path, Path]:
    if sys.platform == "win32":
        scripts_dir = venv_dir / "Scripts"
        return scripts_dir / "python.exe", scripts_dir / "broadside-ai.exe"

    bin_dir = venv_dir / "bin"
    return bin_dir / "python", bin_dir / "broadside-ai"


def _wheel_path() -> Path:
    wheels = sorted(DIST.glob("broadside_ai-*.whl"))
    if not wheels:
        raise FileNotFoundError("No built wheel found in dist/. Run `python -m build` first.")
    return wheels[-1]


def main() -> None:
    wheel = _wheel_path()
    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT)

    venv_dir = SMOKE_ROOT / "venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    python_exe, broadside_exe = _venv_paths(venv_dir)

    _run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(python_exe), "-m", "pip", "install", str(wheel)])
    _run([str(broadside_exe), "--help"])
    _run([str(python_exe), "-m", "broadside_ai", "--help"])
    _run([str(python_exe), "-m", "broadside_ai", "validate-task", "tasks/_template.yaml"])


if __name__ == "__main__":
    main()
