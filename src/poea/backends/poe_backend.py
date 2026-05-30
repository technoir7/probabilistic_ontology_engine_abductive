"""
POE Adapter — Phase 9.

Connects POE-A to the Probabilistic Ontology Engine (POE) structure learner.

Import path note:
    The IMPLEMENTATION_PLAN documents imports as ``engine.*``.
    The actual working path is ``src.engine.*`` because the editable install
    (pip install -e ../probabilistic_ontology_engine) adds the repo root to
    sys.path rather than src/.  The API is otherwise identical.
    See SNAPSHOT.md for the documented divergence.

Dependency boundary — POE-A imports only:
    src.engine.engine        — ProbabilisticOntologyEngine
    src.engine.schemas       — Variable, OntologyCandidate, EvidenceRecord,
                               ObservedAssignment, DependencyEdge, DomainType,
                               MissingnessType, SourceType, EdgeExistenceThresholdConfig
    src.engine.variable_identity — stable_variable_id

No POE domain internals, no POE art-domain code, no copied POE source.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import UUID

logger = logging.getLogger(__name__)

_DOMAIN_ID_DEFAULT = "poea-induced-v1"


# ---------------------------------------------------------------------------
# Lazy POE import — surfaces missing-dependency errors clearly
# ---------------------------------------------------------------------------

def _import_poe() -> tuple:
    """
    Import all required POE symbols, raising a clear error if POE is absent.

    Returns a tuple of (Engine, Variable, DependencyEdge, OntologyCandidate,
    EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType,
    EdgeExistenceThresholdConfig, stable_variable_id).
    """
    try:
        from src.engine.engine import ProbabilisticOntologyEngine
        from src.engine.schemas import (
            DependencyEdge,
            DomainType,
            EdgeExistenceThresholdConfig,
            EvidenceRecord,
            MissingnessType,
            ObservedAssignment,
            OntologyCandidate,
            SourceType,
            Variable,
        )
        from src.engine.variable_identity import stable_variable_id

        return (
            ProbabilisticOntologyEngine,
            Variable,
            DependencyEdge,
            OntologyCandidate,
            EvidenceRecord,
            ObservedAssignment,
            DomainType,
            MissingnessType,
            SourceType,
            EdgeExistenceThresholdConfig,
            stable_variable_id,
        )
    except ImportError as exc:
        raise ImportError(
            "POE is not installed. Run:\n"
            "  pip install -e ../probabilistic_ontology_engine\n"
            f"Original error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Dynamic domain module
# ---------------------------------------------------------------------------

class InducedDomainModule:
    """
    Minimal POE domain module wrapping abductively-induced variables and candidates.

    POE's engine duck-types domain modules; this class implements the required
    interface with no art-domain-specific logic.
    """

    def __init__(
        self,
        module_id: str,
        candidates: list,
        thresholds: Any,
    ) -> None:
        self._module_id = module_id
        self._candidates = candidates
        self._thresholds = thresholds

    def module_id(self) -> str:
        return self._module_id

    def version(self) -> str:
        return "1.0.0"

    def initial_candidates(self) -> list:
        return self._candidates

    def existence_thresholds(self) -> Any:
        return self._thresholds

    # Optional domain module methods — return empty for induced vocabulary
    def initial_entities(self) -> list:
        return []

    def initial_assertions(self) -> list:
        return []

    def variable_specs(self) -> list:
        return []

    def initial_parameterizations(self) -> list:
        return []


# ---------------------------------------------------------------------------
# POEBackend
# ---------------------------------------------------------------------------

class POEBackend:
    """
    Structure-learning backend delegating to the Probabilistic Ontology Engine.

    Implements the StructureLearningBackend protocol.

    learn_graph steps:
        1. Build Variable objects using stable_variable_id (deterministic UUIDs).
        2. Build a seed OntologyCandidate with co-occurrence-seeded edges.
        3. Wrap variables + candidate in an InducedDomainModule.
        4. Register the module with POE and activate it.
        5. Translate POE-A scored evidence → POE EvidenceRecord objects.
        6. Call engine.learn() to run one learning cycle.
        7. Extract the dominant candidate and build the graph artifact.
    """

    BACKEND_NAME = "poe"

    def __init__(
        self,
        domain_id: str = _DOMAIN_ID_DEFAULT,
        db_path: str = ":memory:",
        random_seed: int = 42,
    ) -> None:
        self._domain_id = domain_id
        self._db_path = db_path
        self._random_seed = random_seed

    def learn_graph(
        self,
        concepts: Sequence[Mapping[str, Any]],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        (
            ProbabilisticOntologyEngine,
            Variable,
            DependencyEdge,
            OntologyCandidate,
            EvidenceRecord,
            ObservedAssignment,
            DomainType,
            MissingnessType,
            SourceType,
            EdgeExistenceThresholdConfig,
            stable_variable_id,
        ) = _import_poe()

        concept_list = list(concepts)
        evidence_list = list(scored_evidence)

        # 1. Build Variables with stable, deterministic UUIDs
        variables = _build_variables(
            concept_list, self._domain_id,
            Variable, DomainType, stable_variable_id,
        )
        var_by_name: dict[str, Any] = {v.name: v for v in variables}

        # 2. Seed candidate — co-occurrence edges, canonical direction (DAG-safe)
        edges = _build_cooccurrence_edges(variables, evidence_list, DependencyEdge)
        thresholds = EdgeExistenceThresholdConfig(
            prune_below=0.05,
            accept_above=0.90,
            explore_band=(0.3, 0.7),
        )
        seed_candidate = OntologyCandidate(
            domain_module_id=self._domain_id,
            variables=variables,
            edges=edges,
            description="poea-abductive-seed",
        )

        # 3 & 4. Register domain and initialise engine
        domain = InducedDomainModule(
            module_id=self._domain_id,
            candidates=[seed_candidate],
            thresholds=thresholds,
        )
        engine = ProbabilisticOntologyEngine(
            db_path=self._db_path,
            random_seed=self._random_seed,
        )
        engine.register_domain(domain)
        engine.activate_domain(self._domain_id)

        # 5. Translate scored evidence
        records = _translate_scored_evidence(
            evidence_list,
            var_by_name,
            EvidenceRecord,
            ObservedAssignment,
            MissingnessType,
            SourceType,
        )

        # 6. Learn
        snapshot = None
        if records:
            snapshot = engine.learn(
                batch=records,
                domain_module_id=self._domain_id,
            )
            logger.info(
                "POE learn() complete — %d record(s), domain '%s'",
                len(records),
                self._domain_id,
            )
        else:
            logger.warning(
                "No scoreable evidence for domain '%s'; returning seed graph",
                self._domain_id,
            )

        # 7. Extract graph artifact
        population = engine.get_population(self._domain_id)
        return _build_graph_artifact(
            population=population,
            fallback_variables=variables,
            domain_id=self._domain_id,
            evidence_count=len(records),
            snapshot=snapshot,
        )

    def score_hypotheses(
        self,
        graph: Mapping[str, Any],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """
        Return candidate hypothesis scores from the graph artifact.

        For Phase 9, hypothesis scoring reads from the pre-computed candidate
        summaries embedded in the graph artifact by learn_graph.
        """
        return {
            "backend": self.BACKEND_NAME,
            "hypothesis_count": len(graph.get("candidate_summaries", [])),
            "hypotheses": graph.get("candidate_summaries", []),
            "population": graph.get("population", {}),
        }


# ---------------------------------------------------------------------------
# Helper functions (module-level; also exported for unit testing)
# ---------------------------------------------------------------------------

def _build_variables(
    concepts: list[Mapping[str, Any]],
    domain_id: str,
    Variable: Any,
    DomainType: Any,
    stable_variable_id: Any,
) -> list:
    """Build POE Variable objects with stable UUIDs from concept dicts."""
    variables = []
    for c in concepts:
        vid = stable_variable_id(domain_id, c["name"])
        var = Variable(
            variable_id=vid,
            name=c["name"],
            domain_type=DomainType.BOOLEAN,
            support=[True, False],
        )
        variables.append(var)
    return variables


def _build_cooccurrence_edges(
    variables: list,
    scored_evidence: list[Mapping[str, Any]],
    DependencyEdge: Any,
) -> list:
    """
    Build a co-occurrence-seeded edge list for the seed OntologyCandidate.

    For each evidence record, pairs of concepts with non-MISSING assignments
    are treated as co-occurring.  One directed edge is added per pair,
    directed from the lower-index variable to the higher-index variable
    (canonical ordering preserves DAG validity).

    Without scored evidence, returns an empty list (fully disconnected seed).
    """
    if not variables:
        return []

    idx_by_name: dict[str, int] = {v.name: i for i, v in enumerate(variables)}
    cooccurred: set[tuple[int, int]] = set()

    for record in scored_evidence:
        present: list[int] = []
        for a in record.get("assignments", []):
            if a.get("missingness") == "MISSING":
                continue
            idx = idx_by_name.get(a.get("variable_name", ""))
            if idx is not None:
                present.append(idx)

        for k in range(len(present)):
            for j in range(k + 1, len(present)):
                lo, hi = sorted((present[k], present[j]))
                cooccurred.add((lo, hi))

    return [
        DependencyEdge(
            parent_variable_id=variables[lo].variable_id,
            child_variable_id=variables[hi].variable_id,
        )
        for lo, hi in sorted(cooccurred)
    ]


def _translate_scored_evidence(
    scored_evidence: list[Mapping[str, Any]],
    var_by_name: dict[str, Any],
    EvidenceRecord: Any,
    ObservedAssignment: Any,
    MissingnessType: Any,
    SourceType: Any,
) -> list:
    """
    Translate POE-A ScoredRecord dicts into POE EvidenceRecord objects.

    Missingness mapping:
        OBSERVED      → ObservedAssignment (hard observation)
        SOFT_OBSERVED → ObservedAssignment with probabilities dict
        MISSING       → omitted (no assignment for this variable)

    Records with zero observable assignments are skipped entirely.
    """
    records = []
    for rec in scored_evidence:
        assignments = []
        for a in rec.get("assignments", []):
            name = a.get("variable_name", "")
            var = var_by_name.get(name)
            if var is None:
                continue

            missingness_str = a.get("missingness", "OBSERVED")
            assigned_value = a.get("assigned_value")
            confidence = float(a.get("confidence", 1.0))

            if missingness_str == "MISSING" or assigned_value is None:
                continue

            if missingness_str == "SOFT_OBSERVED":
                # Probabilistic observation: confidence = P(verdict is correct)
                if assigned_value:
                    probs = {True: confidence, False: round(1.0 - confidence, 10)}
                else:
                    probs = {False: confidence, True: round(1.0 - confidence, 10)}
                oa = ObservedAssignment(
                    variable_id=var.variable_id,
                    observed_value=assigned_value,
                    missingness=MissingnessType.SOFT_OBSERVED,
                    confidence=confidence,
                    probabilities=probs,
                )
            else:
                oa = ObservedAssignment(
                    variable_id=var.variable_id,
                    observed_value=assigned_value,
                    missingness=MissingnessType.OBSERVED,
                    confidence=confidence,
                )
            assignments.append(oa)

        if not assignments:
            continue

        records.append(
            EvidenceRecord(
                observed_assignments=assignments,
                source_type=SourceType.FILE,
                source_ref=rec.get("evidence_id", ""),
            )
        )
    return records


def _build_graph_artifact(
    population: Any,
    fallback_variables: list,
    domain_id: str,
    evidence_count: int,
    snapshot: Any,
) -> dict[str, Any]:
    """
    Extract a POE-A graph artifact from a POE OntologyPopulation.

    Uses the dominant candidate (highest log_score among ACTIVE candidates).
    Falls back to an edgeless graph using fallback_variables if no active
    candidates exist.
    """
    now = datetime.now(timezone.utc).isoformat()
    candidates = getattr(population, "candidates", [])
    active = [c for c in candidates if str(getattr(c.status, "value", c.status)) == "ACTIVE"]

    if active:
        dominant = max(active, key=lambda c: c.log_score)
        active_edges = [e for e in dominant.edges if e.enabled]
        name_by_id: dict[UUID, str] = {v.variable_id: v.name for v in dominant.variables}

        nodes_out = [
            {
                "concept_id": str(v.variable_id),
                "name": v.name,
                "prior_probability": 0.5,
                "boolean_state": None,
                "source": "poea_induced",
            }
            for v in dominant.variables
        ]
        edges_out = [
            {
                "parent": name_by_id.get(e.parent_variable_id, str(e.parent_variable_id)),
                "child": name_by_id.get(e.child_variable_id, str(e.child_variable_id)),
                "existence_probability": e.existence_probability,
            }
            for e in active_edges
        ]
    else:
        nodes_out = [
            {
                "concept_id": str(v.variable_id),
                "name": v.name,
                "prior_probability": 0.5,
                "boolean_state": None,
                "source": "poea_induced",
            }
            for v in fallback_variables
        ]
        edges_out = []

    candidate_summaries = [
        {
            "candidate_id": str(c.candidate_id),
            "log_score": c.log_score,
            "evidence_count": c.evidence_count,
            "active_edge_count": sum(1 for e in c.edges if e.enabled),
            "status": str(getattr(c.status, "value", c.status)),
        }
        for c in candidates
    ]

    return {
        "backend": "poe",
        "domain_id": domain_id,
        "node_count": len(nodes_out),
        "edge_count": len(edges_out),
        "nodes": nodes_out,
        "edges": edges_out,
        "candidate_summaries": candidate_summaries,
        "population": {
            "candidate_count": len(candidates),
            "active_count": len(active),
            "dominant_log_score": max((c.log_score for c in active), default=0.0),
        },
        "metadata": {
            "created_at": now,
            "evidence_count": evidence_count,
            "snapshot_id": str(snapshot.snapshot_id) if snapshot else None,
        },
    }
