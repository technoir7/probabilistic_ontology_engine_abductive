"""
Tests for the POE Adapter (Phase 9).

All tests use in-memory POE (db_path=':memory:') and synthetic scored evidence.
No live LLM calls; no file I/O beyond what POE needs internally.
"""
from __future__ import annotations

import pytest

from poea.backends import get_backend
from poea.backends.interface import StructureLearningBackend
from poea.backends.poe_backend import (
    InducedDomainModule,
    POEBackend,
    _build_cooccurrence_edges,
    _build_variables,
    _import_poe,
    _translate_scored_evidence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_concept(name: str) -> dict:
    return {
        "concept_id": f"id_{name.lower()}",
        "name": name,
        "definition": f"{name} definition.",
        "confidence": 0.85,
        "status": "active",
    }


def _make_assignment(name: str, value: bool, missingness: str = "OBSERVED", confidence: float = 0.85) -> dict:
    return {
        "concept_id": f"id_{name.lower()}",
        "variable_name": name,
        "assigned_value": value,
        "confidence": confidence,
        "missingness": missingness,
    }


def _make_scored_record(evidence_id: str, assignments: list[dict]) -> dict:
    return {"evidence_id": evidence_id, "assignments": assignments}


# ---------------------------------------------------------------------------
# POE import check
# ---------------------------------------------------------------------------

def test_poe_imports_succeed():
    """All required POE symbols can be imported."""
    result = _import_poe()
    assert len(result) == 11  # 11-tuple of imported symbols


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_poe_backend_satisfies_protocol():
    assert isinstance(POEBackend(), StructureLearningBackend)


def test_poe_backend_has_learn_graph():
    assert callable(POEBackend().learn_graph)


def test_poe_backend_has_score_hypotheses():
    assert callable(POEBackend().score_hypotheses)


# ---------------------------------------------------------------------------
# _build_variables
# ---------------------------------------------------------------------------

def test_build_variables_count():
    (_, Variable, _, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    variables = _build_variables(concepts, "test-domain", Variable, DomainType, stable_variable_id)
    assert len(variables) == 2


def test_build_variables_names_preserved():
    (_, Variable, _, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("MyConceptX")]
    variables = _build_variables(concepts, "test-domain", Variable, DomainType, stable_variable_id)
    assert variables[0].name == "MyConceptX"


def test_build_variables_boolean_domain():
    (_, Variable, _, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    variables = _build_variables(concepts, "test-domain", Variable, DomainType, stable_variable_id)
    assert str(variables[0].domain_type.value) == "BOOLEAN"
    assert variables[0].support == [True, False]


def test_build_variables_stable_uuid():
    """Same inputs always produce the same variable_id."""
    (_, Variable, _, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    v1 = _build_variables(concepts, "domain-A", Variable, DomainType, stable_variable_id)
    v2 = _build_variables(concepts, "domain-A", Variable, DomainType, stable_variable_id)
    assert v1[0].variable_id == v2[0].variable_id


def test_build_variables_different_domain_different_uuid():
    """Different domain_ids must produce different variable UUIDs."""
    (_, Variable, _, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    v1 = _build_variables(concepts, "domain-A", Variable, DomainType, stable_variable_id)
    v2 = _build_variables(concepts, "domain-B", Variable, DomainType, stable_variable_id)
    assert v1[0].variable_id != v2[0].variable_id


# ---------------------------------------------------------------------------
# _build_cooccurrence_edges
# ---------------------------------------------------------------------------

def test_cooccurrence_no_evidence_produces_no_edges():
    (_, Variable, DependencyEdge, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    edges = _build_cooccurrence_edges(variables, [], DependencyEdge)
    assert edges == []


def test_cooccurrence_single_record_two_concepts():
    (_, Variable, DependencyEdge, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", True, "OBSERVED"),
            _make_assignment("Beta", True, "OBSERVED"),
        ])
    ]
    edges = _build_cooccurrence_edges(variables, scored, DependencyEdge)
    assert len(edges) == 1


def test_cooccurrence_missing_assignments_excluded():
    (_, Variable, DependencyEdge, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", True, "OBSERVED"),
            _make_assignment("Beta", None, "MISSING"),
        ])
    ]
    edges = _build_cooccurrence_edges(variables, scored, DependencyEdge)
    assert edges == []  # Only one non-MISSING concept; no pair


def test_cooccurrence_edges_form_valid_dag():
    """Co-occurrence edge seeding must always produce a valid DAG."""
    (_, Variable, DependencyEdge, OntologyCandidate, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept(f"C{i}") for i in range(4)]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    scored = [
        _make_scored_record("ev001", [
            _make_assignment(f"C{i}", True, "OBSERVED") for i in range(4)
        ])
    ]
    edges = _build_cooccurrence_edges(variables, scored, DependencyEdge)
    cand = OntologyCandidate(domain_module_id="test", variables=variables, edges=edges)
    assert cand.is_dag()


def test_cooccurrence_deduplicates_pairs():
    """Same pair appearing in multiple records produces one edge."""
    (_, Variable, DependencyEdge, _, _, _, DomainType, _, _, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", True), _make_assignment("Beta", True)
        ]),
        _make_scored_record("ev002", [
            _make_assignment("Alpha", False), _make_assignment("Beta", False)
        ]),
    ]
    edges = _build_cooccurrence_edges(variables, scored, DependencyEdge)
    assert len(edges) == 1  # Same pair, deduplicated


# ---------------------------------------------------------------------------
# _translate_scored_evidence
# ---------------------------------------------------------------------------

def test_translate_observed_assignment():
    (_, Variable, _, _, EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    var_by_name = {v.name: v for v in variables}

    scored = [
        _make_scored_record("ev001", [_make_assignment("Alpha", True, "OBSERVED", 0.85)])
    ]
    records = _translate_scored_evidence(
        scored, var_by_name, EvidenceRecord, ObservedAssignment, MissingnessType, SourceType
    )
    assert len(records) == 1
    assert len(records[0].observed_assignments) == 1
    a = records[0].observed_assignments[0]
    assert a.observed_value is True
    assert str(a.missingness.value) == "OBSERVED"
    assert a.probabilities is None


def test_translate_soft_observed_assignment():
    (_, Variable, _, _, EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    var_by_name = {v.name: v for v in variables}

    scored = [
        _make_scored_record("ev001", [_make_assignment("Alpha", True, "SOFT_OBSERVED", 0.40)])
    ]
    records = _translate_scored_evidence(
        scored, var_by_name, EvidenceRecord, ObservedAssignment, MissingnessType, SourceType
    )
    assert len(records) == 1
    a = records[0].observed_assignments[0]
    assert str(a.missingness.value) == "SOFT_OBSERVED"
    assert a.probabilities is not None
    assert abs(sum(a.probabilities.values()) - 1.0) < 0.01


def test_translate_missing_assignment_excluded():
    (_, Variable, _, _, EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    var_by_name = {v.name: v for v in variables}

    scored = [
        _make_scored_record("ev001", [_make_assignment("Alpha", None, "MISSING", 0.0)])
    ]
    records = _translate_scored_evidence(
        scored, var_by_name, EvidenceRecord, ObservedAssignment, MissingnessType, SourceType
    )
    assert records == []  # All-MISSING record is skipped


def test_translate_all_missing_record_skipped():
    (_, Variable, _, _, EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    var_by_name = {v.name: v for v in variables}

    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", None, "MISSING"),
            _make_assignment("Beta", None, "MISSING"),
        ])
    ]
    records = _translate_scored_evidence(
        scored, var_by_name, EvidenceRecord, ObservedAssignment, MissingnessType, SourceType
    )
    assert records == []


def test_translate_unknown_concept_skipped():
    """Assignments for concepts not in var_by_name are silently skipped."""
    (_, Variable, _, _, EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    var_by_name = {v.name: v for v in variables}

    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", True, "OBSERVED"),
            _make_assignment("NotInRegistry", True, "OBSERVED"),
        ])
    ]
    records = _translate_scored_evidence(
        scored, var_by_name, EvidenceRecord, ObservedAssignment, MissingnessType, SourceType
    )
    assert len(records) == 1
    assert len(records[0].observed_assignments) == 1


def test_translate_source_type_is_file():
    (_, Variable, _, _, EvidenceRecord, ObservedAssignment, DomainType, MissingnessType, SourceType, _, stable_variable_id) = _import_poe()
    concepts = [_make_concept("Alpha")]
    variables = _build_variables(concepts, "test", Variable, DomainType, stable_variable_id)
    var_by_name = {v.name: v for v in variables}

    scored = [_make_scored_record("ev001", [_make_assignment("Alpha", True)])]
    records = _translate_scored_evidence(
        scored, var_by_name, EvidenceRecord, ObservedAssignment, MissingnessType, SourceType
    )
    assert str(records[0].source_type.value) == "FILE"


# ---------------------------------------------------------------------------
# InducedDomainModule
# ---------------------------------------------------------------------------

def test_induced_domain_module_returns_module_id():
    (_, _, _, _, _, _, _, _, _, EdgeExistenceThresholdConfig, _) = _import_poe()
    domain = InducedDomainModule("my-domain", [], EdgeExistenceThresholdConfig())
    assert domain.module_id() == "my-domain"


def test_induced_domain_module_returns_candidates():
    (_, _, _, _, _, _, _, _, _, EdgeExistenceThresholdConfig, _) = _import_poe()
    sentinel = object()
    domain = InducedDomainModule("test", [sentinel], EdgeExistenceThresholdConfig())
    assert domain.initial_candidates() == [sentinel]


def test_induced_domain_module_optional_methods_return_empty():
    (_, _, _, _, _, _, _, _, _, EdgeExistenceThresholdConfig, _) = _import_poe()
    domain = InducedDomainModule("test", [], EdgeExistenceThresholdConfig())
    assert domain.initial_entities() == []
    assert domain.initial_assertions() == []
    assert domain.variable_specs() == []
    assert domain.initial_parameterizations() == []


# ---------------------------------------------------------------------------
# POEBackend integration — in-memory POE
# ---------------------------------------------------------------------------

def test_poe_backend_learn_graph_with_concepts_no_evidence():
    """Backend runs without error when no scored evidence is available."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, [])
    assert graph["backend"] == "poe"
    assert graph["node_count"] == 2
    assert "nodes" in graph
    assert "edges" in graph


def test_poe_backend_learn_graph_with_evidence():
    """Backend runs end-to-end with synthetic scored evidence."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta"), _make_concept("Gamma")]
    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", True, "OBSERVED", 0.90),
            _make_assignment("Beta", True, "OBSERVED", 0.85),
            _make_assignment("Gamma", False, "OBSERVED", 0.80),
        ]),
        _make_scored_record("ev002", [
            _make_assignment("Alpha", True, "OBSERVED", 0.85),
            _make_assignment("Beta", False, "OBSERVED", 0.75),
            _make_assignment("Gamma", None, "MISSING", 0.0),
        ]),
    ]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, scored)

    assert graph["backend"] == "poe"
    assert graph["node_count"] == 3
    assert isinstance(graph["edges"], list)
    assert isinstance(graph["nodes"], list)


def test_poe_backend_graph_has_required_keys():
    concepts = [_make_concept("Alpha")]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, [])
    for key in ("backend", "domain_id", "node_count", "edge_count", "nodes", "edges",
                "candidate_summaries", "population", "metadata"):
        assert key in graph, f"Missing key: {key!r}"


def test_poe_backend_nodes_have_required_fields():
    concepts = [_make_concept("Alpha")]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, [])
    node = graph["nodes"][0]
    for field in ("concept_id", "name", "prior_probability", "boolean_state", "source"):
        assert field in node, f"Node missing: {field!r}"
    assert node["prior_probability"] == 0.5
    assert node["boolean_state"] is None
    assert node["source"] == "poea_induced"


def test_poe_backend_population_info_present():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, [])
    pop = graph["population"]
    assert "candidate_count" in pop
    assert "active_count" in pop
    assert pop["candidate_count"] >= 1


def test_poe_backend_soft_observed_evidence():
    """SOFT_OBSERVED assignments are accepted without validation errors."""
    concepts = [_make_concept("Alpha")]
    scored = [
        _make_scored_record("ev001", [
            _make_assignment("Alpha", True, "SOFT_OBSERVED", 0.40)
        ])
    ]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, scored)
    assert graph["node_count"] == 1


def test_poe_backend_domain_id_used_in_output():
    concepts = [_make_concept("Alpha")]
    backend = POEBackend(domain_id="custom-domain-123", db_path=":memory:")
    graph = backend.learn_graph(concepts, [])
    assert graph["domain_id"] == "custom-domain-123"


def test_poe_backend_score_hypotheses():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    backend = POEBackend(db_path=":memory:", random_seed=42)
    graph = backend.learn_graph(concepts, [])
    result = backend.score_hypotheses(graph, [])
    assert result["backend"] == "poe"
    assert "hypotheses" in result
    assert "population" in result


# ---------------------------------------------------------------------------
# Factory registration
# ---------------------------------------------------------------------------

def test_get_backend_poe_returns_poe_backend():
    backend = get_backend("poe")
    assert isinstance(backend, POEBackend)


def test_get_backend_poe_satisfies_protocol():
    backend = get_backend("poe")
    assert isinstance(backend, StructureLearningBackend)


def test_get_backend_poe_kwargs_forwarded():
    backend = get_backend("poe", domain_id="custom-id", db_path=":memory:")
    assert isinstance(backend, POEBackend)
    assert backend._domain_id == "custom-id"


def test_get_backend_unknown_still_raises():
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("nonexistent_backend_xyz")
