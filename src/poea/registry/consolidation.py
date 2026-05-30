"""
Consolidation layer: exact-name deduplication, semantic cluster merging, rejection.

Operates on a list of ConceptEntry objects produced by store.load_raw_concepts.
All operations mutate entries in-place and return the same list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schemas import ConceptEntry, concept_id_from_name

# ---------------------------------------------------------------------------
# Consolidation map data model
# ---------------------------------------------------------------------------

@dataclass
class ConsolidationCluster:
    """
    A named cluster of concepts that should be merged into one canonical entry.

    ``members`` must include the canonical name itself.  Non-canonical members
    are merged into the canonical and their status is set to ``merged_into``.
    """
    canonical: str
    members: list[str]


@dataclass
class ConsolidationMap:
    """
    Full consolidation configuration: semantic clusters and rejected concept names.
    """
    clusters: list[ConsolidationCluster] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ConsolidationMap":
        with Path(path).open(encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        clusters = [
            ConsolidationCluster(
                canonical=c["canonical"],
                members=list(c.get("members", [c["canonical"]])),
            )
            for c in data.get("clusters", [])
        ]
        return cls(
            clusters=clusters,
            rejected=list(data.get("rejected", [])),
        )

    @classmethod
    def empty(cls) -> "ConsolidationMap":
        return cls()


# ---------------------------------------------------------------------------
# Consolidation operations
# ---------------------------------------------------------------------------

def apply_consolidation(
    entries: list[ConceptEntry],
    cmap: ConsolidationMap,
) -> tuple[list[ConceptEntry], int]:
    """
    Apply semantic cluster merges and rejections.

    For each cluster:
    - Non-canonical members are merged into the canonical concept.
    - The canonical entry absorbs their evidence IDs, occurrence count, and
      confidence (if a member's confidence is higher).
    - Non-canonical members get status='merged_into'.

    For each rejected name, the entry gets status='rejected'.

    Returns ``(entries, semantic_merged_count)`` where ``semantic_merged_count``
    is the number of entries whose status was changed to ``merged_into`` during
    semantic cluster processing.
    """
    entry_map: dict[str, ConceptEntry] = {e.concept_id: e for e in entries}
    semantic_merged = 0

    for cluster in cmap.clusters:
        canonical_id = concept_id_from_name(cluster.canonical)
        canonical = entry_map.get(canonical_id)
        if canonical is None:
            continue

        seen_evidence: set[str] = set(canonical.supporting_evidence_ids)
        merged_evidence: list[str] = list(canonical.supporting_evidence_ids)
        total_occurrences = canonical.occurrence_count

        for member_name in cluster.members:
            if member_name == cluster.canonical:
                continue
            member_id = concept_id_from_name(member_name)
            member = entry_map.get(member_id)
            if member is None:
                continue

            # Absorb evidence
            for eid in member.supporting_evidence_ids:
                if eid not in seen_evidence:
                    merged_evidence.append(eid)
                    seen_evidence.add(eid)

            total_occurrences += member.occurrence_count

            # Upgrade definition and confidence if this member is stronger
            if member.confidence > canonical.confidence:
                canonical.confidence = member.confidence
                canonical.definition = member.definition

            canonical.source_concept_ids.append(member_id)

            member.status = "merged_into"
            member.merged_into = canonical_id
            semantic_merged += 1

        canonical.supporting_evidence_ids = merged_evidence
        canonical.occurrence_count = total_occurrences

    for rejected_name in cmap.rejected:
        rejected_id = concept_id_from_name(rejected_name)
        entry = entry_map.get(rejected_id)
        if entry is not None:
            entry.status = "rejected"

    return entries, semantic_merged
