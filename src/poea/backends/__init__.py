"""
Backend package — pluggable structure-learning backends for POE-A.

Use get_backend(name) to obtain a backend by name.
"""
from __future__ import annotations

from .interface import StructureLearningBackend
from .null_backend import NullBackend

_REGISTRY: dict[str, type] = {
    "null": NullBackend,
}


def get_backend(name: str) -> StructureLearningBackend:
    """
    Return a backend instance by name.

    Raises ValueError for unknown backend names.
    Available backends: 'null'.  The 'poe' backend is added in Phase 9.
    """
    cls = _REGISTRY.get(name)
    if cls is None:
        available = ", ".join(f"'{k}'" for k in sorted(_REGISTRY))
        raise ValueError(
            f"Unknown backend: {name!r}. Available: [{available}]"
        )
    return cls()


__all__ = ["StructureLearningBackend", "NullBackend", "get_backend"]
