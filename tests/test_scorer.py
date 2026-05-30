"""Tests for the evidence scorer (Phase 6 — Assignment Bridge)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from poea.concepts.scorer import (
    ConceptAssignment,
    EvidenceScorer,
    ScoredRecord,
    ScoringConfig,
    ScoringStats,
    _build_assignment,
    _extract_json_object,
    _neutral_assignments,
    load_scored_evidence,
    save_scored_evidence,
)
from poea.evidence.schemas import EvidenceUnit
from poea.registry.schemas import ConceptEntry, concept_id_from_name

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_concept(name: str, definition: str = "A test concept.") -> ConceptEntry:
    return ConceptEntry(
        concept_id=concept_id_from_name(name),
        name=name,
        definition=definition,
        confidence=0.85,
        supporting_evidence_ids=["ev001", "ev002"],
        status="active",
    )


def _make_evidence(
    eid: str,
    title: str = "Test evidence",
    text: str = "Some text about the topic.",
) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=eid,
        source="test_source",
        title=title,
        domain_tag="test",
        text=text,
    )


def _mock_client(response_json: dict) -> MagicMock:
    client = MagicMock()
    client.complete.return_value = json.dumps(response_json)
    return client


# ---------------------------------------------------------------------------
# _build_assignment — verdict-to-missingness mapping
# ---------------------------------------------------------------------------

def test_supports_true_maps_to_observed():
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "supports_true", 0.85, soft_threshold=0.5)
    assert a.assigned_value is True
    assert a.missingness == "OBSERVED"
    assert a.confidence == 0.85


def test_supports_false_maps_to_observed():
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "supports_false", 0.80, soft_threshold=0.5)
    assert a.assigned_value is False
    assert a.missingness == "OBSERVED"


def test_neutral_maps_to_missing():
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "neutral", 0.30, soft_threshold=0.5)
    assert a.assigned_value is None
    assert a.missingness == "MISSING"


def test_low_confidence_true_maps_to_soft_observed():
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "supports_true", 0.40, soft_threshold=0.5)
    assert a.assigned_value is True
    assert a.missingness == "SOFT_OBSERVED"


def test_low_confidence_false_maps_to_soft_observed():
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "supports_false", 0.30, soft_threshold=0.5)
    assert a.assigned_value is False
    assert a.missingness == "SOFT_OBSERVED"


def test_boundary_confidence_at_threshold_is_observed():
    """Confidence exactly equal to the threshold should be OBSERVED (not SOFT_OBSERVED)."""
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "supports_true", 0.5, soft_threshold=0.5)
    assert a.missingness == "OBSERVED"


def test_unknown_verdict_treated_as_neutral():
    concept = _make_concept("Alpha")
    a = _build_assignment(concept, "garbage_value", 0.70, soft_threshold=0.5)
    assert a.assigned_value is None
    assert a.missingness == "MISSING"


# ---------------------------------------------------------------------------
# _extract_json_object — JSON extraction strategies
# ---------------------------------------------------------------------------

def test_extract_plain_json():
    data = _extract_json_object('{"Alpha": {"verdict": "supports_true", "confidence": 0.8}}')
    assert data == {"Alpha": {"verdict": "supports_true", "confidence": 0.8}}


def test_extract_json_from_fenced_block():
    raw = '```json\n{"Alpha": {"verdict": "neutral", "confidence": 0.3}}\n```'
    data = _extract_json_object(raw)
    assert data is not None
    assert data["Alpha"]["verdict"] == "neutral"


def test_extract_json_from_surrounding_prose():
    raw = 'Here is my answer:\n{"Alpha": {"verdict": "supports_false", "confidence": 0.7}}\nDone.'
    data = _extract_json_object(raw)
    assert data is not None
    assert data["Alpha"]["verdict"] == "supports_false"


def test_extract_json_returns_none_on_garbage():
    assert _extract_json_object("not json at all") is None


def test_extract_json_returns_none_on_empty():
    assert _extract_json_object("") is None


# ---------------------------------------------------------------------------
# EvidenceScorer — basic scoring
# ---------------------------------------------------------------------------

def test_scorer_calls_llm_once_per_record():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    evidence = [_make_evidence("ev001"), _make_evidence("ev002")]
    response = {
        "Alpha": {"verdict": "supports_true", "confidence": 0.85},
        "Beta": {"verdict": "neutral", "confidence": 0.30},
    }
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, stats = scorer.score_all(evidence, concepts)

    assert client.complete.call_count == 2
    assert stats.scored == 2
    assert stats.cache_hits == 0
    assert len(records) == 2


def test_scorer_one_assignment_per_concept_per_record():
    concepts = [_make_concept("Alpha"), _make_concept("Beta"), _make_concept("Gamma")]
    evidence = [_make_evidence("ev001")]
    response = {
        "Alpha": {"verdict": "supports_true", "confidence": 0.85},
        "Beta": {"verdict": "supports_false", "confidence": 0.70},
        "Gamma": {"verdict": "neutral", "confidence": 0.20},
    }
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, _ = scorer.score_all(evidence, concepts)

    assert len(records[0].assignments) == 3


def test_scorer_all_concepts_batched_in_one_call_per_record():
    """All N concepts for a single evidence record must be sent in one LLM call."""
    concepts = [_make_concept(f"Concept{i}") for i in range(5)]
    evidence = [_make_evidence("ev001")]
    response = {f"Concept{i}": {"verdict": "neutral", "confidence": 0.2} for i in range(5)}
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    scorer.score_all(evidence, concepts)

    assert client.complete.call_count == 1


def test_scorer_correct_verdict_mapping():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    evidence = [_make_evidence("ev001")]
    response = {
        "Alpha": {"verdict": "supports_true", "confidence": 0.85},
        "Beta": {"verdict": "supports_false", "confidence": 0.75},
    }
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, _ = scorer.score_all(evidence, concepts)

    by_name = {a.variable_name: a for a in records[0].assignments}
    assert by_name["Alpha"].assigned_value is True
    assert by_name["Alpha"].missingness == "OBSERVED"
    assert by_name["Beta"].assigned_value is False
    assert by_name["Beta"].missingness == "OBSERVED"


def test_scorer_neutral_maps_to_missing():
    concepts = [_make_concept("Alpha")]
    evidence = [_make_evidence("ev001")]
    response = {"Alpha": {"verdict": "neutral", "confidence": 0.20}}
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, _ = scorer.score_all(evidence, concepts)

    a = records[0].assignments[0]
    assert a.assigned_value is None
    assert a.missingness == "MISSING"


def test_scorer_total_pairs_count():
    concepts = [_make_concept(f"C{i}") for i in range(3)]
    evidence = [_make_evidence(f"ev{i:03d}") for i in range(4)]
    response = {f"C{i}": {"verdict": "neutral", "confidence": 0.2} for i in range(3)}
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    _, stats = scorer.score_all(evidence, concepts)

    assert stats.total_pairs == 12  # 3 concepts × 4 records


# ---------------------------------------------------------------------------
# EvidenceScorer — cache behavior
# ---------------------------------------------------------------------------

def test_scorer_cache_hit_skips_llm_call():
    """A record with all current concepts already scored is returned from cache."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    evidence = [_make_evidence("ev001")]

    existing = [
        ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id=concept_id_from_name("Alpha"),
                    variable_name="Alpha",
                    assigned_value=True,
                    confidence=0.85,
                    missingness="OBSERVED",
                ),
                ConceptAssignment(
                    concept_id=concept_id_from_name("Beta"),
                    variable_name="Beta",
                    assigned_value=None,
                    confidence=0.20,
                    missingness="MISSING",
                ),
            ],
        )
    ]

    client = _mock_client({})
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, stats = scorer.score_all(evidence, concepts, existing_records=existing)

    assert client.complete.call_count == 0
    assert stats.cache_hits == 1
    assert stats.scored == 0
    assert records[0].assignments[0].assigned_value is True


def test_scorer_partial_cache_triggers_full_rescore():
    """If any concept for a record is not in cache, the whole record is re-scored."""
    alpha = _make_concept("Alpha")
    beta = _make_concept("Beta")
    concepts = [alpha, beta]
    evidence = [_make_evidence("ev001")]

    existing = [
        ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id=alpha.concept_id,
                    variable_name="Alpha",
                    assigned_value=True,
                    confidence=0.85,
                    missingness="OBSERVED",
                ),
                # Beta missing from cache
            ],
        )
    ]

    response = {
        "Alpha": {"verdict": "supports_true", "confidence": 0.85},
        "Beta": {"verdict": "neutral", "confidence": 0.20},
    }
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, stats = scorer.score_all(evidence, concepts, existing_records=existing)

    assert client.complete.call_count == 1
    assert stats.scored == 1
    assert stats.cache_hits == 0


def test_scorer_mixed_cache_and_new_records():
    """ev001 cached → skip; ev002 not cached → score."""
    concepts = [_make_concept("Alpha")]
    evidence = [_make_evidence("ev001"), _make_evidence("ev002")]

    existing = [
        ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id=concept_id_from_name("Alpha"),
                    variable_name="Alpha",
                    assigned_value=True,
                    confidence=0.85,
                    missingness="OBSERVED",
                )
            ],
        )
    ]
    response = {"Alpha": {"verdict": "supports_false", "confidence": 0.70}}
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, stats = scorer.score_all(evidence, concepts, existing_records=existing)

    assert client.complete.call_count == 1
    assert stats.cache_hits == 1
    assert stats.scored == 1
    by_id = {r.evidence_id: r for r in records}
    assert by_id["ev001"].assignments[0].assigned_value is True
    assert by_id["ev002"].assignments[0].assigned_value is False


# ---------------------------------------------------------------------------
# EvidenceScorer — error handling
# ---------------------------------------------------------------------------

def test_scorer_invalid_json_returns_neutral_record():
    """When LLM returns unparseable JSON, the record gets all-neutral assignments."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    evidence = [_make_evidence("ev001")]

    client = MagicMock()
    client.complete.return_value = "this is not JSON"

    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, stats = scorer.score_all(evidence, concepts)

    assert stats.errors == 1
    assert records[0].error is not None
    for a in records[0].assignments:
        assert a.missingness == "MISSING"
        assert a.assigned_value is None


def test_scorer_missing_concept_in_response_defaults_to_neutral():
    """Concepts absent from the LLM response get neutral/MISSING."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    evidence = [_make_evidence("ev001")]

    # LLM only returns Alpha
    response = {"Alpha": {"verdict": "supports_true", "confidence": 0.85}}
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, _ = scorer.score_all(evidence, concepts)

    by_name = {a.variable_name: a for a in records[0].assignments}
    assert by_name["Alpha"].assigned_value is True
    assert by_name["Beta"].assigned_value is None
    assert by_name["Beta"].missingness == "MISSING"


def test_scorer_extra_keys_in_response_are_ignored():
    """Extra concept names in the LLM response that are not in active concepts are ignored."""
    concepts = [_make_concept("Alpha")]
    evidence = [_make_evidence("ev001")]

    response = {
        "Alpha": {"verdict": "supports_true", "confidence": 0.85},
        "UnknownConcept": {"verdict": "supports_true", "confidence": 0.90},
    }
    client = _mock_client(response)
    scorer = EvidenceScorer(ScoringConfig(), client=client)
    records, _ = scorer.score_all(evidence, concepts)

    assert len(records[0].assignments) == 1
    assert records[0].assignments[0].variable_name == "Alpha"


# ---------------------------------------------------------------------------
# _neutral_assignments
# ---------------------------------------------------------------------------

def test_neutral_assignments_all_missing():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    result = _neutral_assignments(concepts)
    assert len(result) == 2
    for a in result:
        assert a.assigned_value is None
        assert a.missingness == "MISSING"
        assert a.confidence == 0.0


def test_neutral_assignments_preserves_concept_ids():
    concepts = [_make_concept("Alpha")]
    result = _neutral_assignments(concepts)
    assert result[0].concept_id == concepts[0].concept_id
    assert result[0].variable_name == "Alpha"


# ---------------------------------------------------------------------------
# ScoringConfig
# ---------------------------------------------------------------------------

def test_scoring_config_uses_scoring_model():
    cfg = ScoringConfig.from_dict({"models": {"scoring": "my-scoring-model"}})
    assert cfg.model == "my-scoring-model"


def test_scoring_config_falls_back_to_induction_model():
    cfg = ScoringConfig.from_dict({"models": {"induction": "my-induction-model"}})
    assert cfg.model == "my-induction-model"


def test_scoring_config_defaults_on_empty_dict():
    cfg = ScoringConfig.from_dict({})
    assert cfg.model == "accounts/fireworks/models/deepseek-v4-pro"
    assert cfg.soft_observed_threshold == 0.5
    assert cfg.max_tokens == 2048


def test_scoring_config_custom_threshold():
    cfg = ScoringConfig.from_dict({"scoring": {"soft_observed_threshold": 0.6}})
    assert cfg.soft_observed_threshold == 0.6


# ---------------------------------------------------------------------------
# load_scored_evidence / save_scored_evidence — I/O round-trip
# ---------------------------------------------------------------------------

def test_save_and_load_round_trip(tmp_path):
    records = [
        ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id="abc123",
                    variable_name="Alpha",
                    assigned_value=True,
                    confidence=0.85,
                    missingness="OBSERVED",
                ),
                ConceptAssignment(
                    concept_id="def456",
                    variable_name="Beta",
                    assigned_value=None,
                    confidence=0.20,
                    missingness="MISSING",
                ),
            ],
        )
    ]
    stats = ScoringStats(
        total_records=1,
        scored=1,
        cache_hits=0,
        errors=0,
        total_pairs=2,
        by_concept={"Alpha": {"true": 1, "false": 0, "neutral": 0}},
    )
    path = tmp_path / "scored.json"
    save_scored_evidence(path, records, stats, {"model": "test-model"})

    loaded = load_scored_evidence(path)
    assert len(loaded) == 1
    assert loaded[0].evidence_id == "ev001"
    assert loaded[0].assignments[0].assigned_value is True
    assert loaded[0].assignments[0].missingness == "OBSERVED"
    assert loaded[0].assignments[1].assigned_value is None
    assert loaded[0].assignments[1].missingness == "MISSING"


def test_load_nonexistent_path_returns_empty_list():
    result = load_scored_evidence("/tmp/poea_nonexistent_scored_evidence_99999.json")
    assert result == []


def test_save_creates_parent_directories(tmp_path):
    deep_path = tmp_path / "a" / "b" / "c" / "scored.json"
    records: list[ScoredRecord] = []
    stats = ScoringStats(
        total_records=0, scored=0, cache_hits=0, errors=0, total_pairs=0
    )
    save_scored_evidence(deep_path, records, stats, {})
    assert deep_path.exists()


def test_saved_file_is_valid_json(tmp_path):
    records = [
        ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id="abc",
                    variable_name="Alpha",
                    assigned_value=False,
                    confidence=0.75,
                    missingness="OBSERVED",
                )
            ],
        )
    ]
    stats = ScoringStats(
        total_records=1, scored=1, cache_hits=0, errors=0, total_pairs=1
    )
    path = tmp_path / "out.json"
    save_scored_evidence(path, records, stats, {"test": True})
    with path.open() as f:
        data = json.load(f)
    assert "metadata" in data
    assert "summary" in data
    assert "scored_records" in data
    assert len(data["scored_records"]) == 1
