from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from poea.artifacts.reports import write_run_report
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
