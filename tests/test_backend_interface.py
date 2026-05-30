"""Tests for the backend interface and NullBackend (Phase 7)."""
from __future__ import annotations

import pytest

from poea.backends import get_backend
from poea.backends.interface import StructureLearningBackend
from poea.backends.null_backend import NullBackend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_concept(name: str, concept_id: str = "") -> dict:
    return {
        "concept_id": concept_id or f"id_{name.lower()}",
        "name": name,
        "definition": f"{name} definition.",
        "confidence": 0.85,
        "status": "active",
    }


def _make_scored_record(evidence_id: str, concept_names: list[str]) -> dict:
    return {
        "evidence_id": evidence_id,
        "assignments": [
            {
                "concept_id": f"id_{n.lower()}",
                "variable_name": n,
                "assigned_value": True,
                "confidence": 0.80,
                "missingness": "OBSERVED",
            }
            for n in concept_names
        ],
    }


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_null_backend_satisfies_protocol():
    """NullBackend must be recognised as a StructureLearningBackend."""
    assert isinstance(NullBackend(), StructureLearningBackend)


def test_null_backend_has_learn_graph():
    assert hasattr(NullBackend(), "learn_graph")
    assert callable(NullBackend().learn_graph)


def test_null_backend_has_score_hypotheses():
    assert hasattr(NullBackend(), "score_hypotheses")
    assert callable(NullBackend().score_hypotheses)


# ---------------------------------------------------------------------------
# NullBackend.learn_graph
# ---------------------------------------------------------------------------

def test_learn_graph_one_node_per_concept():
    concepts = [_make_concept("Alpha"), _make_concept("Beta"), _make_concept("Gamma")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    assert graph["node_count"] == 3
    assert len(graph["nodes"]) == 3


def test_learn_graph_no_edges():
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    assert graph["edges"] == []
    assert graph["edge_count"] == 0


def test_learn_graph_preserves_concept_names():
    concepts = [_make_concept("AuctionCatalystEffect"), _make_concept("TrophyBuyerDemand")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    names = {n["name"] for n in graph["nodes"]}
    assert "AuctionCatalystEffect" in names
    assert "TrophyBuyerDemand" in names


def test_learn_graph_preserves_concept_ids():
    concepts = [_make_concept("Alpha", concept_id="abc123")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    assert graph["nodes"][0]["concept_id"] == "abc123"


def test_learn_graph_node_has_default_priors():
    concepts = [_make_concept("Alpha")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    node = graph["nodes"][0]
    assert node["prior_probability"] == 0.5
    assert node["boolean_state"] is None
    assert node["source"] == "poea_induced"


def test_learn_graph_with_empty_concepts():
    backend = NullBackend()
    graph = backend.learn_graph([], [])
    assert graph["nodes"] == []
    assert graph["node_count"] == 0
    assert graph["edge_count"] == 0


def test_learn_graph_with_empty_scored_evidence():
    """NullBackend must work when scored_evidence is empty."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    assert len(graph["nodes"]) == 2


def test_learn_graph_with_scored_evidence():
    """NullBackend accepts scored evidence without error (ignores it for edges)."""
    concepts = [_make_concept("Alpha"), _make_concept("Beta")]
    scored = [_make_scored_record("ev001", ["Alpha", "Beta"])]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, scored)
    assert len(graph["nodes"]) == 2
    assert graph["edges"] == []


def test_learn_graph_metadata_has_evidence_count():
    concepts = [_make_concept("Alpha")]
    scored = [_make_scored_record("ev001", ["Alpha"]), _make_scored_record("ev002", ["Alpha"])]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, scored)
    assert graph["metadata"]["evidence_count"] == 2


def test_learn_graph_returns_backend_name():
    backend = NullBackend()
    graph = backend.learn_graph([], [])
    assert graph["backend"] == "null"


def test_learn_graph_with_config():
    """Passing config must not cause errors (NullBackend ignores it)."""
    concepts = [_make_concept("Alpha")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [], config={"some_param": 42})
    assert len(graph["nodes"]) == 1


# ---------------------------------------------------------------------------
# NullBackend.score_hypotheses
# ---------------------------------------------------------------------------

def test_score_hypotheses_returns_empty_list():
    backend = NullBackend()
    graph = backend.learn_graph([_make_concept("Alpha")], [])
    result = backend.score_hypotheses(graph, [])
    assert result["hypotheses"] == []
    assert result["hypothesis_count"] == 0


def test_score_hypotheses_returns_backend_name():
    backend = NullBackend()
    result = backend.score_hypotheses({}, [])
    assert result["backend"] == "null"


def test_score_hypotheses_includes_explanatory_note():
    backend = NullBackend()
    result = backend.score_hypotheses({}, [])
    assert "note" in result
    assert len(result["note"]) > 0


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

def test_get_backend_null_returns_null_backend():
    backend = get_backend("null")
    assert isinstance(backend, NullBackend)


def test_get_backend_null_satisfies_protocol():
    backend = get_backend("null")
    assert isinstance(backend, StructureLearningBackend)


def test_get_backend_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("not_a_real_backend")


def test_get_backend_unknown_error_mentions_available():
    with pytest.raises(ValueError, match="null"):
        get_backend("bogus")


def test_get_backend_poe_not_yet_available():
    """POE backend is Phase 9 — must not be available in Phase 7."""
    with pytest.raises(ValueError):
        get_backend("poe")


# ---------------------------------------------------------------------------
# Graph structure contract
# ---------------------------------------------------------------------------

def test_graph_has_required_keys():
    """The graph artifact must contain the documented required keys."""
    concepts = [_make_concept("Alpha")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    for key in ("backend", "nodes", "edges", "node_count", "edge_count"):
        assert key in graph, f"Missing required key: {key!r}"


def test_node_has_required_keys():
    concepts = [_make_concept("Alpha")]
    backend = NullBackend()
    graph = backend.learn_graph(concepts, [])
    node = graph["nodes"][0]
    for key in ("concept_id", "name", "definition", "prior_probability", "boolean_state", "source"):
        assert key in node, f"Node missing required key: {key!r}"
