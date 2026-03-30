"""Allow running Broadside as `python -m broadside_ai`.

This always works, even when the `broadside-ai` CLI script isn't on PATH —
which is the default on Windows.
"""

from broadside_ai.cli import main

main()
