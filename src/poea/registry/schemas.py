from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field

ConceptStatus = Literal["candidate", "active", "suppressed", "merged_into", "rejected"]


class ConceptEntry(BaseModel):
    """
    A concept in the registry.

    Each unique concept name gets one entry.  duplicate_count tracks how many
    times that name was independently proposed across batches; supporting_evidence_ids
    is the union across all proposals.
    """

    concept_id: str
    name: str
    definition: str
    confidence: float
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    occurrence_count: int = 1
    status: ConceptStatus = "candidate"
    merged_into: str | None = None
    source_concept_ids: list[str] = Field(default_factory=list)


class RegistryMetrics(BaseModel):
    raw_proposal_count: int
    unique_names_raw: int
    exact_duplicates_merged: int
    semantic_concepts_merged: int
    rejected: int
    suppressed_by_confidence: int
    suppressed_by_evidence: int
    suppressed_by_cap: int = 0
    active_canonical_count: int
    promotion_confidence_threshold: float
    min_supporting_evidence: int
    max_active_concepts: int = 30


def concept_id_from_name(name: str) -> str:
    """Deterministic 16-char hex ID from concept name (normalised)."""
    return hashlib.sha256(name.strip().lower().encode()).hexdigest()[:16]
