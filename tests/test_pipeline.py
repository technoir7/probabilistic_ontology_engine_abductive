from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from poea.cli import app

FIXTURES = Path(__file__).parent / "fixtures"


def _write_input_evidence(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "title": "First evidence",
                    "notes": "Evidence text for alpha and beta mechanisms.",
                    "assignments": {"HandAuthoredVariable": True},
                    "causal_claims": ["Should be stripped"],
                },
                {
                    "title": "Second evidence",
                    "notes": "More evidence text for active concepts.",
                },
            ]
        ),
        encoding="utf-8",
    )


def test_pipeline_null_backend_produces_required_artifacts(tmp_path):
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    input_path = tmp_path / "evidence.json"
    _write_input_evidence(input_path)

    raw_concepts = json.loads((FIXTURES / "sample_raw_concepts.json").read_text())
    (output_dir / "raw_concepts.json").write_text(
        json.dumps(raw_concepts),
        encoding="utf-8",
    )

    graph_path = output_dir / "poea_graph.json"
    result = CliRunner().invoke(
        app,
        [
            "pipeline",
            "--domain",
            "test",
            "--input",
            str(input_path),
            "--backend",
            "null",
            "--output-dir",
            str(output_dir),
            "--output",
            str(graph_path),
        ],
    )

    assert result.exit_code == 0, result.output
    for name in (
        "evidence.json",
        "raw_concepts.json",
        "concept_registry.json",
        "canonical_concepts.json",
        "nodes.json",
        "poea_graph.json",
        "run_report.md",
    ):
        assert (output_dir / name).exists(), f"missing artifact: {name}"

    graph = json.loads(graph_path.read_text())
    canonical = json.loads((output_dir / "canonical_concepts.json").read_text())
    assert graph["backend"] == "null"
    assert graph["node_count"] == len(canonical["concepts"])
    assert graph["edge_count"] == 0


def test_pipeline_null_backend_skips_live_scoring_when_no_cache(tmp_path):
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    input_path = tmp_path / "evidence.json"
    _write_input_evidence(input_path)
    (output_dir / "raw_concepts.json").write_text(
        (FIXTURES / "sample_raw_concepts.json").read_text(),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "pipeline",
            "--domain",
            "test",
            "--input",
            str(input_path),
            "--backend",
            "null",
            "--output-dir",
            str(output_dir),
            "--output",
            str(output_dir / "poea_graph.json"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert not (output_dir / "scored_evidence.json").exists()

    report = (output_dir / "run_report.md").read_text()
    assert "Skipped live evidence scoring for null backend" in report
    assert "Final" not in report  # report is generated from this run, not prior analysis text


def test_pipeline_report_records_stage_status(tmp_path):
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    input_path = tmp_path / "evidence.json"
    _write_input_evidence(input_path)
    (output_dir / "raw_concepts.json").write_text(
        (FIXTURES / "sample_raw_concepts.json").read_text(),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "pipeline",
            "--domain",
            "test",
            "--input",
            str(input_path),
            "--backend",
            "null",
            "--output-dir",
            str(output_dir),
            "--output",
            str(output_dir / "poea_graph.json"),
        ],
    )

    assert result.exit_code == 0, result.output
    report = (output_dir / "run_report.md").read_text()
    assert "| ingest | ran |" in report
    assert "| induce | skipped |" in report
    assert "| run-backend | ran |" in report
    assert "Graph nodes:" in report
