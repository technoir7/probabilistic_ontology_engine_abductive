"""
Shadow prefilter for semantic LLM scoring cost estimation.

Computes deterministic lexical relevance between evidence records and concepts.
Runs in shadow mode: never skips actual LLM calls, but reports which
(evidence, concept) pairs would be skipped by a future filter and estimates
the savings.

Usage:
    prefilter = ShadowPrefilter(lexical_threshold=0.05)
    analysis = prefilter.analyze(evidence_units, concepts, actual_scored_records)
    # analysis.would_skip_pairs  — how many pairs a filter would skip
    # analysis.false_negatives   — how many would-be-skipped pairs had true/false verdicts
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..evidence.schemas import EvidenceUnit
from ..registry.schemas import ConceptEntry

_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_STOPWORDS = frozenset(
    ["the", "and", "of", "in", "a", "an", "is", "are", "was", "were", "to", "for"]
)


def _concept_keywords(name: str, definition: str) -> frozenset[str]:
    """Extract searchable keywords from a concept name and definition snippet."""
    name_words = _CAMEL_SPLIT.sub(" ", name).lower().split()
    name_kws = frozenset(w for w in name_words if w not in _STOPWORDS and len(w) > 2)
    def_words = re.sub(r"[^a-z\s]", " ", definition.lower()).split()
    def_kws = frozenset(w for w in def_words if w not in _STOPWORDS and len(w) > 3)
    return name_kws | def_kws


@dataclass
class ShadowPrefilterAnalysis:
    total_pairs: int
    would_skip_pairs: int
    would_skip_records: int
    false_negatives: int
    skip_rate: float
    false_negative_rate: float
    concept_skip_counts: dict[str, int] = field(default_factory=dict)
    evidence_skip_counts: dict[str, int] = field(default_factory=dict)
    estimated_token_savings: int = 0
    estimated_cost_savings_usd: float = 0.0


class ShadowPrefilter:
    """
    Deterministic lexical prefilter running in shadow mode.

    Computes keyword overlap between evidence text and concept definitions.
    Reports what would be skipped without actually skipping anything.
    The threshold is intentionally conservative so false negatives remain low.
    """

    def __init__(
        self,
        lexical_threshold: float = 0.05,
        tokens_per_pair: int = 15,
        cost_per_m_tokens: float = 1.74,
    ) -> None:
        self._threshold = lexical_threshold
        self._tokens_per_pair = tokens_per_pair
        self._cost_per_m_tokens = cost_per_m_tokens

    def relevance(self, evidence: EvidenceUnit, concept: ConceptEntry) -> float:
        """
        Fraction of concept keywords present in evidence text.

        Returns 0.0 if no keywords, 1.0 if all keywords matched.
        """
        keywords = _concept_keywords(concept.name, concept.definition)
        if not keywords:
            return 1.0
        text_lower = (evidence.title + " " + evidence.text).lower()
        matched = sum(1 for kw in keywords if kw in text_lower)
        return matched / len(keywords)

    def would_skip(self, evidence: EvidenceUnit, concept: ConceptEntry) -> bool:
        return self.relevance(evidence, concept) < self._threshold

    def analyze(
        self,
        evidence_units: list[EvidenceUnit],
        concepts: list[ConceptEntry],
        actual_records: list | None = None,
    ) -> ShadowPrefilterAnalysis:
        """
        Analyze what a lexical prefilter would skip vs. actual scored outcomes.

        actual_records: list of ScoredRecord objects (optional).  When provided,
        computes false-negative count — pairs that would be skipped but had
        actual true/false verdicts.
        """
        actual_assignments: dict[tuple[str, str], bool | None] = {}
        if actual_records:
            for record in actual_records:
                ev_id = record.evidence_id if hasattr(record, "evidence_id") else record.get("evidence_id", "")
                assignments = (
                    record.assignments
                    if hasattr(record, "assignments")
                    else record.get("assignments", [])
                )
                for a in assignments:
                    c_name = a.variable_name if hasattr(a, "variable_name") else a.get("variable_name", "")
                    val = a.assigned_value if hasattr(a, "assigned_value") else a.get("assigned_value")
                    actual_assignments[(ev_id, c_name)] = val

        skip_pairs: list[tuple[str, str]] = []
        concept_skip: dict[str, int] = {c.name: 0 for c in concepts}
        evidence_skip: dict[str, int] = {}
        false_negatives = 0

        for ev in evidence_units:
            ev_skips = 0
            for concept in concepts:
                if self.would_skip(ev, concept):
                    skip_pairs.append((ev.evidence_id, concept.name))
                    concept_skip[concept.name] = concept_skip.get(concept.name, 0) + 1
                    ev_skips += 1
                    actual = actual_assignments.get((ev.evidence_id, concept.name))
                    if actual is True or actual is False:
                        false_negatives += 1
            if ev_skips > 0:
                evidence_skip[ev.evidence_id] = ev_skips

        total_pairs = len(evidence_units) * len(concepts)
        would_skip = len(skip_pairs)
        skip_rate = would_skip / total_pairs if total_pairs else 0.0
        fn_rate = false_negatives / would_skip if would_skip else 0.0
        would_skip_records = sum(
            1 for ev in evidence_units
            if all(self.would_skip(ev, c) for c in concepts)
        )

        est_token_savings = would_skip * self._tokens_per_pair
        est_cost_savings = est_token_savings / 1_000_000 * self._cost_per_m_tokens

        return ShadowPrefilterAnalysis(
            total_pairs=total_pairs,
            would_skip_pairs=would_skip,
            would_skip_records=would_skip_records,
            false_negatives=false_negatives,
            skip_rate=skip_rate,
            false_negative_rate=fn_rate,
            concept_skip_counts=concept_skip,
            evidence_skip_counts=evidence_skip,
            estimated_token_savings=est_token_savings,
            estimated_cost_savings_usd=est_cost_savings,
        )
