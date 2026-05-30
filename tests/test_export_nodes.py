"""Tests for concept-to-node translation (Phase 8)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from poea.artifacts.exporters import (
    concept_entry_to_node,
    concepts_to_nodes,
    load_canonical_concepts,
    write_nodes,
)
from poea.registry.schemas import ConceptEntry, concept_id_from_name

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_concept(name: str, definition: str = "Test definition.") -> ConceptEntry:
    return ConceptEntry(
        concept_id=concept_id_from_name(name),
        name=name,
        definition=definition,
        confidence=0.85,
        supporting_evidence_ids=["ev001", "ev002"],
        status="active",
    )


# ---------------------------------------------------------------------------
# concept_entry_to_node — single-concept translation
# ---------------------------------------------------------------------------

def test_node_has_required_fields():
    concept = _make_concept("AuctionCatalystEffect")
    node = concept_entry_to_node(concept)
    for field in ("concept_id", "name", "definition", "prior_probability", "boolean_state", "source"):
        assert field in node, f"Missing required field: {field!r}"


def test_node_prior_probability_is_half():
    concept = _make_concept("Alpha")
    node = concept_entry_to_node(concept)
    assert node["prior_probability"] == 0.5


def test_node_boolean_state_is_none():
    concept = _make_concept("Alpha")
    node = concept_entry_to_node(concept)
    assert node["boolean_state"] is None


def test_node_source_is_poea_induced():
    concept = _make_concept("Alpha")
    node = concept_entry_to_node(concept)
    assert node["source"] == "poea_induced"


def test_node_preserves_concept_name():
    concept = _make_concept("InstitutionalValidationPremium")
    node = concept_entry_to_node(concept)
    assert node["name"] == "InstitutionalValidationPremium"


def test_node_preserves_definition():
    concept = _make_concept("Alpha", definition="A specific causal mechanism.")
    node = concept_entry_to_node(concept)
    assert node["definition"] == "A specific causal mechanism."


def test_node_preserves_concept_id():
    concept = _make_concept("Alpha")
    node = concept_entry_to_node(concept)
    assert node["concept_id"] == concept.concept_id


def test_node_does_not_include_confidence():
    """Node format must not leak LLM confidence into the structure-learning backend."""
    concept = _make_concept("Alpha")
    node = concept_entry_to_node(concept)
    assert "confidence" not in node


def test_node_does_not_include_evidence_ids():
    """Node format must not include supporting_evidence_ids (raw evidence link)."""
    concept = _make_concept("Alpha")
    node = concept_entry_to_node(concept)
    assert "supporting_evidence_ids" not in node


# ---------------------------------------------------------------------------
# concepts_to_nodes — full artifact
# ---------------------------------------------------------------------------

def test_artifact_has_required_keys():
    artifact = concepts_to_nodes([], domain_tag="test")
    for key in ("domain_tag", "node_count", "nodes", "metadata"):
        assert key in artifact, f"Missing key: {key!r}"


def test_artifact_node_count_matches_nodes_length():
    concepts = [_make_concept("Alpha"), _make_concept("Beta"), _make_concept("Gamma")]
    artifact = concepts_to_nodes(concepts, domain_tag="test")
    assert artifact["node_count"] == 3
    assert len(artifact["nodes"]) == 3


def test_artifact_domain_tag_preserved():
    artifact = concepts_to_nodes([], domain_tag="art")
    assert artifact["domain_tag"] == "art"


def test_artifact_with_no_concepts():
    artifact = concepts_to_nodes([], domain_tag="test")
    assert artifact["nodes"] == []
    assert artifact["node_count"] == 0


def test_artifact_all_nodes_have_correct_priors():
    concepts = [_make_concept(f"Concept{i}") for i in range(5)]
    artifact = concepts_to_nodes(concepts)
    for node in artifact["nodes"]:
        assert node["prior_probability"] == 0.5
        assert node["boolean_state"] is None


def test_artifact_all_nodes_are_poea_induced():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    artifact = concepts_to_nodes(concepts)
    for node in artifact["nodes"]:
        assert node["source"] == "poea_induced"


def test_artifact_no_hardcoded_domain_variables():
    """
    The exporter must work with arbitrary concept names — no art-specific logic.
    Domain-agnostic validation: export concepts with non-art names and verify output.
    """
    concepts = [
        _make_concept("MarketLiquidityCrunch"),
        _make_concept("SupplyShockContagion"),
        _make_concept("RegulatorySentimentShift"),
    ]
    artifact = concepts_to_nodes(concepts, domain_tag="finance")
    assert artifact["domain_tag"] == "finance"
    names = {n["name"] for n in artifact["nodes"]}
    assert "MarketLiquidityCrunch" in names
    assert "SupplyShockContagion" in names


def test_artifact_metadata_has_created_at():
    artifact = concepts_to_nodes([])
    assert "created_at" in artifact["metadata"]


# ---------------------------------------------------------------------------
# load_canonical_concepts
# ---------------------------------------------------------------------------

def test_load_canonical_concepts_from_temp_file(tmp_path):
    concepts_data = {
        "metadata": {"source": "test", "concept_count": 2, "created_at": "2026-01-01"},
        "concepts": [
            {
                "concept_id": concept_id_from_name("Alpha"),
                "name": "Alpha",
                "definition": "Alpha definition.",
                "confidence": 0.85,
                "supporting_evidence_ids": ["ev001"],
                "occurrence_count": 2,
                "status": "active",
                "merged_into": None,
                "source_concept_ids": [],
            },
            {
                "concept_id": concept_id_from_name("Beta"),
                "name": "Beta",
                "definition": "Beta definition.",
                "confidence": 0.80,
                "supporting_evidence_ids": ["ev002"],
                "occurrence_count": 1,
                "status": "active",
                "merged_into": None,
                "source_concept_ids": [],
            },
        ],
    }
    path = tmp_path / "canonical_concepts.json"
    path.write_text(json.dumps(concepts_data))

    concepts, domain_tag = load_canonical_concepts(path)
    assert len(concepts) == 2
    assert concepts[0].name == "Alpha"
    assert concepts[1].name == "Beta"


def test_load_canonical_concepts_returns_domain_tag_from_metadata(tmp_path):
    data = {
        "metadata": {"domain_tag": "finance", "created_at": "2026-01-01"},
        "concepts": [],
    }
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(data))
    _, domain_tag = load_canonical_concepts(path)
    assert domain_tag == "finance"


def test_load_canonical_concepts_defaults_domain_tag_when_absent(tmp_path):
    data = {"metadata": {}, "concepts": []}
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(data))
    _, domain_tag = load_canonical_concepts(path)
    assert domain_tag == "unknown"


# ---------------------------------------------------------------------------
# write_nodes
# ---------------------------------------------------------------------------

def test_write_nodes_creates_file(tmp_path):
    artifact = concepts_to_nodes([_make_concept("Alpha")], domain_tag="test")
    out = tmp_path / "nodes.json"
    write_nodes(out, artifact)
    assert out.exists()


def test_write_nodes_produces_valid_json(tmp_path):
    artifact = concepts_to_nodes([_make_concept("Alpha")], domain_tag="test")
    out = tmp_path / "nodes.json"
    write_nodes(out, artifact)
    data = json.loads(out.read_text())
    assert data["domain_tag"] == "test"
    assert len(data["nodes"]) == 1


def test_write_nodes_creates_parent_directories(tmp_path):
    artifact = concepts_to_nodes([], domain_tag="test")
    out = tmp_path / "a" / "b" / "nodes.json"
    write_nodes(out, artifact)
    assert out.exists()


def test_write_nodes_round_trip(tmp_path):
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    artifact = concepts_to_nodes(concepts, domain_tag="art")
    out = tmp_path / "nodes.json"
    write_nodes(out, artifact)

    loaded = json.loads(out.read_text())
    assert loaded["domain_tag"] == "art"
    assert loaded["node_count"] == 2
    names = {n["name"] for n in loaded["nodes"]}
    assert "Alpha" in names
    assert "Beta" in names


# ---------------------------------------------------------------------------
# Integration: art corpus
# ---------------------------------------------------------------------------

def test_art_corpus_exports_eleven_nodes():
    """Confirm 11 active art concepts export correctly."""
    canonical_path = Path("artifacts/canonical_concepts.json")
    if not canonical_path.exists():
        pytest.skip("canonical_concepts.json not available")

    concepts, _ = load_canonical_concepts(canonical_path)
    artifact = concepts_to_nodes(concepts, domain_tag="art")

    assert artifact["node_count"] == 11
    assert len(artifact["nodes"]) == 11


def test_art_corpus_all_priors_are_half():
    canonical_path = Path("artifacts/canonical_concepts.json")
    if not canonical_path.exists():
        pytest.skip("canonical_concepts.json not available")

    concepts, _ = load_canonical_concepts(canonical_path)
    artifact = concepts_to_nodes(concepts, domain_tag="art")

    for node in artifact["nodes"]:
        assert node["prior_probability"] == 0.5
        assert node["boolean_state"] is None
