"""Tests for registry schema models and concept_id_from_name."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from poea.registry.schemas import ConceptEntry, RegistryMetrics, concept_id_from_name  # noqa: E501

# ---------------------------------------------------------------------------
# concept_id_from_name
# ---------------------------------------------------------------------------

def test_concept_id_from_name_deterministic():
    assert concept_id_from_name("AlphaMechanism") == concept_id_from_name("AlphaMechanism")


def test_concept_id_from_name_case_insensitive():
    assert concept_id_from_name("AlphaMechanism") == concept_id_from_name("alphamechanism")
    assert concept_id_from_name("AlphaMechanism") == concept_id_from_name("ALPHAMECHANISM")


def test_concept_id_from_name_strips_whitespace():
    assert concept_id_from_name("AlphaMechanism") == concept_id_from_name("  AlphaMechanism  ")


def test_concept_id_from_name_differs_for_different_names():
    assert concept_id_from_name("AlphaMechanism") != concept_id_from_name("BetaMechanism")


def test_concept_id_from_name_is_16_chars():
    cid = concept_id_from_name("SomeName")
    assert len(cid) == 16
    assert all(c in "0123456789abcdef" for c in cid)


# ---------------------------------------------------------------------------
# ConceptEntry
# ---------------------------------------------------------------------------

def test_concept_entry_defaults():
    e = ConceptEntry(
        concept_id="abc123",
        name="TestConcept",
        definition="A definition.",
        confidence=0.80,
    )
    assert e.status == "candidate"
    assert e.merged_into is None
    assert e.source_concept_ids == []
    assert e.supporting_evidence_ids == []
    assert e.occurrence_count == 1


def test_concept_entry_all_statuses():
    for status in ("candidate", "active", "suppressed", "merged_into", "rejected"):
        e = ConceptEntry(
            concept_id="x",
            name="X",
            definition="D.",
            confidence=0.5,
            status=status,
        )
        assert e.status == status


def test_concept_entry_invalid_status():
    with pytest.raises(ValidationError):
        ConceptEntry(
            concept_id="x",
            name="X",
            definition="D.",
            confidence=0.5,
            status="unknown_status",
        )


def test_concept_entry_serialises():
    e = ConceptEntry(
        concept_id="abc123",
        name="TestConcept",
        definition="D.",
        confidence=0.75,
        supporting_evidence_ids=["ev1"],
    )
    d = e.model_dump()
    assert d["name"] == "TestConcept"
    assert d["status"] == "candidate"


# ---------------------------------------------------------------------------
# RegistryMetrics
# ---------------------------------------------------------------------------

def test_registry_metrics_all_fields():
    m = RegistryMetrics(
        raw_proposal_count=21,
        unique_names_raw=19,
        exact_duplicates_merged=2,
        semantic_concepts_merged=4,
        rejected=2,
        suppressed_by_confidence=2,
        suppressed_by_evidence=0,
        active_canonical_count=11,
        promotion_confidence_threshold=0.75,
        min_supporting_evidence=2,
    )
    assert m.active_canonical_count == 11
    assert m.exact_duplicates_merged == 2
