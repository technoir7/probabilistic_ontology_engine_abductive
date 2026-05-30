"""Tests for the promotion lifecycle: candidate → active / suppressed."""
from __future__ import annotations

from pathlib import Path

import pytest

from poea.registry.consolidation import ConsolidationMap, apply_consolidation
from poea.registry.lifecycle import promote
from poea.registry.schemas import ConceptEntry, concept_id_from_name
from poea.registry.store import load_raw_concepts

FIXTURES = Path(__file__).parent / "fixtures"


def _make_entry(name: str, confidence: float, evidence_count: int) -> ConceptEntry:
    return ConceptEntry(
        concept_id=concept_id_from_name(name),
        name=name,
        definition=f"{name} definition.",
        confidence=confidence,
        supporting_evidence_ids=[f"ev{i:03d}" for i in range(evidence_count)],
    )


# ---------------------------------------------------------------------------
# promote — basic rules
# ---------------------------------------------------------------------------

def test_promote_active_when_both_thresholds_met():
    entries = [_make_entry("StrongConcept", 0.80, 3)]
    entries, _, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "active"


def test_promote_suppressed_by_confidence():
    entries = [_make_entry("WeakConcept", 0.70, 5)]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "suppressed"
    assert counts["by_confidence"] == 1
    assert counts["by_evidence"] == 0


def test_promote_suppressed_by_evidence():
    entries = [_make_entry("LonelyInstance", 0.90, 1)]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "suppressed"
    assert counts["by_evidence"] == 1
    assert counts["by_confidence"] == 0


def test_promote_confidence_checked_before_evidence():
    """A concept failing both tests is counted under by_confidence, not by_evidence."""
    entries = [_make_entry("DoubleFailure", 0.60, 1)]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "suppressed"
    assert counts["by_confidence"] == 1
    assert counts["by_evidence"] == 0


def test_promote_boundary_confidence_is_active():
    """Confidence exactly equal to min_confidence should pass."""
    entries = [_make_entry("BoundaryConfidence", 0.75, 2)]
    entries, _, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "active"


def test_promote_boundary_evidence_is_active():
    """Evidence count exactly equal to min_evidence should pass."""
    entries = [_make_entry("BoundaryEvidence", 0.80, 2)]
    entries, _, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "active"


def test_promote_skips_merged_into():
    entry = ConceptEntry(
        concept_id=concept_id_from_name("Merged"),
        name="Merged",
        definition="D.",
        confidence=0.90,
        supporting_evidence_ids=["ev001", "ev002"],
        status="merged_into",
        merged_into=concept_id_from_name("Canonical"),
    )
    entries, _, _ = promote([entry], min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "merged_into"


def test_promote_skips_rejected():
    entry = ConceptEntry(
        concept_id=concept_id_from_name("Rejected"),
        name="Rejected",
        definition="D.",
        confidence=0.90,
        supporting_evidence_ids=["ev001", "ev002"],
        status="rejected",
    )
    entries, _, _ = promote([entry], min_confidence=0.75, min_evidence=2)
    assert entries[0].status == "rejected"


def test_promote_mixed_list():
    entries = [
        _make_entry("Active1", 0.90, 3),
        _make_entry("Active2", 0.75, 2),
        _make_entry("SuppressedConf", 0.70, 3),
        _make_entry("SuppressedEv", 0.90, 1),
    ]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2)
    statuses = {e.name: e.status for e in entries}
    assert statuses["Active1"] == "active"
    assert statuses["Active2"] == "active"
    assert statuses["SuppressedConf"] == "suppressed"
    assert statuses["SuppressedEv"] == "suppressed"
    assert counts["by_confidence"] == 1
    assert counts["by_evidence"] == 1


# ---------------------------------------------------------------------------
# max_active cap
# ---------------------------------------------------------------------------

def test_promote_cap_suppresses_excess():
    """Concepts beyond max_active are suppressed after threshold promotion."""
    # 5 concepts all qualify on confidence + evidence
    entries = [_make_entry(f"Concept{i}", 0.90 - i * 0.01, 3) for i in range(5)]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2, max_active=3)
    active = [e for e in entries if e.status == "active"]
    suppressed = [e for e in entries if e.status == "suppressed"]
    assert len(active) == 3
    assert len(suppressed) == 2
    assert counts["by_cap"] == 2


def test_promote_cap_keeps_highest_confidence():
    """The cap retains concepts with the highest confidence."""
    entries = [
        _make_entry("High", 0.95, 3),
        _make_entry("Mid", 0.85, 3),
        _make_entry("Low", 0.80, 3),
    ]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2, max_active=2)
    statuses = {e.name: e.status for e in entries}
    assert statuses["High"] == "active"
    assert statuses["Mid"] == "active"
    assert statuses["Low"] == "suppressed"
    assert counts["by_cap"] == 1


def test_promote_cap_not_triggered_when_within_limit():
    """No cap suppression when active count is within max_active."""
    entries = [_make_entry(f"Concept{i}", 0.90, 3) for i in range(3)]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2, max_active=5)
    assert counts["by_cap"] == 0
    assert all(e.status == "active" for e in entries)


def test_promote_cap_zero_triggers_all_suppressed():
    """max_active=0 suppresses every concept that would otherwise be active."""
    entries = [_make_entry(f"Concept{i}", 0.90, 3) for i in range(3)]
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2, max_active=0)
    assert counts["by_cap"] == 3
    assert all(e.status == "suppressed" for e in entries)


# ---------------------------------------------------------------------------
# promotion events
# ---------------------------------------------------------------------------

def test_promote_events_generated_for_each_candidate():
    """One event is generated per evaluated candidate."""
    entries = [
        _make_entry("Strong", 0.90, 3),
        _make_entry("Weak", 0.70, 3),
        _make_entry("NoEvidence", 0.90, 1),
    ]
    entries, _, events = promote(entries, min_confidence=0.75, min_evidence=2)
    assert len(events) == 3


def test_promote_events_correct_types():
    """Event types match the promotion outcome of each concept."""
    entries = [
        _make_entry("Strong", 0.90, 3),
        _make_entry("LowConf", 0.70, 3),
        _make_entry("LowEv", 0.90, 1),
    ]
    entries, _, events = promote(entries, min_confidence=0.75, min_evidence=2)
    by_name = {ev["concept_name"]: ev["event_type"] for ev in events}
    assert by_name["Strong"] == "promoted_to_active"
    assert by_name["LowConf"] == "suppressed_by_confidence"
    assert by_name["LowEv"] == "suppressed_by_evidence"


def test_promote_events_have_required_fields():
    """Every event contains the required audit fields."""
    entries = [_make_entry("Alpha", 0.90, 3)]
    entries, _, events = promote(entries, min_confidence=0.75, min_evidence=2)
    assert len(events) == 1
    ev = events[0]
    assert "event_id" in ev
    assert "concept_id" in ev
    assert "concept_name" in ev
    assert "event_type" in ev
    assert "criteria" in ev
    assert "actual_values" in ev
    assert "created_at" in ev
    assert ev["criteria"]["min_confidence"] == 0.75
    assert ev["criteria"]["min_evidence"] == 2


def test_promote_cap_events_generated():
    """Cap events are generated for concepts suppressed by the hard cap."""
    entries = [_make_entry(f"Concept{i}", 0.90, 3) for i in range(5)]
    entries, counts, events = promote(entries, min_confidence=0.75, min_evidence=2, max_active=3)
    cap_events = [ev for ev in events if ev["event_type"] == "suppressed_by_cap"]
    assert len(cap_events) == 2
    assert counts["by_cap"] == 2


def test_promote_skipped_entries_produce_no_events():
    """merged_into and rejected concepts do not produce events."""
    merged = ConceptEntry(
        concept_id=concept_id_from_name("Merged"),
        name="Merged",
        definition="D.",
        confidence=0.90,
        supporting_evidence_ids=["ev001", "ev002"],
        status="merged_into",
        merged_into=concept_id_from_name("Canonical"),
    )
    rejected = ConceptEntry(
        concept_id=concept_id_from_name("Rejected"),
        name="Rejected",
        definition="D.",
        confidence=0.90,
        supporting_evidence_ids=["ev001", "ev002"],
        status="rejected",
    )
    entries, _, events = promote([merged, rejected], min_confidence=0.75, min_evidence=2)
    assert events == []


# ---------------------------------------------------------------------------
# Full pipeline on fixture data
# ---------------------------------------------------------------------------

def test_full_pipeline_fixture():
    """Complete pipeline: load → consolidate → promote → assert expected results."""
    from poea.registry.consolidation import ConsolidationCluster

    entries, raw_count = load_raw_concepts(FIXTURES / "sample_raw_concepts.json")
    assert raw_count == 6
    assert len(entries) == 5

    cmap = ConsolidationMap(
        clusters=[
            ConsolidationCluster(
                canonical="AlphaMechanism",
                members=["AlphaMechanism", "DeltaMechanism"],
            )
        ],
        rejected=["EpsilonMechanism"],
    )
    entries, semantic_count = apply_consolidation(entries, cmap)
    assert semantic_count == 1

    entries, suppression_counts, events = promote(entries, min_confidence=0.75, min_evidence=2)

    statuses = {e.name: e.status for e in entries}
    assert statuses["AlphaMechanism"] == "active"
    assert statuses["BetaMechanism"] == "active"
    assert statuses["GammaMechanism"] == "suppressed"
    assert statuses["DeltaMechanism"] == "merged_into"
    assert statuses["EpsilonMechanism"] == "rejected"

    assert suppression_counts["by_evidence"] == 1  # GammaMechanism has 1 evidence record


# ---------------------------------------------------------------------------
# Art corpus integration
# ---------------------------------------------------------------------------

def test_art_corpus_active_count():
    """Confirm 11 active canonical concepts from the art induction run."""
    art_path = Path("artifacts/raw_concepts.json")
    cmap_path = Path("configs/consolidation_map.yaml")
    if not art_path.exists() or not cmap_path.exists():
        pytest.skip("Required artifacts not available")

    entries, _ = load_raw_concepts(art_path)
    entries, _ = apply_consolidation(entries, ConsolidationMap.from_yaml(cmap_path))
    entries, _, _ = promote(entries, min_confidence=0.75, min_evidence=2)

    active = [e for e in entries if e.status == "active"]
    assert len(active) == 11, (
        f"Expected 11 active concepts; got {len(active)}: "
        + ", ".join(e.name for e in active)
    )


def test_art_corpus_suppressed_count():
    art_path = Path("artifacts/raw_concepts.json")
    cmap_path = Path("configs/consolidation_map.yaml")
    if not art_path.exists() or not cmap_path.exists():
        pytest.skip("Required artifacts not available")

    entries, _ = load_raw_concepts(art_path)
    entries, _ = apply_consolidation(entries, ConsolidationMap.from_yaml(cmap_path))
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2)

    suppressed = [e for e in entries if e.status == "suppressed"]
    assert len(suppressed) == 2
    suppressed_names = {e.name for e in suppressed}
    assert "AccessiblePriceLiquidityEngine" in suppressed_names
    assert "MarketDemocratization" in suppressed_names


def test_art_corpus_no_candidate_remains():
    """After promotion, no concept should remain in candidate status."""
    art_path = Path("artifacts/raw_concepts.json")
    cmap_path = Path("configs/consolidation_map.yaml")
    if not art_path.exists() or not cmap_path.exists():
        pytest.skip("Required artifacts not available")

    entries, _ = load_raw_concepts(art_path)
    entries, _ = apply_consolidation(entries, ConsolidationMap.from_yaml(cmap_path))
    entries, _, _ = promote(entries, min_confidence=0.75, min_evidence=2)

    candidates = [e for e in entries if e.status == "candidate"]
    assert candidates == [], f"Remaining candidates: {[e.name for e in candidates]}"


def test_art_corpus_by_cap_zero():
    """With default cap of 30, no art concepts should be suppressed by cap."""
    art_path = Path("artifacts/raw_concepts.json")
    cmap_path = Path("configs/consolidation_map.yaml")
    if not art_path.exists() or not cmap_path.exists():
        pytest.skip("Required artifacts not available")

    entries, _ = load_raw_concepts(art_path)
    entries, _ = apply_consolidation(entries, ConsolidationMap.from_yaml(cmap_path))
    entries, counts, _ = promote(entries, min_confidence=0.75, min_evidence=2, max_active=30)

    assert counts["by_cap"] == 0
