from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_run_report(
    path: str | Path,
    *,
    domain: str,
    backend: str,
    artifacts: dict[str, str],
    stages: list[dict[str, Any]],
    warnings: list[str],
    config: dict[str, Any],
) -> None:
    """Write a Markdown report for a pipeline run."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    evidence = _load_json(artifacts.get("evidence"))
    raw_concepts = _load_json(artifacts.get("raw_concepts"))
    registry = _load_json(artifacts.get("registry"))
    canonical = _load_json(artifacts.get("canonical_concepts"))
    scored = _load_json(artifacts.get("scored_evidence"))
    nodes = _load_json(artifacts.get("nodes"))
    graph = _load_json(artifacts.get("graph"))

    lines: list[str] = []
    lines.append("# POE-A Pipeline Run Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Domain: `{domain}`")
    lines.append(f"Backend: `{backend}`")
    lines.append("")

    lines.append("## Stage Status")
    lines.append("")
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

    lines.append("## Artifact Summary")
    lines.append("")
    lines.append(f"- Evidence records loaded: {_evidence_count(evidence)}")
    lines.append(f"- Concepts proposed: {raw_concepts.get('concept_count', 0) if isinstance(raw_concepts, dict) else 0}")
    lines.append(f"- Concepts merged: {_registry_metric(registry, 'semantic_concepts_merged')}")
    lines.append(f"- Active concepts selected: {_active_count(registry, canonical)}")
    lines.append(f"- Suppressed concepts: {_suppressed_count(registry)}")
    lines.append(f"- Nodes exported: {nodes.get('node_count', 0) if isinstance(nodes, dict) else 0}")
    lines.append(f"- Graph nodes: {graph.get('node_count', 0) if isinstance(graph, dict) else 0}")
    lines.append(f"- Graph edges: {graph.get('edge_count', 0) if isinstance(graph, dict) else 0}")
    lines.append("")

    lines.append("## Evidence Scoring Summary")
    lines.append("")
    if isinstance(scored, dict):
        summary = scored.get("summary", {})
        lines.append(f"- Evidence records scored: {summary.get('total_records', 0)}")
        lines.append(f"- Total concept/evidence pairs: {summary.get('total_pairs', 0)}")
        lines.append(f"- LLM-scored records: {summary.get('scored', 0)}")
        lines.append(f"- Cache hits: {summary.get('cache_hits', 0)}")
        lines.append(f"- Scoring errors: {summary.get('errors', 0)}")
        lines.append(f"- Neutral assignment rate: {_neutral_rate(summary)}")
    else:
        lines.append("- Evidence scoring artifact not present.")
    lines.append("")

    lines.append("## Graph Summary")
    lines.append("")
    if isinstance(graph, dict):
        lines.append(f"- Backend: `{graph.get('backend', backend)}`")
        lines.append(f"- Nodes: {graph.get('node_count', 0)}")
        lines.append(f"- Edges: {graph.get('edge_count', 0)}")
    else:
        lines.append("- Graph artifact not present.")
    lines.append("")

    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Configuration")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(config, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    for label, artifact_path in artifacts.items():
        lines.append(f"- `{label}`: `{artifact_path}`")
    lines.append("")

    p.write_text("\n".join(lines), encoding="utf-8")


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def _evidence_count(evidence: Any) -> int:
    return len(evidence) if isinstance(evidence, list) else 0


def _registry_metric(registry: Any, key: str) -> int:
    if not isinstance(registry, dict):
        return 0
    metrics = registry.get("metrics", {})
    return int(metrics.get(key, 0) or 0)


def _active_count(registry: Any, canonical: Any) -> int:
    if isinstance(canonical, dict):
        return len(canonical.get("concepts", []))
    if isinstance(registry, dict):
        return sum(1 for e in registry.get("entries", []) if e.get("status") == "active")
    return 0


def _suppressed_count(registry: Any) -> int:
    if not isinstance(registry, dict):
        return 0
    return sum(1 for e in registry.get("entries", []) if e.get("status") == "suppressed")


def _neutral_rate(summary: dict[str, Any]) -> str:
    by_concept = summary.get("by_concept", {})
    if not isinstance(by_concept, dict):
        return "n/a"
    neutral = 0
    total = 0
    for bucket in by_concept.values():
        if not isinstance(bucket, dict):
            continue
        neutral += int(bucket.get("neutral", 0) or 0)
        total += sum(int(bucket.get(k, 0) or 0) for k in ("true", "false", "neutral"))
    if total == 0:
        return "n/a"
    return f"{neutral / total:.1%}"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
