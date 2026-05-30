"""Tests for the shadow prefilter evaluator (prefilter_eval.py)."""
from __future__ import annotations

from poea.assignments.prefilter_eval import (
    EvaluationResult,
    PrefilterEvaluator,
    ThresholdResult,
    _make_recommendation,
)
from poea.evidence.schemas import EvidenceUnit
from poea.registry.schemas import ConceptEntry, concept_id_from_name

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _concept(name: str, definition: str = "A causal mechanism about things.") -> ConceptEntry:
    return ConceptEntry(
        concept_id=concept_id_from_name(name),
        name=name,
        definition=definition,
        confidence=0.9,
        supporting_evidence_ids=["ev001"],
        status="active",
    )


def _evidence(eid: str, title: str = "Evidence", text: str = "") -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=eid,
        source="test",
        title=title,
        domain_tag="art",
        text=text,
        metadata={"sparse_text": True} if not text else {},
    )


def _scored_record(ev_id: str, assignments: dict[str, bool | None]) -> dict:
    return {
        "evidence_id": ev_id,
        "assignments": [
            {"variable_name": name, "assigned_value": val}
            for name, val in assignments.items()
        ],
    }


# ---------------------------------------------------------------------------
# ThresholdResult properties
# ---------------------------------------------------------------------------

class TestThresholdResult:
    def test_skip_rate_zero(self):
        tr = ThresholdResult(0.0, 100, 0, 0, 0, 0, 0, 10)
        assert tr.skip_rate == 0.0

    def test_skip_rate_half(self):
        tr = ThresholdResult(0.5, 100, 50, 0, 0, 0, 0, 10)
        assert tr.skip_rate == 0.5

    def test_recall_perfect(self):
        tr = ThresholdResult(0.0, 100, 0, 0, 0, 0, 0, 10)
        assert tr.recall == 1.0

    def test_recall_partial(self):
        tr = ThresholdResult(0.05, 100, 50, 5, 4, 3, 1, 10)
        assert abs(tr.recall - 0.6) < 1e-9

    def test_recall_zero_observed(self):
        tr = ThresholdResult(0.0, 100, 0, 0, 0, 0, 0, 0)
        assert tr.recall == 1.0

    def test_estimated_cost_savings(self):
        # 10 skipped records × 1250 tokens × $1.74/M
        tr = ThresholdResult(0.05, 100, 50, 10, 0, 0, 0, 10)
        expected = 10 * 1250 / 1_000_000 * 1.74
        assert abs(tr.estimated_cost_savings_usd - expected) < 1e-9

    def test_table_row_format(self):
        tr = ThresholdResult(0.05, 770, 566, 20, 17, 16, 1, 38)
        row = tr.to_table_row()
        assert "0.05" in row
        assert "55.3%" in row  # recall = (38-17)/38 = 55.3%
        assert "566" in row


# ---------------------------------------------------------------------------
# PrefilterEvaluator correctness
# ---------------------------------------------------------------------------

class TestPrefilterEvaluator:
    def _make_minimal_corpus(self):
        """Two concepts, three evidence records, known assignments."""
        c1 = _concept("AuctionEffect", "Auction sales and bidding at auction houses.")
        c2 = _concept("MarketCollapse", "Market selling and price collapse scenario.")
        ev_relevant = _evidence("ev001", title="Auction house sale", text="Auction sales surged.")
        ev_irrelevant = _evidence("ev002", title="Nothing", text="Nothing about this.")
        ev_sparse = _evidence("ev003", title="Short title")
        concepts = [c1, c2]
        evidence = [ev_relevant, ev_irrelevant, ev_sparse]
        scored = [
            _scored_record("ev001", {"AuctionEffect": True, "MarketCollapse": None}),
            _scored_record("ev002", {"AuctionEffect": None, "MarketCollapse": None}),
            _scored_record("ev003", {"AuctionEffect": None, "MarketCollapse": False}),
        ]
        return evidence, concepts, scored

    def test_total_pairs_correct(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0])
        assert result.total_pairs == 6  # 3 records × 2 concepts

    def test_total_observed_correct(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0])
        assert result.total_observed == 2  # ev001/AuctionEffect=True, ev003/MarketCollapse=False

    def test_threshold_zero_has_no_skips(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0])
        assert result.threshold_results[0].skipped_pairs == 0
        assert result.threshold_results[0].false_negatives == 0
        assert result.threshold_results[0].recall == 1.0

    def test_high_threshold_skips_everything(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([1.0])
        tr = result.threshold_results[0]
        assert tr.skipped_pairs == 6
        assert tr.skipped_records == 3

    def test_false_negatives_counted_correctly(self):
        """A pair that would be skipped but has actual true/false is a FN."""
        # ev003 is sparse ("Short title") — no keywords match → relevance=0 for all concepts
        # ev003 has MarketCollapse=False → FN at any threshold > 0
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.01])  # threshold > 0 → skips relevance=0 pairs
        tr = result.threshold_results[0]
        # ev003/MarketCollapse has relevance=0 (sparse title, no keywords matched)
        # so it should be a false negative
        assert tr.false_negatives >= 1

    def test_fn_list_contains_correct_items(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([1.0])  # skip everything
        tr = result.threshold_results[0]
        fn_concepts = {fn.concept_name for fn in tr.fn_list}
        # AuctionEffect=True (ev001) and MarketCollapse=False (ev003) are both observed
        assert "AuctionEffect" in fn_concepts
        assert "MarketCollapse" in fn_concepts

    def test_recall_decreases_with_threshold(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0, 0.5, 1.0])
        recalls = [tr.recall for tr in result.threshold_results]
        # Recall should be non-increasing as threshold increases
        for i in range(len(recalls) - 1):
            assert recalls[i] >= recalls[i + 1]

    def test_skipped_records_at_zero_threshold(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0])
        assert result.threshold_results[0].skipped_records == 0

    def test_multiple_thresholds_evaluated(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0, 0.05, 0.1])
        assert len(result.threshold_results) == 3

    def test_thresholds_sorted_ascending(self):
        ev, c, s = self._make_minimal_corpus()
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.1, 0.0, 0.05])
        thresholds = [tr.threshold for tr in result.threshold_results]
        assert thresholds == sorted(thresholds)


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------

class TestMakeRecommendation:
    def _tr(self, threshold: float, skipped_records: int, fn: int, total_obs: int) -> ThresholdResult:
        return ThresholdResult(
            threshold=threshold,
            total_pairs=100,
            skipped_pairs=50,
            skipped_records=skipped_records,
            false_negatives=fn,
            fn_true=fn,
            fn_false=0,
            total_observed=total_obs,
        )

    def test_no_viable_threshold_recommends_redesign(self):
        # 13% FN rate at any positive threshold
        results = [
            self._tr(0.0, 0, 0, 38),   # skips nothing → no savings
            self._tr(0.01, 2, 5, 38),  # recall=87% → too low
        ]
        rec, _ = _make_recommendation(results)
        assert "Redesign" in rec

    def test_viable_threshold_recommends_enable(self):
        results = [
            self._tr(0.0, 0, 0, 10),   # no savings
            self._tr(0.05, 5, 0, 10),  # 100% recall, 5 records saved
        ]
        rec, _ = _make_recommendation(results)
        assert "Enable" in rec
        assert "0.05" in rec

    def test_prefers_highest_savings_with_viable_recall(self):
        results = [
            self._tr(0.0, 0, 0, 10),
            self._tr(0.03, 3, 0, 10),   # viable
            self._tr(0.05, 8, 0, 10),   # viable and saves more
            self._tr(0.10, 15, 2, 10),  # not viable (recall=80%)
        ]
        rec, _ = _make_recommendation(results)
        # Should pick 0.05 (highest viable savings)
        assert "0.05" in rec


# ---------------------------------------------------------------------------
# EvaluationResult markdown
# ---------------------------------------------------------------------------

class TestEvaluationResultMarkdown:
    def _minimal_result(self) -> EvaluationResult:
        tr0 = ThresholdResult(0.0, 770, 0, 0, 0, 0, 0, 38)
        tr1 = ThresholdResult(0.05, 770, 566, 20, 17, 16, 1, 38)
        return EvaluationResult(
            total_pairs=770,
            total_records=70,
            total_concepts=11,
            total_observed=38,
            total_true=35,
            total_false=3,
            total_neutral=732,
            threshold_results=[tr0, tr1],
            recommendation="C. Redesign prefilter",
            recommendation_reason="The prefilter cannot safely skip pairs.",
        )

    def test_markdown_contains_required_sections(self):
        md = self._minimal_result().to_markdown()
        assert "## Executive Summary" in md
        assert "## Threshold Comparison Table" in md
        assert "## False Negative Analysis" in md
        assert "## Cost Savings Analysis" in md
        assert "## Recommendation" in md

    def test_markdown_contains_recommendation(self):
        md = self._minimal_result().to_markdown()
        assert "Redesign prefilter" in md

    def test_markdown_contains_pair_counts(self):
        md = self._minimal_result().to_markdown()
        assert "770" in md
        assert "38" in md

    def test_markdown_contains_threshold_values(self):
        md = self._minimal_result().to_markdown()
        assert "0.00" in md
        assert "0.05" in md

    def test_markdown_is_valid_string(self):
        md = self._minimal_result().to_markdown()
        assert isinstance(md, str)
        assert len(md) > 500


# ---------------------------------------------------------------------------
# Full corpus evaluation (no API calls required)
# ---------------------------------------------------------------------------

class TestFullCorpusEvaluation:
    """Run evaluator against actual corpus artifacts to verify results match analysis."""

    def _load_artifacts(self):
        import json
        from pathlib import Path

        p = Path("artifacts")
        if not (p / "evidence.json").exists() or not (p / "scored_evidence.json").exists():
            return None, None, None

        with open(p / "evidence.json") as f:
            ev_data = json.load(f)
        with open(p / "canonical_concepts.json") as f:
            c_data = json.load(f)
        with open(p / "scored_evidence.json") as f:
            scored = json.load(f)

        from poea.evidence.schemas import EvidenceUnit
        from poea.registry.schemas import ConceptEntry

        evidence = [EvidenceUnit.model_validate(u) for u in ev_data]
        concepts = [ConceptEntry.model_validate(c) for c in c_data.get("concepts", [])]
        records = scored.get("scored_records", [])
        return evidence, concepts, records

    def test_full_corpus_total_pairs(self):
        ev, c, s = self._load_artifacts()
        if ev is None:
            return  # artifacts not available
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0])
        assert result.total_pairs == 770  # 70 × 11
        assert result.total_observed == 38

    def test_threshold_zero_has_perfect_recall(self):
        ev, c, s = self._load_artifacts()
        if ev is None:
            return
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0])
        assert result.threshold_results[0].recall == 1.0
        assert result.threshold_results[0].false_negatives == 0

    def test_threshold_01_has_five_false_negatives(self):
        ev, c, s = self._load_artifacts()
        if ev is None:
            return
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.01])
        tr = result.threshold_results[0]
        assert tr.false_negatives == 5
        assert abs(tr.recall - (38 - 5) / 38) < 1e-9

    def test_threshold_05_has_seventeen_false_negatives(self):
        ev, c, s = self._load_artifacts()
        if ev is None:
            return
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.05])
        tr = result.threshold_results[0]
        assert tr.false_negatives == 17

    def test_recommendation_is_redesign(self):
        ev, c, s = self._load_artifacts()
        if ev is None:
            return
        evaluator = PrefilterEvaluator(ev, c, s)
        result = evaluator.evaluate([0.0, 0.01, 0.03, 0.05, 0.10])
        assert "Redesign" in result.recommendation
