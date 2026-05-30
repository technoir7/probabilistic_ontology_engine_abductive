from __future__ import annotations

from poea.assignments import (
    AssignmentRouter,
    DeterministicMapperBackend,
    DirectStructuredAssignmentBackend,
    HybridPrefilterScorerBackend,
    SemanticLLMScorerBackend,
)
from poea.concepts.scorer import ConceptAssignment, ScoredRecord, ScoringStats
from poea.evidence.schemas import EvidenceUnit
from poea.registry.schemas import ConceptEntry, concept_id_from_name


class FakeSemanticScorer:
    def __init__(self) -> None:
        self.calls = 0
        self.evidence_ids: list[str] = []

    def score_all(self, evidence, concepts, existing_records=None):
        self.calls += len(evidence)
        self.evidence_ids.extend([e.evidence_id for e in evidence])
        records = [
            ScoredRecord(
                evidence_id=e.evidence_id,
                assignments=[
                    ConceptAssignment(
                        concept_id=c.concept_id,
                        variable_name=c.name,
                        assigned_value=True,
                        confidence=0.9,
                        missingness="OBSERVED",
                    )
                    for c in concepts
                ],
            )
            for e in evidence
        ]
        return records, ScoringStats(
            total_records=len(evidence),
            scored=len(evidence),
            cache_hits=0,
            errors=0,
            total_pairs=len(evidence) * len(concepts),
        )


def _concept(name: str) -> ConceptEntry:
    return ConceptEntry(
        concept_id=concept_id_from_name(name),
        name=name,
        definition=f"{name} definition.",
        confidence=0.9,
        supporting_evidence_ids=["ev001"],
        status="active",
    )


def _evidence(
    evidence_id: str,
    *,
    text: str = "Evidence text.",
    metadata: dict | None = None,
) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=evidence_id,
        source="test.json",
        title=evidence_id,
        domain_tag="test",
        text=text,
        metadata=metadata or {},
    )


def _router(fake_scorer: FakeSemanticScorer) -> AssignmentRouter:
    return AssignmentRouter.default(fake_scorer)  # type: ignore[arg-type]


def test_structured_numeric_evidence_does_not_call_llm_scorer():
    concepts = [_concept("LiquidityStress")]
    evidence = [
        _evidence(
            "ev001",
            metadata={
                "assignment_mode": "deterministic",
                "deterministic_mapper": "numeric_fixture",
                "evidence_type": "structured_numeric",
                "value": 12.5,
            },
        )
    ]

    def mapper(unit, concept_list):
        assert unit.metadata["value"] == 12.5
        return {concept_list[0].name: {"value": True, "confidence": 1.0}}

    fake_scorer = FakeSemanticScorer()
    direct = DirectStructuredAssignmentBackend()
    semantic = SemanticLLMScorerBackend(fake_scorer)  # type: ignore[arg-type]
    deterministic = DeterministicMapperBackend({"numeric_fixture": mapper})
    router = AssignmentRouter(
        direct_backend=direct,
        deterministic_backend=deterministic,
        semantic_backend=semantic,
        hybrid_backend=HybridPrefilterScorerBackend(direct, semantic),
    )

    result = router.score_all(evidence, concepts)

    assert fake_scorer.calls == 0
    assert result.records[0].assignments[0].assigned_value is True
    assert result.metadata["mode_counts"] == {"deterministic": 1}
    assert result.stats.scored == 0


def test_prose_evidence_routes_to_semantic_scoring():
    concepts = [_concept("AuctionCatalyst")]
    evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
    fake_scorer = FakeSemanticScorer()

    result = _router(fake_scorer).score_all(evidence, concepts)

    assert fake_scorer.calls == 1
    assert fake_scorer.evidence_ids == ["ev001"]
    assert result.records[0].assignments[0].assigned_value is True
    assert result.metadata["mode_counts"] == {"semantic": 1}
    assert result.stats.scored == 1


def test_already_assigned_evidence_translates_directly_to_assignments():
    alpha = _concept("Alpha")
    beta = _concept("Beta")
    evidence = [
        _evidence(
            "ev001",
            metadata={
                "evidence_type": "structured_json_with_assignments",
                "structured_assignments": {
                    alpha.concept_id: {"value": True, "confidence": 0.95},
                    "Beta": {"value": False, "confidence": 0.4},
                },
            },
        )
    ]
    fake_scorer = FakeSemanticScorer()

    result = _router(fake_scorer).score_all(evidence, [alpha, beta])

    assert fake_scorer.calls == 0
    by_name = {a.variable_name: a for a in result.records[0].assignments}
    assert by_name["Alpha"].assigned_value is True
    assert by_name["Alpha"].missingness == "OBSERVED"
    assert by_name["Beta"].assigned_value is False
    assert by_name["Beta"].missingness == "SOFT_OBSERVED"
    assert result.metadata["mode_counts"] == {"direct_structured": 1}


def test_router_decisions_are_deterministic():
    evidence = _evidence("ev001", metadata={"evidence_type": "mixed"})
    router = _router(FakeSemanticScorer())

    decisions = [router.decide(evidence) for _ in range(5)]

    assert {d.mode for d in decisions} == {"hybrid"}
    assert {d.backend for d in decisions} == {"hybrid_prefilter"}
    assert {d.reason for d in decisions} == {"evidence_type=mixed"}


def test_existing_cache_is_reused_before_routing_to_semantic():
    concept = _concept("Alpha")
    evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
    cached = ScoredRecord(
        evidence_id="ev001",
        assignments=[
            ConceptAssignment(
                concept_id=concept.concept_id,
                variable_name=concept.name,
                assigned_value=False,
                confidence=0.8,
                missingness="OBSERVED",
            )
        ],
    )
    fake_scorer = FakeSemanticScorer()

    result = _router(fake_scorer).score_all(evidence, [concept], existing_records=[cached])

    assert fake_scorer.calls == 0
    assert result.records == [cached]
    assert result.stats.cache_hits == 1
    assert result.metadata["backend_counts"] == {"cache": 1}
