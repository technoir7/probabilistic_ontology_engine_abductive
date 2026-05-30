"""
Tests for semantic LLM scoring optimizations:
- Compact prompt preserves output schema
- Shadow prefilter doesn't change outputs
- Cache prevents repeated LLM calls
- Routing/cost metrics are deterministic
- Structured evidence never calls LLM
- Old POE mapper is used for structured domains
- Unknown structured evidence errors without LLM
- Art-market prose routes to semantic scorer
"""
from __future__ import annotations

import json

from poea.assignments import (
    AssignmentRouter,
    DeterministicMapperBackend,
    DirectStructuredAssignmentBackend,
    HybridPrefilterScorerBackend,
    OldPOEDomainMapperAdapter,
    OldPOEDomainMapperSpec,
    SemanticLLMScorerBackend,
    ShadowPrefilter,
    ShadowPrefilterAnalysis,
)
from poea.concepts.scorer import (
    ConceptAssignment,
    ScoredRecord,
    ScoringStats,
)
from poea.concepts.scorer_prompts import SCORER_SYSTEM_PROMPT, build_scorer_user_message
from poea.evidence.schemas import EvidenceUnit
from poea.registry.schemas import ConceptEntry, concept_id_from_name

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _concept(name: str, definition: str = "A test causal mechanism.") -> ConceptEntry:
    return ConceptEntry(
        concept_id=concept_id_from_name(name),
        name=name,
        definition=definition,
        confidence=0.9,
        supporting_evidence_ids=["ev001"],
        status="active",
    )


def _evidence(eid: str, *, text: str = "Evidence text.", metadata: dict | None = None) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=eid,
        source="test",
        title=eid,
        domain_tag="art",
        text=text,
        metadata=metadata or {},
    )


class CountingMockScorer:
    def __init__(self) -> None:
        self.calls = 0
        self.last_evidence_ids: list[str] = []

    def score_all(self, evidence, concepts, existing_records=None):
        self.calls += len(evidence)
        self.last_evidence_ids = [e.evidence_id for e in evidence]
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


def _router(mock_scorer: CountingMockScorer, *, shadow: bool = False) -> AssignmentRouter:
    prefilter = ShadowPrefilter() if shadow else None
    return AssignmentRouter.default(mock_scorer, include_old_poe_mappers=False, shadow_prefilter=prefilter)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Compact prompt tests
# ---------------------------------------------------------------------------

class TestCompactPrompt:
    def test_system_prompt_contains_verdict_values(self):
        assert "supports_true" in SCORER_SYSTEM_PROMPT
        assert "supports_false" in SCORER_SYSTEM_PROMPT
        assert "neutral" in SCORER_SYSTEM_PROMPT

    def test_system_prompt_requires_json_only_output(self):
        prompt_lower = SCORER_SYSTEM_PROMPT.lower()
        assert "json" in prompt_lower
        assert "markdown" in prompt_lower

    def test_user_message_contains_concept_names(self):
        ev = _evidence("ev001", text="Art sales surged at Sotheby's auction.")
        concepts = [_concept("AuctionEffect"), _concept("MarketPressure")]
        msg = build_scorer_user_message(ev, concepts)
        assert "AuctionEffect" in msg
        assert "MarketPressure" in msg

    def test_user_message_contains_evidence_id(self):
        ev = _evidence("ev_abc123", text="Some text.")
        concepts = [_concept("TestConcept")]
        msg = build_scorer_user_message(ev, concepts)
        assert "ev_abc123" in msg

    def test_user_message_includes_concept_definitions(self):
        ev = _evidence("ev001", text="Text.")
        concept = _concept("AuctionEffect", definition="A specific definition for testing.")
        msg = build_scorer_user_message(ev, [concept])
        assert "A specific definition for testing." in msg

    def test_compact_user_message_smaller_than_schema_version(self):
        """Compact message should be smaller because schema block is removed."""
        ev = _evidence("ev001", text="Long auction house article about market trends.")
        # Use names that are not substrings of each other
        names = [f"UniqueConceptAlpha{i:02d}" for i in range(11)]
        concepts = [_concept(n) for n in names]
        msg = build_scorer_user_message(ev, concepts)
        # New format: each concept name appears exactly once (in concept list),
        # not twice (old format repeated names in schema block too).
        for name in names:
            assert msg.count(name) == 1, f"{name!r} appeared {msg.count(name)} times"

    def test_compact_prompt_output_schema_still_parseable(self):
        """Verify the scorer still parses compact-format responses correctly."""
        from poea.concepts.scorer import _extract_json_object

        # Simulate a compact JSON response (no fences, no trailing prose)
        compact_response = json.dumps({"AuctionEffect": {"verdict": "supports_true", "confidence": 0.85}})
        parsed = _extract_json_object(compact_response)
        assert parsed is not None
        assert parsed["AuctionEffect"]["verdict"] == "supports_true"
        assert parsed["AuctionEffect"]["confidence"] == 0.85

    def test_compact_prompt_missing_concept_defaults_to_neutral(self):
        """Parser should handle missing concepts gracefully (unchanged behavior)."""
        from poea.concepts.scorer import _build_assignment

        concept = _concept("MissingConcept")
        raw_verdict = {}
        verdict_str = str(raw_verdict.get("verdict", "neutral"))
        assignment = _build_assignment(concept, verdict_str, 0.0, soft_threshold=0.5)
        assert assignment.assigned_value is None
        assert assignment.missingness == "MISSING"


# ---------------------------------------------------------------------------
# Shadow prefilter tests
# ---------------------------------------------------------------------------

class TestShadowPrefilter:
    def test_shadow_prefilter_does_not_skip_llm_calls(self):
        """Shadow prefilter runs but does not change any scoring outputs."""
        concepts = [_concept("AuctionCatalyst")]
        evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
        mock = CountingMockScorer()
        router = _router(mock, shadow=True)

        result = router.score_all(evidence, concepts)

        # LLM still called (shadow mode = no skipping)
        assert mock.calls == 1
        assert result.records[0].assignments[0].assigned_value is True

    def test_shadow_prefilter_reports_would_skip_stats(self):
        """Shadow prefilter metadata should appear in routing metadata for semantic records."""
        concepts = [_concept("ArtMarketPressure", "A concept about market selling pressure.")]
        # Evidence text that clearly doesn't mention art market pressure
        evidence = [
            _evidence("ev001", text="The Eiffel Tower was built in 1889.", metadata={"evidence_type": "prose_text"}),
        ]
        mock = CountingMockScorer()
        router = _router(mock, shadow=True)

        result = router.score_all(evidence, concepts)

        # Should still call LLM
        assert mock.calls == 1
        # Shadow prefilter results in metadata
        shadow = result.metadata.get("shadow_prefilter", {})
        assert isinstance(shadow, dict)
        assert "total_pairs" in shadow
        assert "would_skip_pairs" in shadow
        assert "false_negatives" in shadow
        assert "skip_rate" in shadow

    def test_shadow_prefilter_no_false_negatives_on_matched_evidence(self):
        """If evidence clearly matches concept keywords, prefilter shouldn't flag it for skipping."""
        concepts = [_concept("AuctionEffect", "Auction sales and bidding effects.")]
        # Evidence clearly about auctions
        evidence = [
            _evidence("ev001", text="The auction at Sotheby's showed record bidding.", metadata={"evidence_type": "prose_text"}),
        ]
        prefilter = ShadowPrefilter(lexical_threshold=0.05)
        should_skip = prefilter.would_skip(evidence[0], concepts[0])
        # "auction", "sales", "bidding" are all in text — should NOT be skipped
        assert not should_skip

    def test_shadow_mode_outputs_unchanged_vs_no_shadow(self):
        """Results with shadow prefilter must be identical to results without."""
        concepts = [_concept("TestConcept")]
        evidence = [
            _evidence("ev001", metadata={"evidence_type": "prose_text"}),
            _evidence("ev002", metadata={"evidence_type": "prose_text"}),
        ]

        mock1 = CountingMockScorer()
        router1 = _router(mock1, shadow=False)
        result1 = router1.score_all(evidence, concepts)

        mock2 = CountingMockScorer()
        router2 = _router(mock2, shadow=True)
        result2 = router2.score_all(evidence, concepts)

        assert mock1.calls == mock2.calls
        for r1, r2 in zip(result1.records, result2.records):
            assert r1.evidence_id == r2.evidence_id
            assert r1.assignments[0].assigned_value == r2.assignments[0].assigned_value

    def test_shadow_prefilter_relevance_score_range(self):
        prefilter = ShadowPrefilter()
        concept = _concept("AuctionEffect", "Auction sales and bidding.")
        ev_relevant = _evidence("ev1", text="The auction sales were high this quarter.")
        ev_irrelevant = _evidence("ev2", text="Weather patterns in South America.")
        assert prefilter.relevance(ev_relevant, concept) > prefilter.relevance(ev_irrelevant, concept)

    def test_shadow_prefilter_analyze_returns_analysis(self):
        prefilter = ShadowPrefilter(lexical_threshold=0.1)
        concepts = [_concept("AuctionCatalyst", "Auction bidding activity."), _concept("MarketCollapse", "Market selling collapse.")]
        evidence = [
            _evidence("ev1", text="Auction houses reported strong bidding."),
            _evidence("ev2", text="The weather was nice today."),
        ]
        analysis = prefilter.analyze(evidence, concepts)
        assert isinstance(analysis, ShadowPrefilterAnalysis)
        assert analysis.total_pairs == 4  # 2 records × 2 concepts
        assert 0 <= analysis.would_skip_pairs <= 4
        assert 0.0 <= analysis.skip_rate <= 1.0

    def test_shadow_prefilter_false_negative_detection(self):
        """False negative: prefilter would skip but actual verdict was true/false."""
        prefilter = ShadowPrefilter(lexical_threshold=1.0)  # Skip everything
        concepts = [_concept("AuctionCatalyst")]
        evidence = [_evidence("ev1", text="Some irrelevant text.")]
        actual_records = [
            ScoredRecord(
                evidence_id="ev1",
                assignments=[
                    ConceptAssignment(
                        concept_id=concepts[0].concept_id,
                        variable_name="AuctionCatalyst",
                        assigned_value=True,  # Actual verdict was true
                        confidence=0.9,
                        missingness="OBSERVED",
                    )
                ],
            )
        ]
        analysis = prefilter.analyze(evidence, concepts, actual_records=actual_records)
        # Threshold=1.0 means would skip everything; actual had true verdict → false negative
        assert analysis.false_negatives >= 1


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestScoringCache:
    def test_cache_prevents_repeated_llm_calls(self):
        concept = _concept("Alpha")
        evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
        cached = ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id=concept.concept_id,
                    variable_name=concept.name,
                    assigned_value=False,
                    confidence=0.75,
                    missingness="OBSERVED",
                )
            ],
        )
        mock = CountingMockScorer()
        router = _router(mock)

        result = router.score_all(evidence, [concept], existing_records=[cached])

        assert mock.calls == 0
        assert result.records[0] == cached
        assert result.stats.cache_hits == 1

    def test_cache_miss_triggers_llm_call(self):
        concept = _concept("Alpha")
        other_concept = _concept("Beta")
        evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
        # Cache has Alpha but not Beta
        cached = ScoredRecord(
            evidence_id="ev001",
            assignments=[
                ConceptAssignment(
                    concept_id=concept.concept_id,
                    variable_name=concept.name,
                    assigned_value=True,
                    confidence=0.9,
                    missingness="OBSERVED",
                )
            ],
        )
        mock = CountingMockScorer()
        router = _router(mock)

        # We now have both Alpha and Beta as active concepts; cache only covers Alpha
        router.score_all(evidence, [concept, other_concept], existing_records=[cached])

        # Cache miss because Beta not in cache → LLM called
        assert mock.calls == 1


# ---------------------------------------------------------------------------
# Routing correctness tests
# ---------------------------------------------------------------------------

class TestRoutingCorrectness:
    def test_structured_evidence_routes_deterministic_not_llm(self):
        concepts = [_concept("LiquidityStress")]
        evidence = [
            _evidence("ev001", metadata={
                "evidence_type": "structured_numeric",
                "assignment_mode": "deterministic",
                "deterministic_assignments": {"LiquidityStress": True},
            })
        ]
        mock = CountingMockScorer()
        router = _router(mock)
        result = router.score_all(evidence, concepts)

        assert mock.calls == 0
        assert result.stats.scored == 0
        assert result.metadata["mode_counts"].get("deterministic", 0) == 1

    def test_old_poe_mapper_used_for_structured_domains(self, monkeypatch):
        from types import SimpleNamespace
        from uuid import UUID

        var_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        concept = ConceptEntry(
            concept_id=str(var_id),
            name="RegimeShift",
            definition="Old POE macro variable.",
            confidence=1.0,
            supporting_evidence_ids=["ev001"],
            status="active",
        )

        pipeline_module = SimpleNamespace(
            MockPipeline=type("MockPipeline", (), {
                "build_evidence_record": staticmethod(lambda snap: SimpleNamespace(
                    observed_assignments=[SimpleNamespace(
                        variable_id=var_id, observed_value=True,
                        missingness="OBSERVED", confidence=0.95,
                    )]
                ))
            }),
            MockSnapshot=type("MockSnapshot", (), {"__init__": lambda self, **kw: None}),
        )
        domain_module = SimpleNamespace(
            get_variables=lambda: {"RegimeShift": SimpleNamespace(variable_id=var_id, name="RegimeShift")}
        )
        monkeypatch.setattr(
            "poea.assignments.poe_compat.importlib.import_module",
            lambda name: pipeline_module if name.endswith(".pipeline") else domain_module,
        )

        adapter = OldPOEDomainMapperAdapter(
            OldPOEDomainMapperSpec("test-domain-v1", "test_domain_v1", "MockPipeline", "MockSnapshot")
        )
        mock = CountingMockScorer()
        direct = DirectStructuredAssignmentBackend()
        semantic = SemanticLLMScorerBackend(mock)  # type: ignore[arg-type]
        deterministic = DeterministicMapperBackend({"test-domain-v1": adapter}, include_old_poe_mappers=False)
        router = AssignmentRouter(
            direct_backend=direct,
            deterministic_backend=deterministic,
            semantic_backend=semantic,
            hybrid_backend=HybridPrefilterScorerBackend(direct, semantic),
        )
        evidence = [_evidence("ev001", metadata={
            "evidence_type": "structured_numeric",
            "old_poe_domain": "test-domain-v1",
            "old_poe_snapshot": {"x": 1},
        })]

        result = router.score_all(evidence, [concept])

        assert mock.calls == 0
        assert result.records[0].assignments[0].assigned_value is True

    def test_unknown_structured_errors_without_llm(self):
        concept = _concept("SomeVariable")
        evidence = [_evidence("ev001", metadata={"evidence_type": "structured_numeric"})]
        mock = CountingMockScorer()
        router = _router(mock)
        result = router.score_all(evidence, [concept])

        assert mock.calls == 0
        assert result.stats.errors == 1
        assert result.records[0].error is not None
        assert "No deterministic mapper" in result.records[0].error

    def test_art_prose_evidence_routes_to_semantic(self):
        from poea.evidence.normalizer import normalize_record
        unit = normalize_record(
            {"title": "Art Market Report", "notes": "Auction sales surged at Sotheby's."},
            source="art_source.json",
            domain_tag="art",
        )
        assert unit.metadata.get("evidence_type") == "prose_text"
        mock = CountingMockScorer()
        router = _router(mock)
        result = router.score_all([unit], [_concept("AuctionCatalyst")])
        assert mock.calls == 1
        assert result.metadata["mode_counts"].get("semantic", 0) == 1

    def test_prose_text_evidence_type_routes_to_semantic(self):
        concepts = [_concept("AuctionEffect")]
        evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
        mock = CountingMockScorer()
        router = _router(mock)
        result = router.score_all(evidence, concepts)
        assert mock.calls == 1
        assert result.metadata["mode_counts"] == {"semantic": 1}


# ---------------------------------------------------------------------------
# Cost and routing metrics
# ---------------------------------------------------------------------------

class TestCostRoutingMetrics:
    def test_routing_metrics_deterministic_on_same_input(self):
        concepts = [_concept("Alpha"), _concept("Beta")]
        evidence = [
            _evidence("ev1", metadata={"evidence_type": "prose_text"}),
            _evidence("ev2", metadata={"evidence_type": "structured_numeric",
                                       "deterministic_assignments": {"Alpha": True, "Beta": False}}),
        ]
        mock = CountingMockScorer()
        router = _router(mock)

        results = [router.score_all(evidence, concepts) for _ in range(3)]
        mode_counts = [r.metadata["mode_counts"] for r in results]

        # All three runs should produce identical mode counts
        assert mode_counts[0] == mode_counts[1] == mode_counts[2]

    def test_fireworks_calls_avoided_by_deterministic_in_metadata(self):
        concepts = [_concept("LiquidityStress")]
        evidence = [
            _evidence("ev1", metadata={"assignment_mode": "direct_structured",
                                       "structured_assignments": {"LiquidityStress": True}}),
            _evidence("ev2", metadata={"assignment_mode": "direct_structured",
                                       "structured_assignments": {"LiquidityStress": False}}),
            _evidence("ev3", metadata={"evidence_type": "prose_text"}),
        ]
        mock = CountingMockScorer()
        router = _router(mock)
        result = router.score_all(evidence, concepts)

        meta = result.metadata
        assert meta["fireworks_calls_made"] == 1
        assert meta["fireworks_calls_avoided_by_deterministic"] == 2
        assert meta["fireworks_calls_avoided_by_cache"] == 0

    def test_cache_avoided_calls_in_metadata(self):
        concept = _concept("Alpha")
        evidence = [_evidence("ev001", metadata={"evidence_type": "prose_text"})]
        cached = ScoredRecord(
            evidence_id="ev001",
            assignments=[ConceptAssignment(
                concept_id=concept.concept_id, variable_name=concept.name,
                assigned_value=True, confidence=0.9, missingness="OBSERVED",
            )],
        )
        mock = CountingMockScorer()
        router = _router(mock)
        result = router.score_all(evidence, [concept], existing_records=[cached])

        assert result.metadata["fireworks_calls_avoided_by_cache"] == 1
        assert result.metadata["fireworks_calls_made"] == 0
