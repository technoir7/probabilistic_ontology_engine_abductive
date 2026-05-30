"""Tests for the consolidation pipeline: store loading, semantic merges, rejections."""
from __future__ import annotations

from pathlib import Path

import pytest

from poea.registry.consolidation import (
    ConsolidationCluster,
    ConsolidationMap,
    apply_consolidation,
)
from poea.registry.schemas import ConceptEntry, concept_id_from_name
from poea.registry.store import load_raw_concepts

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# store.load_raw_concepts
# ---------------------------------------------------------------------------

def test_load_raw_concepts_returns_entries_and_count():
    entries, raw_count = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    assert raw_count == 6
    assert len(entries) == 5  # AlphaMechanism deduplicated from 2 → 1


def test_load_deduplicates_exact_names():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    names = [e.name for e in entries]
    assert names.count("AlphaMechanism") == 1


def test_load_merges_evidence_ids_on_dedup():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    # ev001, ev002 from first proposal + ev010, ev011 from second
    assert set(alpha.supporting_evidence_ids) == {"ev001", "ev002", "ev010", "ev011"}


def test_load_takes_max_confidence_on_dedup():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    assert alpha.confidence == 0.90


def test_load_occurrence_count_reflects_dedup():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    assert alpha.occurrence_count == 2


def test_load_single_occurrence_count_is_one():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    beta = next(e for e in entries if e.name == "BetaMechanism")
    assert beta.occurrence_count == 1


def test_load_assigns_canonical_concept_ids():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    for e in entries:
        assert e.concept_id == concept_id_from_name(e.name)


def test_load_all_statuses_are_candidate():
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    assert all(e.status == "candidate" for e in entries)


# ---------------------------------------------------------------------------
# apply_consolidation — semantic cluster merge
# ---------------------------------------------------------------------------

def _sample_entries() -> list[ConceptEntry]:
    entries, _ = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    return entries


def _test_cmap() -> ConsolidationMap:
    return ConsolidationMap(
        clusters=[
            ConsolidationCluster(
                canonical="AlphaMechanism",
                members=["AlphaMechanism", "DeltaMechanism"],
            )
        ],
        rejected=["EpsilonMechanism"],
    )


def test_apply_consolidation_merges_non_canonical():
    entries = _sample_entries()
    entries, semantic_count = apply_consolidation(entries, _test_cmap())
    delta = next(e for e in entries if e.name == "DeltaMechanism")
    assert delta.status == "merged_into"
    assert delta.merged_into == concept_id_from_name("AlphaMechanism")


def test_apply_consolidation_returns_correct_count():
    entries = _sample_entries()
    _, semantic_count = apply_consolidation(entries, _test_cmap())
    assert semantic_count == 1  # DeltaMechanism merged into AlphaMechanism


def test_apply_consolidation_absorbs_evidence_ids():
    entries = _sample_entries()
    entries, _ = apply_consolidation(entries, _test_cmap())
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    # ev006, ev007 from DeltaMechanism must be absorbed
    assert "ev006" in alpha.supporting_evidence_ids
    assert "ev007" in alpha.supporting_evidence_ids


def test_apply_consolidation_preserves_canonical_evidence():
    entries = _sample_entries()
    entries, _ = apply_consolidation(entries, _test_cmap())
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    assert "ev001" in alpha.supporting_evidence_ids
    assert "ev002" in alpha.supporting_evidence_ids


def test_apply_consolidation_sums_occurrence_counts():
    entries = _sample_entries()
    entries, _ = apply_consolidation(entries, _test_cmap())
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    # AlphaMechanism occurrence_count=2 (dedup) + DeltaMechanism=1
    assert alpha.occurrence_count == 3


def test_apply_consolidation_tracks_source_ids():
    entries = _sample_entries()
    entries, _ = apply_consolidation(entries, _test_cmap())
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    assert concept_id_from_name("DeltaMechanism") in alpha.source_concept_ids


def test_apply_consolidation_does_not_merge_canonical_itself():
    entries = _sample_entries()
    entries, _ = apply_consolidation(entries, _test_cmap())
    alpha = next(e for e in entries if e.name == "AlphaMechanism")
    assert alpha.status == "candidate"  # canonical stays candidate, not merged_into


def test_apply_consolidation_rejects_named_concept():
    entries = _sample_entries()
    entries, _ = apply_consolidation(entries, _test_cmap())
    epsilon = next(e for e in entries if e.name == "EpsilonMechanism")
    assert epsilon.status == "rejected"


def test_apply_consolidation_empty_map_is_noop():
    entries = _sample_entries()
    original_statuses = {e.name: e.status for e in entries}
    entries, count = apply_consolidation(entries, ConsolidationMap.empty())
    assert count == 0
    for e in entries:
        assert e.status == original_statuses[e.name]


def test_apply_consolidation_upgrades_confidence_if_member_higher():
    entries = [
        ConceptEntry(
            concept_id=concept_id_from_name("CanonicalConcept"),
            name="CanonicalConcept",
            definition="Canonical def.",
            confidence=0.70,
        ),
        ConceptEntry(
            concept_id=concept_id_from_name("HigherMember"),
            name="HigherMember",
            definition="Higher def.",
            confidence=0.90,
        ),
    ]
    cmap = ConsolidationMap(
        clusters=[
            ConsolidationCluster(
                canonical="CanonicalConcept",
                members=["CanonicalConcept", "HigherMember"],
            )
        ]
    )
    entries, _ = apply_consolidation(entries, cmap)
    canonical = next(e for e in entries if e.name == "CanonicalConcept")
    assert canonical.confidence == 0.90
    assert canonical.definition == "Higher def."


def test_consolidation_map_from_yaml(tmp_path):
    yaml_content = """
clusters:
  - canonical: ConceptA
    members:
      - ConceptA
      - ConceptB

rejected:
  - ConceptC
"""
    p = tmp_path / "test_map.yaml"
    p.write_text(yaml_content)
    cmap = ConsolidationMap.from_yaml(p)
    assert len(cmap.clusters) == 1
    assert cmap.clusters[0].canonical == "ConceptA"
    assert "ConceptB" in cmap.clusters[0].members
    assert "ConceptC" in cmap.rejected


def test_consolidation_map_empty():
    cmap = ConsolidationMap.empty()
    assert cmap.clusters == []
    assert cmap.rejected == []


# ---------------------------------------------------------------------------
# Full pipeline on real art corpus
# ---------------------------------------------------------------------------

def test_art_corpus_exact_dupes_count():
    """Confirm the two known exact-name duplicates are detected."""
    art_path = Path("artifacts/raw_concepts.json")
    if not art_path.exists():
        pytest.skip("artifacts/raw_concepts.json not available")
    entries, raw_count = load_raw_concepts(art_path)
    exact_merged = raw_count - len(entries)
    assert exact_merged == 2, (
        f"Expected 2 exact-name duplicates; got {exact_merged}. "
        f"raw_count={raw_count}, unique_names={len(entries)}"
    )


def test_art_corpus_semantic_merge_counts():
    """Confirm the four semantic merges from the consolidation map."""
    art_path = Path("artifacts/raw_concepts.json")
    cmap_path = Path("configs/consolidation_map.yaml")
    if not art_path.exists() or not cmap_path.exists():
        pytest.skip("Required artifacts not available")
    entries, _ = load_raw_concepts(art_path)
    _, semantic_count = apply_consolidation(entries, ConsolidationMap.from_yaml(cmap_path))
    assert semantic_count == 4, (
        f"Expected 4 semantic merges (2 per cluster); got {semantic_count}"
    )
