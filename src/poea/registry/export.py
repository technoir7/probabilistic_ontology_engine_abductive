"""
Orchestrate the full registry build pipeline and write output artifacts.

Pipeline:
    load raw concepts
        ↓
    apply consolidation (semantic clusters + rejections)
        ↓
    promote (candidate → active / suppressed)
        ↓
    write concept_registry.json   (all entries, all statuses, promotion_events)
    write canonical_concepts.json (active entries only)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .consolidation import ConsolidationMap, apply_consolidation
from .lifecycle import promote
from .schemas import ConceptEntry, RegistryMetrics
from .store import load_raw_concepts


def build_registry(
    raw_concepts_path: str | Path,
    consolidation_map_path: str | Path | None,
    output_dir: str | Path,
    promotion_confidence: float = 0.75,
    min_evidence: int = 2,
    max_active: int = 30,
) -> RegistryMetrics:
    """
    Run the full consolidation pipeline and write both output artifacts.

    Returns a RegistryMetrics summary.
    """
    raw_path = Path(raw_concepts_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: load and name-deduplicate
    entries, raw_proposal_count = load_raw_concepts(raw_path)
    unique_names_raw = len(entries)
    exact_duplicates_merged = raw_proposal_count - unique_names_raw

    # Step 2: consolidate
    cmap = (
        ConsolidationMap.from_yaml(consolidation_map_path)
        if consolidation_map_path and Path(consolidation_map_path).exists()
        else ConsolidationMap.empty()
    )
    entries, semantic_merged = apply_consolidation(entries, cmap)

    # Step 3: promote
    entries, suppression_counts, promotion_events = promote(
        entries,
        min_confidence=promotion_confidence,
        min_evidence=min_evidence,
        max_active=max_active,
    )

    # Compute summary metrics
    rejected = sum(1 for e in entries if e.status == "rejected")
    active_count = sum(1 for e in entries if e.status == "active")

    metrics = RegistryMetrics(
        raw_proposal_count=raw_proposal_count,
        unique_names_raw=unique_names_raw,
        exact_duplicates_merged=exact_duplicates_merged,
        semantic_concepts_merged=semantic_merged,
        rejected=rejected,
        suppressed_by_confidence=suppression_counts["by_confidence"],
        suppressed_by_evidence=suppression_counts["by_evidence"],
        suppressed_by_cap=suppression_counts["by_cap"],
        active_canonical_count=active_count,
        promotion_confidence_threshold=promotion_confidence,
        min_supporting_evidence=min_evidence,
        max_active_concepts=max_active,
    )

    now = datetime.now(timezone.utc).isoformat()

    # Write full registry
    registry_path = out_dir / "concept_registry.json"
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "source": str(raw_path),
                    "consolidation_map": str(consolidation_map_path) if consolidation_map_path else None,
                    "promotion_confidence": promotion_confidence,
                    "min_supporting_evidence": min_evidence,
                    "max_active_concepts": max_active,
                    "created_at": now,
                },
                "metrics": metrics.model_dump(),
                "promotion_events": promotion_events,
                "entries": [_entry_to_dict(e) for e in _sorted_entries(entries)],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Write canonical concepts (active only)
    active = [e for e in entries if e.status == "active"]
    canonical_path = out_dir / "canonical_concepts.json"
    with canonical_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "source": str(raw_path),
                    "concept_count": len(active),
                    "created_at": now,
                },
                "concepts": [_entry_to_dict(e) for e in _sorted_entries(active)],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return metrics


def write_registry_artifacts(
    entries: list[ConceptEntry],
    promotion_events: list[dict[str, Any]],
    existing_meta: dict,
    output_dir: Path,
    promotion_confidence: float,
    min_evidence: int,
    max_active: int,
) -> int:
    """
    Write updated concept_registry.json and canonical_concepts.json from existing entries.

    Used by ``registry promote`` to persist re-promotion results without
    re-running the full consolidation pipeline.  Returns the active concept count.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    active_count = sum(1 for e in entries if e.status == "active")

    # Merge new events with any existing ones from prior runs
    prior_events: list[dict] = existing_meta.get("promotion_events", [])
    all_events = prior_events + promotion_events

    updated_meta = {
        **existing_meta.get("metadata", {}),
        "promotion_confidence": promotion_confidence,
        "min_supporting_evidence": min_evidence,
        "max_active_concepts": max_active,
        "promoted_at": now,
    }

    # Rebuild metrics from entry statuses
    existing_metrics: dict = existing_meta.get("metrics", {})
    updated_metrics = {
        **existing_metrics,
        "suppressed_by_confidence": sum(1 for e in entries if e.status == "suppressed"),
        "suppressed_by_cap": sum(
            1 for ev in promotion_events if ev.get("event_type") == "suppressed_by_cap"
        ),
        "active_canonical_count": active_count,
        "promotion_confidence_threshold": promotion_confidence,
        "min_supporting_evidence": min_evidence,
        "max_active_concepts": max_active,
    }

    registry_path = out_dir / "concept_registry.json"
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": updated_meta,
                "metrics": updated_metrics,
                "promotion_events": all_events,
                "entries": [_entry_to_dict(e) for e in _sorted_entries(entries)],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    active = [e for e in entries if e.status == "active"]
    canonical_path = out_dir / "canonical_concepts.json"
    with canonical_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "source": existing_meta.get("metadata", {}).get("source", ""),
                    "concept_count": len(active),
                    "created_at": now,
                },
                "concepts": [_entry_to_dict(e) for e in _sorted_entries(active)],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return active_count


def _entry_to_dict(entry: ConceptEntry) -> dict:
    return {
        "concept_id": entry.concept_id,
        "name": entry.name,
        "definition": entry.definition,
        "confidence": entry.confidence,
        "supporting_evidence_ids": entry.supporting_evidence_ids,
        "occurrence_count": entry.occurrence_count,
        "status": entry.status,
        "merged_into": entry.merged_into,
        "source_concept_ids": entry.source_concept_ids,
    }


def _sorted_entries(entries: list[ConceptEntry]) -> list[ConceptEntry]:
    status_order = {"active": 0, "candidate": 1, "suppressed": 2, "rejected": 3, "merged_into": 4}
    return sorted(entries, key=lambda e: (status_order.get(e.status, 9), -e.confidence))
