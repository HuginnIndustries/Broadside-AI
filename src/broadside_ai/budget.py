"""Budget circuit breaker - mandatory cost control for scatter/gather.

Scatter/gather multiplies API costs by design. Every scatter gets a budget.
No exceptions.
"""

from __future__ import annotations

import threading


class BudgetExceeded(Exception):
    """Raised when a scatter exceeds its token budget."""

    def __init__(self, limit: int, used: int) -> None:
        self.limit = limit
        self.used = used
        super().__init__(
            f"Scatter budget exceeded: {used:,} tokens used, limit was {limit:,}. "
            f"Remaining branches cancelled."
        )


class ScatterBudget:
    """Per-scatter token budget with thread-safe tracking.

    If max_tokens is None, the budget is unbounded (still tracks usage).
    """

    def __init__(self, max_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens
        self._used = 0
        self._lock = threading.Lock()

    def record(self, tokens: int) -> None:
        """Record tokens consumed by a branch. Raises if budget exceeded."""
        with self._lock:
            self._used += tokens
            if self.max_tokens is not None and self._used >= self.max_tokens:
                raise BudgetExceeded(self.max_tokens, self._used)

    @property
    def used(self) -> int:
        return self._used

    @property
    def exhausted(self) -> bool:
        if self.max_tokens is None:
            return False
        return self._used >= self.max_tokens

    @property
    def remaining(self) -> int | None:
        if self.max_tokens is None:
            return None
        return max(0, self.max_tokens - self._used)
