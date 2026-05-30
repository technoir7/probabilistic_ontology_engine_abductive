from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPORT_ARTIFACTS = {
    "evidence": "evidence.json",
    "raw_concepts": "raw_concepts.json",
    "registry": "concept_registry.json",
    "canonical_concepts": "canonical_concepts.json",
    "scored_evidence": "scored_evidence.json",
    "nodes": "nodes.json",
    "graph": "poea_graph.json",
    "run_report": "run_report.md",
}


@dataclass(frozen=True)
class ScoringDiagnostics:
    records: int = 0
    total_pairs: int = 0
    true_count: int = 0
    false_count: int = 0
    neutral_count: int = 0
    missing_count: int = 0
    observed_count: int = 0
    soft_observed_count: int = 0
    missingness_missing_count: int = 0
    errors: int = 0
    included_learning_records: int = 0
    omitted_learning_records: int = 0
    all_neutral_records: int = 0
    no_scoreable_assignment_records: int = 0
    by_concept: dict[str, dict[str, int]] | None = None


def default_report_artifacts(
    output_dir: str | Path = "artifacts",
    *,
    graph_path: str | Path | None = None,
    report_path: str | Path | None = None,
) -> dict[str, str]:
    """Return conventional artifact paths for a latest-run report."""
    out = Path(output_dir)
    paths = {name: out / filename for name, filename in _REPORT_ARTIFACTS.items()}
    if graph_path is not None:
        paths["graph"] = Path(graph_path)
    if report_path is not None:
        paths["run_report"] = Path(report_path)
    return {k: str(v) for k, v in paths.items()}


def write_run_report(
    path: str | Path,
    *,
    domain: str,
    backend: str,
    artifacts: dict[str, str],
    stages: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Write a Markdown report for a pipeline run or regenerated artifact audit."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    loaded = {
        name: _load_json(artifact_path)
        for name, artifact_path in artifacts.items()
        if name != "run_report"
    }
    evidence = loaded.get("evidence")
    raw_concepts = loaded.get("raw_concepts")
    registry = loaded.get("registry")
    canonical = loaded.get("canonical_concepts")
    scored = loaded.get("scored_evidence")
    nodes = loaded.get("nodes")
    graph = loaded.get("graph")

    inferred_domain = domain if domain != "unknown" else _infer_domain(evidence, nodes)
    inferred_backend = backend if backend != "unknown" else _infer_backend(graph, config or {})
    diagnostics = _scoring_diagnostics(scored)
    generated_warnings = _generate_warnings(
        artifacts=artifacts,
        evidence=evidence,
        registry=registry,
        canonical=canonical,
        scored=scored,
        graph=graph,
        diagnostics=diagnostics,
    )
    all_warnings = list(warnings or []) + [w for w in generated_warnings if w not in set(warnings or [])]

    lines: list[str] = []
    lines.append("# POE-A Run Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Domain: `{inferred_domain}`")
    lines.append(f"Backend: `{inferred_backend}`")
    lines.append("")

    _append_stage_status(lines, stages or [])
    _append_run_summary(lines, evidence, raw_concepts, registry, canonical, scored, nodes, graph, diagnostics)
    _append_concept_summary(lines, registry, canonical)
    _append_scoring_summary(lines, scored, diagnostics)
    _append_concept_scoring_table(lines, registry, scored, diagnostics)
    _append_sample_scorer_outputs(lines, evidence, scored)
    _append_graph_summary(lines, graph, inferred_backend)
    _append_backend_candidates(lines, graph)
    _append_warnings(lines, all_warnings)
    _append_timestamps(lines, raw_concepts, registry, canonical, scored, nodes, graph)
    _append_configuration(lines, config or {})
    _append_artifacts(lines, artifacts)

    p.write_text("\n".join(lines), encoding="utf-8")


def _append_stage_status(lines: list[str], stages: list[dict[str, Any]]) -> None:
    lines.append("## Stage Status")
    lines.append("")
    if not stages:
        lines.append("- Regenerated from existing artifacts; no pipeline stages were run.")
        lines.append("")
        return

    lines.append("| Stage | Status | Detail |")
    lines.append("| --- | --- | --- |")
    for stage in stages:
        lines.append(
            "| {name} | {status} | {detail} |".format(
                name=_escape(str(stage.get("name", ""))),
                status=_escape(str(stage.get("status", ""))),
                detail=_escape(str(stage.get("detail", ""))),
            )
        )
    lines.append("")


def _append_run_summary(
    lines: list[str],
    evidence: Any,
    raw_concepts: Any,
    registry: Any,
    canonical: Any,
    scored: Any,
    nodes: Any,
    graph: Any,
    diagnostics: ScoringDiagnostics,
) -> None:
    status_counts = _status_counts(registry)
    dropped = status_counts["suppressed"] + status_counts["rejected"] + status_counts["merged_into"]

    lines.append("## Run Summary")
    lines.append("")
    lines.append(f"- Evidence records loaded: {_evidence_count(evidence)}")
    lines.append(f"- Concepts proposed: {_raw_concept_count(raw_concepts)}")
    lines.append(f"- Concepts merged: {_merged_count(registry)}")
    lines.append(f"- Active concepts selected: {_active_count(registry, canonical)}")
    lines.append(f"- Dropped concepts: {dropped}")
    lines.append(f"- Suppressed concepts: {status_counts['suppressed']}")
    lines.append(f"- Rejected concepts: {status_counts['rejected']}")
    lines.append(f"- Merged-into concepts: {status_counts['merged_into']}")
    lines.append(f"- Total concept/evidence score pairs: {diagnostics.total_pairs}")
    lines.append(f"- Scoring errors: {diagnostics.errors}")
    lines.append(f"- Records included in POE learning: {diagnostics.included_learning_records}")
    lines.append(f"- Records omitted from POE learning: {diagnostics.omitted_learning_records}")
    lines.append(f"- Nodes exported: {_artifact_count(nodes, 'node_count')}")
    lines.append(f"- Graph nodes: {_artifact_count(graph, 'node_count')}")
    lines.append(f"- Graph edges: {_artifact_count(graph, 'edge_count')}")
    lines.append(f"- Learned edges: {_artifact_count(graph, 'edge_count')}")
    lines.append("")


def _append_concept_summary(lines: list[str], registry: Any, canonical: Any) -> None:
    status_counts = _status_counts(registry)
    metrics = registry.get("metrics", {}) if isinstance(registry, dict) else {}

    lines.append("## Concept Registry")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| active | {_active_count(registry, canonical)} |")
    lines.append(f"| suppressed | {status_counts['suppressed']} |")
    lines.append(f"| rejected | {status_counts['rejected']} |")
    lines.append(f"| merged_into | {status_counts['merged_into']} |")
    lines.append(f"| exact duplicates merged | {int(metrics.get('exact_duplicates_merged', 0) or 0)} |")
    lines.append(f"| semantic concepts merged | {int(metrics.get('semantic_concepts_merged', 0) or 0)} |")
    lines.append("")

    entries = registry.get("entries", []) if isinstance(registry, dict) else []
    active = [e for e in entries if isinstance(e, dict) and e.get("status") == "active"]
    if active:
        lines.append("### Active Concepts")
        lines.append("")
        lines.append("| Concept | Confidence | Registry evidence |")
        lines.append("| --- | ---: | ---: |")
        for entry in active:
            lines.append(
                "| {name} | {conf:.2f} | {support} |".format(
                    name=_escape(str(entry.get("name", ""))),
                    conf=float(entry.get("confidence", 0.0) or 0.0),
                    support=len(entry.get("supporting_evidence_ids", []) or []),
                )
            )
        lines.append("")


def _append_scoring_summary(lines: list[str], scored: Any, diagnostics: ScoringDiagnostics) -> None:
    metadata = scored.get("metadata", {}) if isinstance(scored, dict) else {}
    summary = scored.get("summary", {}) if isinstance(scored, dict) else {}

    lines.append("## Evidence Scoring Summary")
    lines.append("")
    if not isinstance(scored, dict):
        lines.append("- Evidence scoring artifact not present.")
        lines.append("")
        return

    lines.append(f"- Evidence records scored: {summary.get('total_records', diagnostics.records)}")
    lines.append(f"- Total concept/evidence pairs: {summary.get('total_pairs', diagnostics.total_pairs)}")
    lines.append(f"- LLM-scored records: {summary.get('scored', 0)}")
    lines.append(f"- Cache hits: {summary.get('cache_hits', 0)}")
    lines.append(f"- Scoring errors: {diagnostics.errors}")
    lines.append(f"- True assignment rate: {_format_rate(diagnostics.true_count, diagnostics.total_pairs)}")
    lines.append(f"- False assignment rate: {_format_rate(diagnostics.false_count, diagnostics.total_pairs)}")
    lines.append(f"- Neutral assignment rate: {_format_rate(diagnostics.neutral_count, diagnostics.total_pairs)}")
    lines.append(f"- Missing assignment rate: {_format_rate(diagnostics.missing_count, diagnostics.total_pairs)}")
    lines.append(f"- SOFT_OBSERVED assignments: {diagnostics.soft_observed_count}")
    lines.append(f"- OBSERVED assignments: {diagnostics.observed_count}")
    lines.append(f"- MISSING assignments: {diagnostics.missingness_missing_count}")
    lines.append(f"- All-neutral records: {diagnostics.all_neutral_records}")
    lines.append(f"- Records with no scoreable assignments: {diagnostics.no_scoreable_assignment_records}")
    lines.append(f"- Records included in POE learning: {diagnostics.included_learning_records}")
    lines.append(f"- Records omitted from POE learning: {diagnostics.omitted_learning_records}")
    if metadata:
        lines.append(f"- Scoring model: `{metadata.get('model', 'unknown')}`")
        lines.append(f"- Scored at: `{metadata.get('scored_at', 'unknown')}`")
        lines.append(f"- Soft observed threshold: `{metadata.get('soft_observed_threshold', 'unknown')}`")
        router = metadata.get("assignment_router", {})
        if isinstance(router, dict) and router:
            lines.append(f"- Assignment router: `{router.get('router', 'unknown')}`")
            lines.append(f"- Assignment mode counts: `{router.get('mode_counts', {})}`")
            lines.append(f"- Assignment backend counts: `{router.get('backend_counts', {})}`")
    lines.append("")


def _append_concept_scoring_table(
    lines: list[str],
    registry: Any,
    scored: Any,
    diagnostics: ScoringDiagnostics,
) -> None:
    lines.append("## Assignments Per Concept")
    lines.append("")
    if not isinstance(scored, dict):
        lines.append("- Evidence scoring artifact not present.")
        lines.append("")
        return

    support_by_name = _registry_support_by_name(registry)
    by_concept = diagnostics.by_concept or {}
    if not by_concept:
        lines.append("- No concept-level scoring summary available.")
        lines.append("")
        return

    lines.append("| Concept | True | False | Neutral | Missing | SOFT_OBSERVED | Observed support | Neutral rate |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for concept_name in sorted(by_concept):
        bucket = by_concept[concept_name]
        total = int(bucket.get("true", 0)) + int(bucket.get("false", 0)) + int(bucket.get("neutral", 0))
        observed_support = int(bucket.get("true", 0)) + int(bucket.get("false", 0))
        lines.append(
            "| {name} | {true} | {false} | {neutral} | {missing} | {soft} | {observed} / {registry_support} | {neutral_rate} |".format(
                name=_escape(concept_name),
                true=int(bucket.get("true", 0)),
                false=int(bucket.get("false", 0)),
                neutral=int(bucket.get("neutral", 0)),
                missing=int(bucket.get("missing", 0)),
                soft=int(bucket.get("soft_observed", 0)),
                observed=observed_support,
                registry_support=support_by_name.get(concept_name, 0),
                neutral_rate=_format_rate(int(bucket.get("neutral", 0)), total),
            )
        )
    lines.append("")


def _append_sample_scorer_outputs(lines: list[str], evidence: Any, scored: Any) -> None:
    lines.append("## Sample Scorer Outputs")
    lines.append("")
    if not isinstance(scored, dict):
        lines.append("- Evidence scoring artifact not present.")
        lines.append("")
        return

    samples = _sample_scored_records(scored)
    if not samples:
        lines.append("- No scored records available.")
        lines.append("")
        return

    evidence_titles = _evidence_titles(evidence)
    lines.append("| Evidence | Title | Error | True | False | Neutral | SOFT_OBSERVED | Sample assignments |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for record in samples:
        counts = _record_counts(record)
        evidence_id = str(record.get("evidence_id", ""))
        lines.append(
            "| {evidence_id} | {title} | {error} | {true} | {false} | {neutral} | {soft} | {assignments} |".format(
                evidence_id=_escape(evidence_id),
                title=_escape(evidence_titles.get(evidence_id, "")),
                error=_escape(str(record.get("error") or "")),
                true=counts["true"],
                false=counts["false"],
                neutral=counts["neutral"],
                soft=counts["soft_observed"],
                assignments=_escape(_sample_assignment_text(record)),
            )
        )
    lines.append("")


def _append_graph_summary(lines: list[str], graph: Any, backend: str) -> None:
    lines.append("## Graph Summary")
    lines.append("")
    if not isinstance(graph, dict):
        lines.append("- Graph artifact not present.")
        lines.append("")
        return

    metadata = graph.get("metadata", {}) if isinstance(graph.get("metadata"), dict) else {}
    lines.append(f"- Backend: `{graph.get('backend', backend)}`")
    lines.append(f"- Domain ID: `{graph.get('domain_id', 'n/a')}`")
    lines.append(f"- Nodes: {graph.get('node_count', 0)}")
    lines.append(f"- Edges: {graph.get('edge_count', 0)}")
    lines.append(f"- Backend evidence records: {metadata.get('evidence_count', 'n/a')}")
    lines.append(f"- Graph created at: `{metadata.get('created_at', 'unknown')}`")
    lines.append("")

    edges = graph.get("edges", [])
    if isinstance(edges, list) and edges:
        lines.append("### Learned Edges")
        lines.append("")
        lines.append("| Parent | Child | Existence probability |")
        lines.append("| --- | --- | ---: |")
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            probability = edge.get("existence_probability", "")
            lines.append(
                "| {parent} | {child} | {probability} |".format(
                    parent=_escape(str(edge.get("parent", ""))),
                    child=_escape(str(edge.get("child", ""))),
                    probability=_format_float(probability),
                )
            )
        lines.append("")


def _append_backend_candidates(lines: list[str], graph: Any) -> None:
    lines.append("## Backend Candidate Summaries")
    lines.append("")
    if not isinstance(graph, dict):
        lines.append("- Graph artifact not present.")
        lines.append("")
        return

    population = graph.get("population", {})
    if isinstance(population, dict) and population:
        lines.append(f"- Candidate count: {population.get('candidate_count', 0)}")
        lines.append(f"- Active candidates: {population.get('active_count', 0)}")
        lines.append(f"- Dominant log score: {_format_float(population.get('dominant_log_score', 0.0))}")
        lines.append("")

    candidates = graph.get("candidate_summaries", [])
    if not isinstance(candidates, list) or not candidates:
        lines.append("- No backend candidate summaries present.")
        lines.append("")
        return

    lines.append("| Candidate | Status | Log score | Evidence count | Active edges |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for candidate in candidates[:10]:
        if not isinstance(candidate, dict):
            continue
        lines.append(
            "| {candidate_id} | {status} | {log_score} | {evidence_count} | {active_edge_count} |".format(
                candidate_id=_escape(str(candidate.get("candidate_id", ""))),
                status=_escape(str(candidate.get("status", ""))),
                log_score=_format_float(candidate.get("log_score", 0.0)),
                evidence_count=candidate.get("evidence_count", 0),
                active_edge_count=candidate.get("active_edge_count", 0),
            )
        )
    if len(candidates) > 10:
        lines.append(f"| ... | ... | ... | ... | {len(candidates) - 10} additional candidate(s) omitted |")
    lines.append("")


def _append_warnings(lines: list[str], warnings: list[str]) -> None:
    lines.append("## Warnings And Anomalies")
    lines.append("")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")
    lines.append("")


def _append_timestamps(
    lines: list[str],
    raw_concepts: Any,
    registry: Any,
    canonical: Any,
    scored: Any,
    nodes: Any,
    graph: Any,
) -> None:
    lines.append("## Artifact Timestamps")
    lines.append("")
    lines.append("| Artifact | Recorded timestamp |")
    lines.append("| --- | --- |")
    lines.append(f"| raw_concepts.model | `{_dict_get(raw_concepts, 'model')}` |")
    lines.append(f"| registry.created_at | `{_metadata_get(registry, 'created_at')}` |")
    lines.append(f"| canonical_concepts.created_at | `{_metadata_get(canonical, 'created_at')}` |")
    lines.append(f"| scored_evidence.scored_at | `{_metadata_get(scored, 'scored_at')}` |")
    lines.append(f"| nodes.created_at | `{_metadata_get(nodes, 'created_at')}` |")
    lines.append(f"| graph.created_at | `{_metadata_get(graph, 'created_at')}` |")
    lines.append("")


def _append_configuration(lines: list[str], config: dict[str, Any]) -> None:
    lines.append("## Configuration")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(config, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")


def _append_artifacts(lines: list[str], artifacts: dict[str, str]) -> None:
    lines.append("## Artifacts")
    lines.append("")
    lines.append("| Label | Path | Exists | Modified UTC | Size bytes |")
    lines.append("| --- | --- | --- | --- | ---: |")
    for label, artifact_path in artifacts.items():
        path = Path(artifact_path)
        exists = path.exists()
        modified = _mtime_iso(path) if exists else "missing"
        size = path.stat().st_size if exists else 0
        lines.append(
            "| {label} | `{path}` | {exists} | `{modified}` | {size} |".format(
                label=_escape(label),
                path=_escape(str(path)),
                exists="yes" if exists else "no",
                modified=modified,
                size=size,
            )
        )
    lines.append("")


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None


def _evidence_count(evidence: Any) -> int:
    return len(evidence) if isinstance(evidence, list) else 0


def _raw_concept_count(raw_concepts: Any) -> int:
    if not isinstance(raw_concepts, dict):
        return 0
    return int(raw_concepts.get("concept_count", len(raw_concepts.get("concepts", [])) or 0) or 0)


def _merged_count(registry: Any) -> int:
    if not isinstance(registry, dict):
        return 0
    metrics = registry.get("metrics", {})
    semantic = int(metrics.get("semantic_concepts_merged", 0) or 0)
    if semantic:
        return semantic
    return _status_counts(registry)["merged_into"]


def _active_count(registry: Any, canonical: Any) -> int:
    if isinstance(canonical, dict):
        return len(canonical.get("concepts", []))
    if isinstance(registry, dict):
        return sum(1 for e in registry.get("entries", []) if e.get("status") == "active")
    return 0


def _artifact_count(artifact: Any, key: str) -> int:
    if not isinstance(artifact, dict):
        return 0
    return int(artifact.get(key, 0) or 0)


def _status_counts(registry: Any) -> Counter:
    counts: Counter = Counter()
    if isinstance(registry, dict):
        for entry in registry.get("entries", []):
            if isinstance(entry, dict):
                counts[str(entry.get("status", "unknown"))] += 1
    return counts


def _registry_support_by_name(registry: Any) -> dict[str, int]:
    support: dict[str, int] = {}
    if not isinstance(registry, dict):
        return support
    for entry in registry.get("entries", []):
        if not isinstance(entry, dict):
            continue
        support[str(entry.get("name", ""))] = len(entry.get("supporting_evidence_ids", []) or [])
    return support


def _scoring_diagnostics(scored: Any) -> ScoringDiagnostics:
    if not isinstance(scored, dict):
        return ScoringDiagnostics(by_concept={})

    records = [r for r in scored.get("scored_records", []) if isinstance(r, dict)]
    by_concept: dict[str, dict[str, int]] = {}
    true_count = false_count = neutral_count = 0
    observed_count = soft_observed_count = missing_count = 0
    all_neutral_records = no_scoreable_records = 0

    for record in records:
        counts = _record_counts(record)
        true_count += counts["true"]
        false_count += counts["false"]
        neutral_count += counts["neutral"]
        observed_count += counts["observed"]
        soft_observed_count += counts["soft_observed"]
        missing_count += counts["missing"]
        if counts["true"] == 0 and counts["false"] == 0 and counts["neutral"] > 0:
            all_neutral_records += 1
        if counts["true"] == 0 and counts["false"] == 0 and counts["soft_observed"] == 0:
            no_scoreable_records += 1
        for assignment in record.get("assignments", []):
            if not isinstance(assignment, dict):
                continue
            concept_name = str(assignment.get("variable_name", assignment.get("concept_id", "")))
            bucket = by_concept.setdefault(
                concept_name,
                {"true": 0, "false": 0, "neutral": 0, "missing": 0, "soft_observed": 0},
            )
            if assignment.get("assigned_value") is True:
                bucket["true"] += 1
            elif assignment.get("assigned_value") is False:
                bucket["false"] += 1
            else:
                bucket["neutral"] += 1
            if assignment.get("missingness") == "MISSING":
                bucket["missing"] += 1
            if assignment.get("missingness") == "SOFT_OBSERVED":
                bucket["soft_observed"] += 1

    summary = scored.get("summary", {})
    total_pairs = int(summary.get("total_pairs", true_count + false_count + neutral_count) or 0)
    errors = int(summary.get("errors", sum(1 for r in records if r.get("error"))) or 0)
    included = len(records) - no_scoreable_records

    return ScoringDiagnostics(
        records=len(records),
        total_pairs=total_pairs,
        true_count=true_count,
        false_count=false_count,
        neutral_count=neutral_count,
        missing_count=missing_count,
        observed_count=observed_count,
        soft_observed_count=soft_observed_count,
        missingness_missing_count=missing_count,
        errors=errors,
        included_learning_records=included,
        omitted_learning_records=no_scoreable_records,
        all_neutral_records=all_neutral_records,
        no_scoreable_assignment_records=no_scoreable_records,
        by_concept=by_concept,
    )


def _record_counts(record: dict[str, Any]) -> dict[str, int]:
    counts = {"true": 0, "false": 0, "neutral": 0, "observed": 0, "soft_observed": 0, "missing": 0}
    for assignment in record.get("assignments", []):
        if not isinstance(assignment, dict):
            continue
        if assignment.get("assigned_value") is True:
            counts["true"] += 1
        elif assignment.get("assigned_value") is False:
            counts["false"] += 1
        else:
            counts["neutral"] += 1

        missingness = assignment.get("missingness")
        if missingness == "OBSERVED":
            counts["observed"] += 1
        elif missingness == "SOFT_OBSERVED":
            counts["soft_observed"] += 1
        elif missingness == "MISSING":
            counts["missing"] += 1
    return counts


def _generate_warnings(
    *,
    artifacts: dict[str, str],
    evidence: Any,
    registry: Any,
    canonical: Any,
    scored: Any,
    graph: Any,
    diagnostics: ScoringDiagnostics,
) -> list[str]:
    warnings: list[str] = []

    for label, artifact_path in artifacts.items():
        if label == "run_report":
            continue
        if not Path(artifact_path).exists():
            warnings.append(f"Missing artifact: {label} ({artifact_path}).")

    evidence_count = _evidence_count(evidence)
    if isinstance(scored, dict):
        scored_records = int(scored.get("summary", {}).get("total_records", diagnostics.records) or 0)
        if evidence_count and scored_records != evidence_count:
            warnings.append(f"Evidence/scoring record mismatch: {evidence_count} evidence records vs {scored_records} scored records.")

    if diagnostics.total_pairs:
        neutral_rate = diagnostics.neutral_count / diagnostics.total_pairs
        if neutral_rate >= 0.90:
            warnings.append(f"High neutral assignment rate: {neutral_rate:.1%}.")
    if diagnostics.all_neutral_records:
        warnings.append(f"{diagnostics.all_neutral_records} scored record(s) are all-neutral.")
    if diagnostics.errors:
        warnings.append(f"{diagnostics.errors} scoring error(s) recorded.")
    if diagnostics.no_scoreable_assignment_records:
        warnings.append(f"{diagnostics.no_scoreable_assignment_records} evidence record(s) have no scoreable assignments for POE learning.")

    low_support = _low_observed_support_concepts(diagnostics)
    if low_support:
        rendered = ", ".join(low_support[:8])
        suffix = f" (+{len(low_support) - 8} more)" if len(low_support) > 8 else ""
        warnings.append(f"Concepts with one or fewer observed true/false assignments: {rendered}{suffix}.")

    graph_evidence = _graph_evidence_count(graph)
    if graph_evidence is not None and graph_evidence != diagnostics.included_learning_records:
        warnings.append(
            "Scored records included in POE learning do not match graph backend evidence count: "
            f"{diagnostics.included_learning_records} included vs {graph_evidence} in graph metadata."
        )

    active_count = _active_count(registry, canonical)
    graph_nodes = _artifact_count(graph, "node_count")
    if active_count and graph_nodes and active_count != graph_nodes:
        warnings.append(f"Active concept/node mismatch: {active_count} active concepts vs {graph_nodes} graph nodes.")

    return warnings


def _low_observed_support_concepts(diagnostics: ScoringDiagnostics) -> list[str]:
    low: list[str] = []
    for name, bucket in (diagnostics.by_concept or {}).items():
        observed = int(bucket.get("true", 0)) + int(bucket.get("false", 0))
        if observed <= 1:
            low.append(name)
    return sorted(low)


def _graph_evidence_count(graph: Any) -> int | None:
    if not isinstance(graph, dict):
        return None
    metadata = graph.get("metadata", {})
    if not isinstance(metadata, dict) or "evidence_count" not in metadata:
        return None
    try:
        return int(metadata["evidence_count"])
    except (TypeError, ValueError):
        return None


def _sample_scored_records(scored: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    records = [r for r in scored.get("scored_records", []) if isinstance(r, dict)]
    selected: list[dict[str, Any]] = []

    def add(match: Any) -> None:
        if isinstance(match, dict) and match not in selected:
            selected.append(match)

    add(next((r for r in records if r.get("error")), None))
    add(next((r for r in records if _record_counts(r)["true"] or _record_counts(r)["false"]), None))
    add(next((r for r in records if _record_counts(r)["true"] == 0 and _record_counts(r)["false"] == 0), None))
    for record in records:
        add(record)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _sample_assignment_text(record: dict[str, Any], limit: int = 5) -> str:
    parts: list[str] = []
    for assignment in record.get("assignments", [])[:limit]:
        if not isinstance(assignment, dict):
            continue
        value = assignment.get("assigned_value")
        if value is True:
            rendered_value = "true"
        elif value is False:
            rendered_value = "false"
        else:
            rendered_value = "neutral"
        parts.append(
            "{name}={value} ({confidence:.2f}, {missingness})".format(
                name=assignment.get("variable_name", assignment.get("concept_id", "")),
                value=rendered_value,
                confidence=float(assignment.get("confidence", 0.0) or 0.0),
                missingness=assignment.get("missingness", ""),
            )
        )
    if len(record.get("assignments", [])) > limit:
        parts.append("...")
    return "; ".join(parts)


def _evidence_titles(evidence: Any) -> dict[str, str]:
    if not isinstance(evidence, list):
        return {}
    return {
        str(item.get("evidence_id", "")): str(item.get("title", ""))
        for item in evidence
        if isinstance(item, dict)
    }


def _infer_domain(evidence: Any, nodes: Any) -> str:
    if isinstance(nodes, dict) and nodes.get("domain_tag"):
        return str(nodes["domain_tag"])
    if isinstance(evidence, list) and evidence and isinstance(evidence[0], dict):
        return str(evidence[0].get("domain_tag", "unknown"))
    return "unknown"


def _infer_backend(graph: Any, config: dict[str, Any]) -> str:
    if isinstance(graph, dict) and graph.get("backend"):
        return str(graph["backend"])
    backend_config = config.get("backend", {})
    if isinstance(backend_config, dict) and backend_config.get("default"):
        return str(backend_config["default"])
    return "unknown"


def _metadata_get(artifact: Any, key: str) -> str:
    if not isinstance(artifact, dict):
        return "n/a"
    metadata = artifact.get("metadata", {})
    if not isinstance(metadata, dict):
        return "n/a"
    return str(metadata.get(key, "n/a"))


def _dict_get(artifact: Any, key: str) -> str:
    if not isinstance(artifact, dict):
        return "n/a"
    return str(artifact.get(key, "n/a"))


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.1%}"


def _format_float(value: Any) -> str:
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
