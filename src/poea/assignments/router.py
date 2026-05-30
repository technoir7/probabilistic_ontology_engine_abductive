from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping, Protocol, Sequence

from ..concepts.scorer import (
    ConceptAssignment,
    EvidenceScorer,
    ScoredRecord,
    ScoringStats,
    _accumulate_stats,
    _neutral_assignments,
)
from ..evidence.schemas import EvidenceUnit
from ..registry.schemas import ConceptEntry
from .poe_compat import OldPOEMapperError, discover_old_poe_domain_mappers

AssignmentMode = Literal["direct_structured", "deterministic", "semantic", "hybrid"]
MapperResult = ScoredRecord | Sequence[ConceptAssignment] | Mapping[str, Any]
DeterministicMapper = Callable[[EvidenceUnit, Sequence[ConceptEntry]], MapperResult]

_DIRECT_ASSIGNMENT_KEYS = (
    "structured_assignments",
    "concept_assignments",
    "assignments",
)
_DETERMINISTIC_ASSIGNMENT_KEYS = (
    "deterministic_assignments",
    "rule_assignments",
)


class AssignmentBackend(Protocol):
    """Backend contract for translating evidence into concept assignments."""

    backend_name: str

    def score_all(
        self,
        evidence: Sequence[EvidenceUnit],
        concepts: Sequence[ConceptEntry],
    ) -> list[ScoredRecord]:
        """Return one scored record per evidence record."""
        ...


@dataclass(frozen=True)
class AssignmentDecision:
    evidence_id: str
    mode: AssignmentMode
    backend: str
    reason: str


@dataclass
class AssignmentResult:
    records: list[ScoredRecord]
    stats: ScoringStats
    metadata: dict[str, Any] = field(default_factory=dict)


class DirectStructuredAssignmentBackend:
    """
    Translate existing structured assignments into POE-A scored records.

    Supported evidence metadata keys are ``structured_assignments``,
    ``concept_assignments``, and ``assignments``. Assignment maps may be keyed
    by concept_id or concept name. Values may be booleans, null, or dicts with
    ``value``/``assigned_value``, optional ``confidence``, and optional
    ``missingness``.
    """

    backend_name = "direct_structured"

    def __init__(self, soft_observed_threshold: float = 0.5) -> None:
        self._soft_observed_threshold = soft_observed_threshold

    def score_all(
        self,
        evidence: Sequence[EvidenceUnit],
        concepts: Sequence[ConceptEntry],
    ) -> list[ScoredRecord]:
        return [self.score_record(unit, concepts) for unit in evidence]

    def score_record(
        self,
        evidence: EvidenceUnit,
        concepts: Sequence[ConceptEntry],
    ) -> ScoredRecord:
        raw_assignments = _first_mapping(evidence.metadata, _DIRECT_ASSIGNMENT_KEYS)
        assignments = [
            _assignment_from_mapping(
                concept=concept,
                raw_assignments=raw_assignments,
                soft_observed_threshold=self._soft_observed_threshold,
            )
            for concept in concepts
        ]
        return ScoredRecord(evidence_id=evidence.evidence_id, assignments=assignments)

    @staticmethod
    def has_assignments(evidence: EvidenceUnit) -> bool:
        return _first_mapping(evidence.metadata, _DIRECT_ASSIGNMENT_KEYS) != {}


class DeterministicMapperBackend:
    """
    Run registered deterministic domain mappers or rule assignments.

    This is the POE-A analogue of POE's domain evidence mappers: structured
    observations should become assignments through deterministic code, not LLM
    interpretation. If a record is routed here without a matching mapper or
    assignment map, it receives all-neutral assignments with a record-level
    error explaining the missing deterministic mapper.
    """

    backend_name = "deterministic_mapper"

    def __init__(
        self,
        mappers: Mapping[str, DeterministicMapper] | None = None,
        soft_observed_threshold: float = 0.5,
        include_old_poe_mappers: bool = True,
    ) -> None:
        self._mappers = (
            discover_old_poe_domain_mappers()
            if include_old_poe_mappers
            else {}
        )
        self._mappers.update(mappers or {})
        self._soft_observed_threshold = soft_observed_threshold
        self._direct = DirectStructuredAssignmentBackend(
            soft_observed_threshold=soft_observed_threshold
        )

    def score_all(
        self,
        evidence: Sequence[EvidenceUnit],
        concepts: Sequence[ConceptEntry],
    ) -> list[ScoredRecord]:
        return [self.score_record(unit, concepts) for unit in evidence]

    def score_record(
        self,
        evidence: EvidenceUnit,
        concepts: Sequence[ConceptEntry],
    ) -> ScoredRecord:
        raw_assignments = _first_mapping(evidence.metadata, _DETERMINISTIC_ASSIGNMENT_KEYS)
        if raw_assignments:
            assignments = [
                _assignment_from_mapping(
                    concept=concept,
                    raw_assignments=raw_assignments,
                    soft_observed_threshold=self._soft_observed_threshold,
                )
                for concept in concepts
            ]
            return ScoredRecord(evidence_id=evidence.evidence_id, assignments=assignments)

        mapper_id = str(
            evidence.metadata.get("old_poe_domain")
            or evidence.metadata.get("poe_domain")
            or evidence.metadata.get("domain_id")
            or evidence.metadata.get("domain_module_id")
            or evidence.metadata.get("old_poe_mapper")
            or evidence.metadata.get("poe_mapper")
            or evidence.metadata.get("evidence_mapper")
            or evidence.metadata.get("deterministic_mapper")
            or evidence.metadata.get("mapper_id")
            or evidence.domain_tag
        )
        mapper = self._mappers.get(mapper_id)
        if mapper is None:
            return ScoredRecord(
                evidence_id=evidence.evidence_id,
                assignments=_neutral_assignments(list(concepts)),
                error=f"No deterministic mapper registered for '{mapper_id}'",
            )

        try:
            return _coerce_mapper_result(
                evidence=evidence,
                concepts=concepts,
                result=mapper(evidence, concepts),
                soft_observed_threshold=self._soft_observed_threshold,
            )
        except OldPOEMapperError as exc:
            return ScoredRecord(
                evidence_id=evidence.evidence_id,
                assignments=_neutral_assignments(list(concepts)),
                error=str(exc),
            )


class SemanticLLMScorerBackend:
    """Assignment backend wrapping the existing LLM evidence scorer."""

    backend_name = "semantic_llm"

    def __init__(self, scorer: EvidenceScorer) -> None:
        self._scorer = scorer

    def score_all(
        self,
        evidence: Sequence[EvidenceUnit],
        concepts: Sequence[ConceptEntry],
    ) -> list[ScoredRecord]:
        records, _ = self._scorer.score_all(list(evidence), list(concepts))
        return records


class HybridPrefilterScorerBackend:
    """
    Conservative hybrid backend for mixed records.

    Current behavior avoids LLM calls for records that already contain direct
    structured assignments and delegates remaining mixed records to the semantic
    scorer. It is intentionally conservative; sparse concept filtering can be
    added later behind this interface after shadow-mode validation.
    """

    backend_name = "hybrid_prefilter"

    def __init__(
        self,
        direct_backend: DirectStructuredAssignmentBackend,
        semantic_backend: SemanticLLMScorerBackend,
    ) -> None:
        self._direct = direct_backend
        self._semantic = semantic_backend

    def score_all(
        self,
        evidence: Sequence[EvidenceUnit],
        concepts: Sequence[ConceptEntry],
    ) -> list[ScoredRecord]:
        records: dict[str, ScoredRecord] = {}
        semantic_units: list[EvidenceUnit] = []
        for unit in evidence:
            if self._direct.has_assignments(unit):
                records[unit.evidence_id] = self._direct.score_record(unit, concepts)
            else:
                semantic_units.append(unit)
        for record in self._semantic.score_all(semantic_units, concepts):
            records[record.evidence_id] = record
        return [records[unit.evidence_id] for unit in evidence]


class AssignmentRouter:
    """
    Deterministically route evidence records to assignment backends.

    The router never calls an LLM to decide whether an LLM should be used. It
    uses explicit metadata first, then structural signals. Only explicit
    prose/unstructured evidence routes to semantic scoring; unknown structured
    records use deterministic mapping and fail loudly if no mapper exists.
    """

    def __init__(
        self,
        *,
        direct_backend: DirectStructuredAssignmentBackend,
        deterministic_backend: DeterministicMapperBackend,
        semantic_backend: SemanticLLMScorerBackend,
        hybrid_backend: HybridPrefilterScorerBackend,
    ) -> None:
        self._backends: dict[AssignmentMode, AssignmentBackend] = {
            "direct_structured": direct_backend,
            "deterministic": deterministic_backend,
            "semantic": semantic_backend,
            "hybrid": hybrid_backend,
        }

    @classmethod
    def default(
        cls,
        scorer: EvidenceScorer,
        *,
        soft_observed_threshold: float = 0.5,
        deterministic_mappers: Mapping[str, DeterministicMapper] | None = None,
        include_old_poe_mappers: bool = True,
    ) -> "AssignmentRouter":
        direct = DirectStructuredAssignmentBackend(
            soft_observed_threshold=soft_observed_threshold
        )
        deterministic = DeterministicMapperBackend(
            mappers=deterministic_mappers,
            soft_observed_threshold=soft_observed_threshold,
            include_old_poe_mappers=include_old_poe_mappers,
        )
        semantic = SemanticLLMScorerBackend(scorer)
        hybrid = HybridPrefilterScorerBackend(direct, semantic)
        return cls(
            direct_backend=direct,
            deterministic_backend=deterministic,
            semantic_backend=semantic,
            hybrid_backend=hybrid,
        )

    def decide(self, evidence: EvidenceUnit) -> AssignmentDecision:
        metadata = evidence.metadata
        explicit_mode = str(metadata.get("assignment_mode", "")).strip().lower()
        evidence_type = str(
            metadata.get("evidence_type")
            or metadata.get("assignment_evidence_type")
            or ""
        ).strip().lower()

        if explicit_mode in {"direct", "direct_structured", "structured_direct"}:
            return self._decision(evidence, "direct_structured", "explicit assignment_mode")
        if explicit_mode in {"deterministic", "mapper", "rule_based", "rule-based"}:
            return self._decision(evidence, "deterministic", "explicit assignment_mode")
        if explicit_mode in {"semantic", "llm", "semantic_llm"}:
            return self._decision(evidence, "semantic", "explicit assignment_mode")
        if explicit_mode == "hybrid":
            return self._decision(evidence, "hybrid", "explicit assignment_mode")

        if DirectStructuredAssignmentBackend.has_assignments(evidence):
            return self._decision(evidence, "direct_structured", "structured assignments present")

        if _first_mapping(metadata, _DETERMINISTIC_ASSIGNMENT_KEYS):
            return self._decision(evidence, "deterministic", "deterministic assignments present")

        if evidence_type in {"structured_numeric", "time_series", "tabular", "api_derived"}:
            return self._decision(evidence, "deterministic", f"evidence_type={evidence_type}")
        if evidence_type in {"structured_json_with_assignments", "already_assigned"}:
            return self._decision(evidence, "direct_structured", f"evidence_type={evidence_type}")
        if evidence_type == "mixed":
            return self._decision(evidence, "hybrid", "evidence_type=mixed")
        if evidence_type in {"prose", "prose_text", "article", "text", "unstructured_text"}:
            return self._decision(evidence, "semantic", f"evidence_type={evidence_type}")

        if metadata.get("numeric_observations") or metadata.get("time_series"):
            return self._decision(evidence, "deterministic", "structured numeric metadata present")
        if metadata.get("requires_semantic_assignment") is True:
            return self._decision(evidence, "semantic", "requires_semantic_assignment=true")

        return self._decision(evidence, "deterministic", "default deterministic route")

    def score_all(
        self,
        evidence: Sequence[EvidenceUnit],
        concepts: Sequence[ConceptEntry],
        existing_records: Sequence[ScoredRecord] | None = None,
    ) -> AssignmentResult:
        evidence_list = list(evidence)
        concept_list = list(concepts)
        active_ids = {c.concept_id for c in concept_list}
        existing_by_id = {r.evidence_id: r for r in existing_records or []}

        stats = ScoringStats(
            total_records=len(evidence_list),
            scored=0,
            cache_hits=0,
            errors=0,
            total_pairs=len(evidence_list) * len(concept_list),
        )
        result_by_id: dict[str, ScoredRecord] = {}
        decisions: list[AssignmentDecision] = []
        routed: dict[AssignmentMode, list[EvidenceUnit]] = {
            "direct_structured": [],
            "deterministic": [],
            "semantic": [],
            "hybrid": [],
        }

        for unit in evidence_list:
            existing = existing_by_id.get(unit.evidence_id)
            if existing is not None and active_ids <= {a.concept_id for a in existing.assignments}:
                result_by_id[unit.evidence_id] = existing
                stats.cache_hits += 1
                _accumulate_stats(stats, existing, concept_list)
                decisions.append(
                    AssignmentDecision(
                        evidence_id=unit.evidence_id,
                        mode="direct_structured",
                        backend="cache",
                        reason="existing scored record covers active concepts",
                    )
                )
                continue

            decision = self.decide(unit)
            decisions.append(decision)
            routed[decision.mode].append(unit)

        for mode in ("direct_structured", "deterministic", "hybrid", "semantic"):
            units = routed[mode]
            if not units:
                continue
            backend = self._backends[mode]
            records = backend.score_all(units, concept_list)
            for record in records:
                result_by_id[record.evidence_id] = record
                if record.error:
                    stats.errors += 1
                if mode == "semantic":
                    stats.scored += 1
                elif mode == "hybrid" and not DirectStructuredAssignmentBackend.has_assignments(
                    _unit_by_id(units, record.evidence_id)
                ):
                    stats.scored += 1
                _accumulate_stats(stats, record, concept_list)

        ordered = [result_by_id[unit.evidence_id] for unit in evidence_list]
        mode_counts = Counter(d.mode for d in decisions if d.backend != "cache")
        backend_counts = Counter(d.backend for d in decisions)
        metadata = {
            "router": "AssignmentRouter",
            "mode_counts": dict(sorted(mode_counts.items())),
            "backend_counts": dict(sorted(backend_counts.items())),
            "decisions": [
                {
                    "evidence_id": d.evidence_id,
                    "mode": d.mode,
                    "backend": d.backend,
                    "reason": d.reason,
                }
                for d in decisions
            ],
        }
        return AssignmentResult(records=ordered, stats=stats, metadata=metadata)

    def _decision(
        self,
        evidence: EvidenceUnit,
        mode: AssignmentMode,
        reason: str,
    ) -> AssignmentDecision:
        return AssignmentDecision(
            evidence_id=evidence.evidence_id,
            mode=mode,
            backend=self._backends[mode].backend_name,
            reason=reason,
        )


def _first_mapping(metadata: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _assignment_from_mapping(
    *,
    concept: ConceptEntry,
    raw_assignments: Mapping[str, Any],
    soft_observed_threshold: float,
) -> ConceptAssignment:
    raw = raw_assignments.get(concept.concept_id, raw_assignments.get(concept.name))
    assigned_value, confidence, missingness = _parse_assignment_value(
        raw,
        soft_observed_threshold=soft_observed_threshold,
    )
    return ConceptAssignment(
        concept_id=concept.concept_id,
        variable_name=concept.name,
        assigned_value=assigned_value,
        confidence=confidence,
        missingness=missingness,
    )


def _parse_assignment_value(
    raw: Any,
    *,
    soft_observed_threshold: float,
) -> tuple[bool | None, float, str]:
    if raw is None:
        return None, 0.0, "MISSING"

    if isinstance(raw, dict):
        value = raw.get(
            "assigned_value",
            raw.get("value", raw.get("observed_value", raw.get("verdict"))),
        )
        confidence = float(raw.get("confidence", 1.0) or 0.0)
        missingness = raw.get("missingness")
    else:
        value = raw
        confidence = 1.0
        missingness = None

    assigned_value = _coerce_bool_or_none(value)
    if missingness == "MISSING":
        return None, confidence, "MISSING"
    if assigned_value is None:
        return None, confidence, "MISSING"

    if missingness in {"OBSERVED", "SOFT_OBSERVED"}:
        rendered_missingness = str(missingness)
    else:
        rendered_missingness = (
            "SOFT_OBSERVED"
            if confidence < soft_observed_threshold
            else "OBSERVED"
        )
    return assigned_value, confidence, rendered_missingness


def _coerce_bool_or_none(value: Any) -> bool | None:
    if value is True or value is False or value is None:
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "supports_true"}:
            return True
        if normalized in {"false", "no", "0", "supports_false"}:
            return False
        if normalized in {"neutral", "missing", "none", "null"}:
            return None
    return None


def _coerce_mapper_result(
    *,
    evidence: EvidenceUnit,
    concepts: Sequence[ConceptEntry],
    result: MapperResult,
    soft_observed_threshold: float,
) -> ScoredRecord:
    if isinstance(result, ScoredRecord):
        return result
    if isinstance(result, Mapping):
        assignments = [
            _assignment_from_mapping(
                concept=concept,
                raw_assignments=result,
                soft_observed_threshold=soft_observed_threshold,
            )
            for concept in concepts
        ]
        return ScoredRecord(evidence_id=evidence.evidence_id, assignments=assignments)
    return ScoredRecord(evidence_id=evidence.evidence_id, assignments=list(result))


def _unit_by_id(units: Sequence[EvidenceUnit], evidence_id: str) -> EvidenceUnit:
    for unit in units:
        if unit.evidence_id == evidence_id:
            return unit
    raise KeyError(evidence_id)
