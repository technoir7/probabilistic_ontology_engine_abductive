from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from poea.artifacts.reports import (
    _append_entropy_diagnostics,
    _append_posterior_inference,
    _append_structure_diagnostics,
    _append_variable_uncertainty,
    write_run_report,
)
from poea.cli import app


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_complete_artifacts(output_dir: Path) -> None:
    _write_json(
        output_dir / "evidence.json",
        [
            {
                "evidence_id": "ev001",
                "source": "fixture",
                "title": "First record",
                "domain_tag": "test",
                "text": "Alpha evidence.",
            },
            {
                "evidence_id": "ev002",
                "source": "fixture",
                "title": "Second record",
                "domain_tag": "test",
                "text": "Beta evidence.",
            },
        ],
    )
    _write_json(
        output_dir / "raw_concepts.json",
        {
            "model": "test-induction-model",
            "evidence_count": 2,
            "batch_count": 1,
            "concept_count": 4,
            "errors": [],
            "concepts": [],
        },
    )
    entries = [
        {
            "concept_id": "alpha",
            "name": "Alpha",
            "definition": "Alpha definition.",
            "confidence": 0.9,
            "supporting_evidence_ids": ["ev001"],
            "occurrence_count": 1,
            "status": "active",
            "merged_into": None,
            "source_concept_ids": [],
        },
        {
            "concept_id": "beta",
            "name": "Beta",
            "definition": "Beta definition.",
            "confidence": 0.8,
            "supporting_evidence_ids": ["ev002"],
            "occurrence_count": 1,
            "status": "active",
            "merged_into": None,
            "source_concept_ids": [],
        },
        {
            "concept_id": "gamma",
            "name": "Gamma",
            "definition": "Gamma definition.",
            "confidence": 0.6,
            "supporting_evidence_ids": [],
            "occurrence_count": 1,
            "status": "suppressed",
            "merged_into": None,
            "source_concept_ids": [],
        },
        {
            "concept_id": "delta",
            "name": "Delta",
            "definition": "Delta definition.",
            "confidence": 0.7,
            "supporting_evidence_ids": [],
            "occurrence_count": 1,
            "status": "merged_into",
            "merged_into": "alpha",
            "source_concept_ids": [],
        },
    ]
    _write_json(
        output_dir / "concept_registry.json",
        {
            "metadata": {"created_at": "2026-05-30T00:00:00+00:00"},
            "metrics": {
                "raw_proposal_count": 4,
                "exact_duplicates_merged": 0,
                "semantic_concepts_merged": 1,
                "rejected": 0,
                "suppressed_by_confidence": 1,
                "suppressed_by_evidence": 0,
                "suppressed_by_cap": 0,
                "active_canonical_count": 2,
            },
            "promotion_events": [],
            "entries": entries,
        },
    )
    _write_json(
        output_dir / "canonical_concepts.json",
        {
            "metadata": {"created_at": "2026-05-30T00:00:00+00:00"},
            "concepts": entries[:2],
        },
    )
    _write_json(
        output_dir / "scored_evidence.json",
        {
            "metadata": {
                "model": "test-scoring-model",
                "scored_at": "2026-05-30T00:01:00+00:00",
                "soft_observed_threshold": 0.5,
            },
            "summary": {
                "total_records": 2,
                "scored": 2,
                "cache_hits": 0,
                "errors": 0,
                "total_pairs": 4,
                "by_concept": {
                    "Alpha": {"true": 1, "false": 0, "neutral": 1},
                    "Beta": {"true": 0, "false": 1, "neutral": 1},
                },
            },
            "scored_records": [
                {
                    "evidence_id": "ev001",
                    "assignments": [
                        {
                            "concept_id": "alpha",
                            "variable_name": "Alpha",
                            "assigned_value": True,
                            "confidence": 0.9,
                            "missingness": "OBSERVED",
                        },
                        {
                            "concept_id": "beta",
                            "variable_name": "Beta",
                            "assigned_value": None,
                            "confidence": 0.1,
                            "missingness": "MISSING",
                        },
                    ],
                    "error": None,
                },
                {
                    "evidence_id": "ev002",
                    "assignments": [
                        {
                            "concept_id": "alpha",
                            "variable_name": "Alpha",
                            "assigned_value": None,
                            "confidence": 0.2,
                            "missingness": "MISSING",
                        },
                        {
                            "concept_id": "beta",
                            "variable_name": "Beta",
                            "assigned_value": False,
                            "confidence": 0.4,
                            "missingness": "SOFT_OBSERVED",
                        },
                    ],
                    "error": None,
                },
            ],
        },
    )
    _write_json(
        output_dir / "nodes.json",
        {
            "domain_tag": "test",
            "node_count": 2,
            "metadata": {"created_at": "2026-05-30T00:02:00+00:00"},
            "nodes": [],
        },
    )
    _write_json(
        output_dir / "poea_graph.json",
        {
            "backend": "poe",
            "domain_id": "fixture-domain",
            "node_count": 2,
            "edge_count": 1,
            "nodes": [],
            "edges": [{"parent": "Alpha", "child": "Beta", "existence_probability": 0.75}],
            "candidate_summaries": [
                {
                    "candidate_id": "candidate-1",
                    "status": "ACTIVE",
                    "log_score": -1.25,
                    "evidence_count": 2,
                    "active_edge_count": 1,
                }
            ],
            "population": {"candidate_count": 1, "active_count": 1, "dominant_log_score": -1.25},
            "metadata": {"created_at": "2026-05-30T00:03:00+00:00", "evidence_count": 2},
        },
    )


def test_report_generation_from_complete_artifacts(tmp_path):
    output_dir = tmp_path / "artifacts"
    _write_complete_artifacts(output_dir)
    report_path = output_dir / "run_report.md"

    result = CliRunner().invoke(
        app,
        ["report", "--run", "latest", "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0, result.output
    second_result = CliRunner().invoke(
        app,
        ["report", "--run", "latest", "--output-dir", str(output_dir)],
    )
    assert second_result.exit_code == 0, second_result.output
    report = report_path.read_text()
    assert "Evidence records loaded: 2" in report
    assert "Active concepts selected: 2" in report
    assert "Records included in POE learning: 2" in report
    assert "| Alpha | Beta | 0.75 |" in report
    assert "| candidate-1 | ACTIVE | -1.25 | 2 | 1 |" in report


def test_report_generation_when_optional_artifacts_are_missing(tmp_path):
    output_dir = tmp_path / "artifacts"
    _write_json(output_dir / "evidence.json", [])

    result = CliRunner().invoke(
        app,
        ["report", "--run", "latest", "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0, result.output
    report = (output_dir / "run_report.md").read_text()
    assert "Evidence scoring artifact not present." in report
    assert "Missing artifact: scored_evidence" in report
    assert "Missing artifact: graph" in report


def test_report_neutral_rate_calculation(tmp_path):
    output_dir = tmp_path / "artifacts"
    _write_complete_artifacts(output_dir)

    write_run_report(
        output_dir / "run_report.md",
        domain="test",
        backend="poe",
        artifacts={
            "evidence": str(output_dir / "evidence.json"),
            "raw_concepts": str(output_dir / "raw_concepts.json"),
            "registry": str(output_dir / "concept_registry.json"),
            "canonical_concepts": str(output_dir / "canonical_concepts.json"),
            "scored_evidence": str(output_dir / "scored_evidence.json"),
            "nodes": str(output_dir / "nodes.json"),
            "graph": str(output_dir / "poea_graph.json"),
            "run_report": str(output_dir / "run_report.md"),
        },
        stages=[],
        warnings=[],
        config={},
    )

    report = (output_dir / "run_report.md").read_text()
    assert "Neutral assignment rate: 50.0%" in report
    assert "| Alpha | 1 | 0 | 1 | 1 | 0 | 1 / 1 | 50.0% |" in report
    assert "| Beta | 0 | 1 | 1 | 1 | 1 | 1 / 1 | 50.0% |" in report


def test_report_sample_scorer_output_rendering(tmp_path):
    output_dir = tmp_path / "artifacts"
    _write_complete_artifacts(output_dir)

    result = CliRunner().invoke(
        app,
        ["report", "--run", "latest", "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0, result.output
    report = (output_dir / "run_report.md").read_text()
    assert "## Sample Scorer Outputs" in report
    assert "Alpha=true (0.90, OBSERVED)" in report
    assert "Beta=false (0.40, SOFT_OBSERVED)" in report


# ---------------------------------------------------------------------------
# Posterior inference section (Task 1: expose old POE engine.query())
# ---------------------------------------------------------------------------

def _make_graph_with_posteriors() -> dict:
    return {
        "backend": "poe",
        "domain_id": "test-domain",
        "node_count": 2,
        "edge_count": 0,
        "nodes": [],
        "edges": [],
        "candidate_summaries": [],
        "population": {"candidate_count": 1, "active_count": 1, "dominant_log_score": -2.0},
        "posterior_inference": {
            "method": "old_poe_pgmpy_variable_elimination",
            "aggregation": "population_weighted_average",
            "posteriors": {
                "Alpha": {"True": 0.72, "False": 0.28},
                "Beta": {"True": 0.35, "False": 0.65},
            },
            "population_summary": {
                "active_candidates": 1,
                "dominant_candidate": "abc12345",
                "dominant_score": -2.0,
                "structure_entropy": 0.0,
                "paradigm_shift_count": 0,
            },
        },
        "metadata": {"created_at": "2026-05-30T00:00:00+00:00", "evidence_count": 2},
    }


def test_append_posterior_inference_section_header():
    graph = _make_graph_with_posteriors()
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "## Posterior Inference" in section
    assert "pgmpy" in section.lower() or "VariableElimination" in section


def test_append_posterior_inference_shows_method():
    graph = _make_graph_with_posteriors()
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "old_poe_pgmpy_variable_elimination" in section


def test_append_posterior_inference_shows_variable_posteriors():
    graph = _make_graph_with_posteriors()
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "Alpha" in section
    assert "Beta" in section
    assert "0.7200" in section
    assert "0.3500" in section


def test_append_posterior_inference_shows_dominant_direction():
    """Alpha has P(True)=0.72 > P(False)=0.28 → should show 'active'."""
    graph = _make_graph_with_posteriors()
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "active" in section   # Alpha: P(True)=0.72 → active
    assert "absent" in section   # Beta: P(False)=0.65 → absent


def test_append_posterior_inference_shows_population_summary():
    graph = _make_graph_with_posteriors()
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "Population Summary" in section
    assert "abc12345" in section


def test_append_posterior_inference_no_graph():
    lines: list[str] = []
    _append_posterior_inference(lines, None)
    section = "\n".join(lines)
    assert "not present" in section


def test_append_posterior_inference_missing_inference_key():
    graph = {"backend": "poe", "node_count": 1}
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "No posterior inference results" in section


def test_append_posterior_inference_error_key():
    graph = {
        "backend": "poe",
        "posterior_inference": {"error": "pgmpy model check failed"},
    }
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    assert "pgmpy model check failed" in section


def test_report_includes_posterior_inference_section_from_graph(tmp_path):
    """Full report generation includes posterior inference when graph has it."""
    output_dir = tmp_path / "artifacts"
    _write_complete_artifacts(output_dir)

    # Overwrite graph with posteriors
    _write_json(output_dir / "poea_graph.json", _make_graph_with_posteriors())

    result = CliRunner().invoke(
        app,
        ["report", "--run", "latest", "--output-dir", str(output_dir)],
    )
    assert result.exit_code == 0, result.output
    report = (output_dir / "run_report.md").read_text()
    assert "## Posterior Inference" in report
    assert "old_poe_pgmpy_variable_elimination" in report
    assert "Alpha" in report
    assert "0.7200" in report


def test_report_posterior_inference_not_claimed_as_new():
    """The posterior inference section must attribute results to old POE, not POE-A."""
    graph = _make_graph_with_posteriors()
    lines: list[str] = []
    _append_posterior_inference(lines, graph)
    section = "\n".join(lines)
    # Must clearly attribute to old POE
    assert "old POE" in section or "Old POE" in section
    # Must not claim POE-A computes posteriors
    assert "POE-A does not compute" in section or "engine.query()" in section


# ---------------------------------------------------------------------------
# Variable uncertainty section
# ---------------------------------------------------------------------------

def _make_graph_with_full_diagnostics() -> dict:
    return {
        "backend": "poe",
        "domain_id": "test-domain",
        "node_count": 2,
        "edge_count": 0,
        "nodes": [],
        "edges": [],
        "candidate_summaries": [],
        "population": {"candidate_count": 1, "active_count": 1, "dominant_log_score": -2.0},
        "posterior_inference": {
            "method": "old_poe_pgmpy_variable_elimination",
            "aggregation": "population_weighted_average",
            "posteriors": {
                "Alpha": {"True": 0.80, "False": 0.20},
                "Beta": {"True": 0.52, "False": 0.48},
                "Gamma": {"True": 0.15, "False": 0.85},
            },
        },
        "structure_diagnostics": {
            "method": "old_poe_build_structure_diagnostics",
            "env_mode": "strict",
            "total_evidence_records": 5,
            "candidates": [
                {
                    "candidate_id": "abc12345-1234-1234-1234-123456789012",
                    "description": "poea-abductive-seed",
                    "generation": 0,
                    "status": "ACTIVE",
                    "is_dominant": True,
                    "evidence_count": 5,
                    "log_score": -3.5,
                    "avg_ll": -0.70,
                    "bic_penalty_raw": 0.30,
                    "bic_score_strict": -1.00,
                    "bic_score_explore": -0.775,
                    "active_edge_count": 0,
                    "total_edge_count": 0,
                    "edges": [],
                },
            ],
        },
        "entropy_diagnostics": {
            "method": "old_poe_build_entropy_diagnostics",
            "total_evidence_rows": 5,
            "variables": {
                "Alpha": {"observed_count": 4, "missing_count": 1, "entropy": 0.8113},
                "Beta": {"observed_count": 3, "missing_count": 2, "entropy": 0.9183},
            },
            "top_mutual_information_pairs": [
                {"variable_x": "Alpha", "variable_y": "Beta", "joint_observed_count": 3, "mutual_information": 0.1245},
            ],
        },
        "metadata": {"created_at": "2026-05-30T00:00:00+00:00", "evidence_count": 5},
    }


def test_append_variable_uncertainty_section_header():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_variable_uncertainty(lines, graph)
    section = "\n".join(lines)
    assert "## Variable Uncertainty Ranking" in section


def test_append_variable_uncertainty_shows_concepts():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_variable_uncertainty(lines, graph)
    section = "\n".join(lines)
    assert "Alpha" in section
    assert "Beta" in section
    assert "Gamma" in section


def test_append_variable_uncertainty_sorted_by_certainty():
    """Beta (P=0.52, uncertainty=0.02) should appear before Alpha (P=0.80, uncertainty=0.30)."""
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_variable_uncertainty(lines, graph)
    section = "\n".join(lines)
    beta_pos = section.find("Beta")
    alpha_pos = section.find("Alpha")
    # Beta is most uncertain, should appear first
    assert beta_pos < alpha_pos


def test_append_variable_uncertainty_no_posteriors():
    graph = {"backend": "poe", "posterior_inference": {}}
    lines: list[str] = []
    _append_variable_uncertainty(lines, graph)
    section = "\n".join(lines)
    assert "No posterior inference results" in section


# ---------------------------------------------------------------------------
# Structure diagnostics section
# ---------------------------------------------------------------------------

def test_append_structure_diagnostics_section_header():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_structure_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "## Structure Diagnostics" in section
    assert "BIC" in section


def test_append_structure_diagnostics_shows_method():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_structure_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "old_poe_build_structure_diagnostics" in section


def test_append_structure_diagnostics_shows_candidate():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_structure_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "abc12345" in section
    assert "ACTIVE" in section


def test_append_structure_diagnostics_shows_dominant_marker():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_structure_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "★" in section


def test_append_structure_diagnostics_no_data():
    graph = {"backend": "poe", "structure_diagnostics": {}}
    lines: list[str] = []
    _append_structure_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "No structure diagnostics" in section


# ---------------------------------------------------------------------------
# Entropy diagnostics section
# ---------------------------------------------------------------------------

def test_append_entropy_diagnostics_section_header():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_entropy_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "## Evidence Entropy" in section


def test_append_entropy_diagnostics_shows_method():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_entropy_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "old_poe_build_entropy_diagnostics" in section


def test_append_entropy_diagnostics_shows_variable_entropy():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_entropy_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "Alpha" in section
    assert "0.8113" in section


def test_append_entropy_diagnostics_shows_mi_pairs():
    graph = _make_graph_with_full_diagnostics()
    lines: list[str] = []
    _append_entropy_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "Mutual Information" in section
    assert "Alpha" in section
    assert "Beta" in section


def test_append_entropy_diagnostics_no_data():
    graph = {"backend": "poe", "entropy_diagnostics": {}}
    lines: list[str] = []
    _append_entropy_diagnostics(lines, graph)
    section = "\n".join(lines)
    assert "No entropy diagnostics" in section


def test_full_report_includes_all_new_sections(tmp_path):
    """Full report generation includes all three new diagnostic sections."""
    output_dir = tmp_path / "artifacts"
    _write_complete_artifacts(output_dir)
    _write_json(output_dir / "poea_graph.json", _make_graph_with_full_diagnostics())

    result = CliRunner().invoke(
        app,
        ["report", "--run", "latest", "--output-dir", str(output_dir)],
    )
    assert result.exit_code == 0, result.output
    report = (output_dir / "run_report.md").read_text()

    assert "## Variable Uncertainty Ranking" in report
    assert "## Structure Diagnostics" in report
    assert "## Evidence Entropy" in report
