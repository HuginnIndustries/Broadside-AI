"""Allow running Broadside as `python -m broadside`.

This always works, even when the `broadside` CLI script isn't on PATH —
which is the default on Windows.
"""

from broadside.cli import main

main()
