"""Backend registry — pluggable LLM providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from broadside.backends.base import Backend

_REGISTRY: dict[str, type[Backend]] = {}


def register(name: str, cls: type[Backend]) -> None:
    _REGISTRY[name] = cls


def get_backend(name: str, **kwargs: object) -> Backend:
    """Look up a backend by name, instantiate with kwargs.

    Backends that require optional dependencies (anthropic, openai) raise
    a clear ImportError if the extra isn't installed.
    """
    if name not in _REGISTRY:
        # Lazy-load built-in backends on first access
        _try_load_builtin(name)

    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise ValueError(
            f"Unknown backend '{name}'. Available: {available}. "
            f"You may need to install an extra: pip install broadside[{name}]"
        )
    return _REGISTRY[name](**kwargs)


def _try_load_builtin(name: str) -> None:
    """Attempt to import a built-in backend module to trigger registration."""
    builtins = {
        "ollama": "broadside.backends.ollama",
        "anthropic": "broadside.backends.anthropic",
        "openai": "broadside.backends.openai",
    }
    if name in builtins:
        try:
            __import__(builtins[name])
        except ImportError:
            pass
