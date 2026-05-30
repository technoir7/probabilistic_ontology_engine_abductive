"""Tests for the Concept schema and its validators."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from poea.concepts.schemas import Concept, InductionBatchResult


def test_valid_concept():
    c = Concept(
        name="PricePolarization",
        definition="The divergence of market prices toward extremes.",
        confidence=0.8,
        supporting_evidence_ids=["abc123"],
    )
    assert c.name == "PricePolarization"
    assert c.confidence == 0.8


def test_confidence_clamped_above_one():
    c = Concept(name="X", definition="A concept.", confidence=1.5)
    assert c.confidence == 1.0


def test_confidence_clamped_below_zero():
    c = Concept(name="X", definition="A concept.", confidence=-0.3)
    assert c.confidence == 0.0


def test_confidence_boundary_values():
    assert Concept(name="X", definition="D.", confidence=0.0).confidence == 0.0
    assert Concept(name="X", definition="D.", confidence=1.0).confidence == 1.0


def test_empty_name_rejected():
    with pytest.raises(ValidationError):
        Concept(name="", definition="A definition.", confidence=0.5)


def test_whitespace_name_rejected():
    with pytest.raises(ValidationError):
        Concept(name="   ", definition="A definition.", confidence=0.5)


def test_empty_definition_rejected():
    with pytest.raises(ValidationError):
        Concept(name="ValidName", definition="", confidence=0.5)


def test_default_supporting_evidence_ids():
    c = Concept(name="X", definition="D.", confidence=0.5)
    assert c.supporting_evidence_ids == []


def test_supporting_evidence_ids_stored():
    c = Concept(name="X", definition="D.", confidence=0.5, supporting_evidence_ids=["a", "b"])
    assert c.supporting_evidence_ids == ["a", "b"]


def test_concept_serialises_to_dict():
    c = Concept(name="X", definition="D.", confidence=0.5)
    d = c.model_dump()
    assert set(d.keys()) == {"name", "definition", "confidence", "supporting_evidence_ids"}


def test_induction_batch_result():
    c = Concept(name="X", definition="D.", confidence=0.5)
    result = InductionBatchResult(
        batch_index=0,
        evidence_ids=["e1", "e2"],
        concepts=[c],
        model="claude-sonnet-4-6",
    )
    assert result.batch_index == 0
    assert len(result.concepts) == 1
    assert result.error is None


def test_induction_batch_result_with_error():
    result = InductionBatchResult(
        batch_index=1,
        evidence_ids=["e1"],
        concepts=[],
        model="claude-sonnet-4-6",
        error="API timeout",
    )
    assert result.error == "API timeout"
    assert result.concepts == []
