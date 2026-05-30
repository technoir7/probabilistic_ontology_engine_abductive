"""
Promotion rules: candidate → active or suppressed.

Only concepts with status='candidate' are evaluated.
Concepts that are merged_into or rejected are left unchanged.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .schemas import ConceptEntry


def promote(
    entries: list[ConceptEntry],
    min_confidence: float = 0.75,
    min_evidence: int = 2,
    max_active: int = 30,
) -> tuple[list[ConceptEntry], dict[str, int], list[dict[str, Any]]]:
    """
    Promote candidate concepts to active or suppressed.

    Confidence is checked before evidence count so that a concept failing
    both thresholds is counted once under 'by_confidence'.

    After threshold evaluation, if the number of active concepts exceeds
    max_active, the lowest-confidence active concepts are suppressed until
    the cap is met ('by_cap').

    Returns ``(entries, counts, events)`` where:
    - counts has keys 'by_confidence', 'by_evidence', 'by_cap'
    - events is a list of promotion event dicts (one per evaluated candidate,
      plus one per concept suppressed by the cap)
    """
    counts = {"by_confidence": 0, "by_evidence": 0, "by_cap": 0}
    events: list[dict[str, Any]] = []
    criteria = {
        "min_confidence": min_confidence,
        "min_evidence": min_evidence,
        "max_active": max_active,
    }
    now = datetime.now(timezone.utc).isoformat()

    for entry in entries:
        if entry.status != "candidate":
            continue

        actual = {
            "confidence": entry.confidence,
            "evidence_count": len(entry.supporting_evidence_ids),
        }

        if entry.confidence < min_confidence:
            entry.status = "suppressed"
            counts["by_confidence"] += 1
            event_type = "suppressed_by_confidence"
        elif len(entry.supporting_evidence_ids) < min_evidence:
            entry.status = "suppressed"
            counts["by_evidence"] += 1
            event_type = "suppressed_by_evidence"
        else:
            entry.status = "active"
            event_type = "promoted_to_active"

        events.append(
            {
                "event_id": str(uuid.uuid4()),
                "concept_id": entry.concept_id,
                "concept_name": entry.name,
                "event_type": event_type,
                "criteria": criteria,
                "actual_values": actual,
                "created_at": now,
            }
        )

    # Hard cap: suppress the lowest-confidence active concepts beyond max_active.
    active_entries = [e for e in entries if e.status == "active"]
    if len(active_entries) > max_active:
        active_entries.sort(key=lambda e: (e.confidence, e.name))
        overflow = active_entries[: len(active_entries) - max_active]
        overflow_ids = {e.concept_id for e in overflow}
        for entry in entries:
            if entry.concept_id in overflow_ids:
                entry.status = "suppressed"
                counts["by_cap"] += 1
                events.append(
                    {
                        "event_id": str(uuid.uuid4()),
                        "concept_id": entry.concept_id,
                        "concept_name": entry.name,
                        "event_type": "suppressed_by_cap",
                        "criteria": criteria,
                        "actual_values": {
                            "confidence": entry.confidence,
                            "evidence_count": len(entry.supporting_evidence_ids),
                        },
                        "created_at": now,
                    }
                )

    return entries, counts, events
