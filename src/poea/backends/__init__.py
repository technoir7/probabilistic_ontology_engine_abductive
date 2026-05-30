"""
Backend package — pluggable structure-learning backends for POE-A.

Use get_backend(name, **kwargs) to obtain a backend by name.

Available backends:
    null — trivial graph (Phase 7); no external dependencies.
    poe  — Probabilistic Ontology Engine (Phase 9); requires POE installed.
"""
from __future__ import annotations

from .interface import StructureLearningBackend
from .null_backend import NullBackend


def get_backend(name: str, **kwargs) -> StructureLearningBackend:
    """
    Return a backend instance by name.

    ``kwargs`` are forwarded to the backend constructor, allowing callers to
    pass e.g. ``domain_id``, ``db_path``, or ``random_seed`` for the POE backend.

    Raises ValueError for unknown backend names.
    Raises ImportError (wrapped in ValueError) if the POE backend is requested
    but POE is not installed.
    """
    if name == "null":
        return NullBackend()

    if name == "poe":
        try:
            from .poe_backend import POEBackend
        except ImportError as exc:
            raise ValueError(
                f"Backend 'poe' requires POE to be installed:\n"
                f"  pip install -e ../probabilistic_ontology_engine\n"
                f"Original error: {exc}"
            ) from exc
        return POEBackend(**kwargs)

    raise ValueError(
        f"Unknown backend: {name!r}. Available: ['null', 'poe']"
    )


__all__ = ["StructureLearningBackend", "NullBackend", "get_backend"]
