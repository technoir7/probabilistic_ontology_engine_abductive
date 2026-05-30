"""
NullBackend — a trivial structure-learning backend for testing.

Returns one node per concept and no edges.  Allows the full POE-A pipeline
to be exercised end-to-end without a real structure-learning installation.

The NullBackend satisfies the StructureLearningBackend protocol and can be
used anywhere a real backend is expected.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


class NullBackend:
    """
    Trivial backend: one node per concept, zero edges.

    learn_graph converts each concept entry into a node with default priors
    (prior_probability=0.5, boolean_state=None) and returns an empty edge list.

    score_hypotheses returns an empty hypothesis list with an explanatory note.
    """

    BACKEND_NAME = "null"

    def learn_graph(
        self,
        concepts: Sequence[Mapping[str, Any]],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """
        Return a graph with one node per concept and no edges.

        Each node includes ``prior_probability=0.5`` and ``boolean_state=None``
        to express maximum uncertainty, consistent with Phase 8's node format.
        """
        nodes = [
            {
                "concept_id": c.get("concept_id", ""),
                "name": c.get("name", ""),
                "definition": c.get("definition", ""),
                "prior_probability": 0.5,
                "boolean_state": None,
                "source": "poea_induced",
            }
            for c in concepts
        ]

        return {
            "backend": self.BACKEND_NAME,
            "node_count": len(nodes),
            "edge_count": 0,
            "nodes": nodes,
            "edges": [],
            "metadata": {
                "evidence_count": len(scored_evidence),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def score_hypotheses(
        self,
        graph: Mapping[str, Any],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """
        Return an empty hypothesis list.

        The NullBackend does not perform probabilistic inference.
        """
        return {
            "backend": self.BACKEND_NAME,
            "hypothesis_count": 0,
            "hypotheses": [],
            "note": "NullBackend does not perform hypothesis scoring.",
        }
