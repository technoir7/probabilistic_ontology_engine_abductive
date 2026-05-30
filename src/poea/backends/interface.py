"""
Backend interface protocol for POE-A structure-learning backends.

All backends must implement StructureLearningBackend.  POE-A itself only
depends on this protocol — never on backend internals.

Key constraint: backends receive ``scored_evidence``, not raw evidence text.
The evidence scoring stage (Phase 6) translates text into concept-keyed
assignments before the backend is called.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class StructureLearningBackend(Protocol):
    """
    Minimal contract that all structure-learning backends must satisfy.

    Parameters
    ----------
    concepts:
        Active concepts from the POE-A registry.  Each entry is a dict with
        at least ``concept_id`` and ``name``.
    scored_evidence:
        Evidence records with concept assignments produced by Phase 6.
        Each entry has ``evidence_id`` and ``assignments`` (list of dicts
        with ``concept_id``, ``variable_name``, ``assigned_value``,
        ``confidence``, ``missingness``).
    graph:
        Graph artifact returned by a previous ``learn_graph`` call.
    config:
        Optional backend-specific configuration.
    """

    def learn_graph(
        self,
        concepts: Sequence[Mapping[str, Any]],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """
        Learn a graph structure from concepts and scored evidence.

        Returns a graph artifact dict.  The dict must contain at least:
        - ``backend`` (str): the backend name
        - ``nodes`` (list): one entry per concept
        - ``edges`` (list): directed edges between nodes
        - ``node_count`` (int)
        - ``edge_count`` (int)
        """
        ...

    def score_hypotheses(
        self,
        graph: Mapping[str, Any],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """
        Score hypotheses given a graph and evidence assignments.

        Returns a hypothesis scoring artifact dict.
        """
        ...
