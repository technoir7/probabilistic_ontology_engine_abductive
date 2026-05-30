"""
Load raw_concepts.json and produce a de-duplicated list of ConceptEntry objects.

Name deduplication happens here: if the same concept name was proposed in
multiple batches, the entries are merged into one (max confidence, union of
evidence IDs, summed occurrence count).  The raw proposal count before merging
is returned alongside the entries so callers can report exact-duplicate metrics.

Also provides load_registry() for reading an existing concept_registry.json.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .schemas import ConceptEntry, concept_id_from_name


def load_raw_concepts(path: str | Path) -> tuple[list[ConceptEntry], int]:
    """
    Load and name-deduplicate concepts from a raw_concepts.json artifact.

    Returns ``(entries, raw_proposal_count)`` where ``raw_proposal_count`` is
    the total number of proposals before name deduplication — i.e. the length
    of the ``concepts`` array in the source file.
    """
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)

    raw: list[dict] = data.get("concepts", [])
    raw_proposal_count = len(raw)

    # Group all proposals by name.
    groups: dict[str, list[dict]] = defaultdict(list)
    for proposal in raw:
        groups[proposal["name"]].append(proposal)

    entries: list[ConceptEntry] = []
    for name, proposals in groups.items():
        best = max(proposals, key=lambda p: p["confidence"])

        # Union of evidence IDs preserving insertion order.
        seen: set[str] = set()
        evidence: list[str] = []
        for p in proposals:
            for eid in p.get("supporting_evidence_ids", []):
                if eid not in seen:
                    evidence.append(eid)
                    seen.add(eid)

        entries.append(
            ConceptEntry(
                concept_id=concept_id_from_name(name),
                name=name,
                definition=best["definition"],
                confidence=max(p["confidence"] for p in proposals),
                supporting_evidence_ids=evidence,
                occurrence_count=len(proposals),
            )
        )

    return entries, raw_proposal_count


def load_registry(path: str | Path) -> tuple[list[ConceptEntry], dict]:
    """
    Load ConceptEntry objects and metadata from a concept_registry.json artifact.

    Returns ``(entries, metadata)`` where metadata is the top-level dict
    (minus the entries list) so callers can preserve it on re-write.
    """
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)

    raw_entries: list[dict] = data.get("entries", [])
    entries = [ConceptEntry.model_validate(e) for e in raw_entries]
    meta = {k: v for k, v in data.items() if k != "entries"}
    return entries, meta
