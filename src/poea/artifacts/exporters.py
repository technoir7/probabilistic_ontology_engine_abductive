"""
Concept-to-Node Translation — Phase 8.

Translates active concepts from the registry into POE-compatible node objects.
The output is a nodes artifact consumed by structure-learning backends,
including the Phase 9 POE adapter.

Default priors:
    prior_probability = 0.5  (maximum uncertainty — no evidence activation yet)
    boolean_state    = None  (unobserved)
    source           = "poea_induced"

These values are not hardcoded to any domain.  They are defaults for any
abductively-induced concept before evidence activation has been applied.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..registry.schemas import ConceptEntry


def concept_entry_to_node(concept: ConceptEntry) -> dict[str, Any]:
    """
    Convert a single ConceptEntry to a node dict.

    The node dict is the unit consumed by structure-learning backends.
    Fields match the Phase 8 documented format plus ``concept_id`` for
    POE-A internal traceability.
    """
    return {
        "concept_id": concept.concept_id,
        "name": concept.name,
        "definition": concept.definition,
        "prior_probability": 0.5,
        "boolean_state": None,
        "source": "poea_induced",
    }


def concepts_to_nodes(
    concepts: list[ConceptEntry],
    domain_tag: str = "unknown",
) -> dict[str, Any]:
    """
    Convert a list of active ConceptEntry objects to a nodes artifact dict.

    The artifact format:
    {
        "domain_tag": "...",
        "node_count": N,
        "nodes": [{"name": ..., "definition": ..., ...}, ...]
    }
    """
    nodes = [concept_entry_to_node(c) for c in concepts]
    return {
        "domain_tag": domain_tag,
        "node_count": len(nodes),
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "poea_induced",
        },
        "nodes": nodes,
    }


def load_canonical_concepts(path: str | Path) -> tuple[list[ConceptEntry], str]:
    """
    Load active concepts from a canonical_concepts.json artifact.

    Returns (concepts, domain_tag) where domain_tag is taken from the
    artifact metadata if present, otherwise "unknown".
    """
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)

    raw_concepts = data.get("concepts", [])
    concepts = [ConceptEntry.model_validate(c) for c in raw_concepts]

    metadata = data.get("metadata", {})
    domain_tag = metadata.get("domain_tag", "unknown")

    return concepts, domain_tag


def write_nodes(path: str | Path, nodes_artifact: dict[str, Any]) -> None:
    """Write a nodes artifact to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(nodes_artifact, f, indent=2, ensure_ascii=False)
