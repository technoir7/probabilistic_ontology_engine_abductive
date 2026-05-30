from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

from .backends import get_backend
from .concepts.inducer import ConceptInducer, InductionConfig
from .concepts.scorer import (
    EvidenceScorer,
    ScoringConfig,
    load_scored_evidence,
    save_scored_evidence,
)
from .evidence.loaders import load_from_path
from .evidence.schemas import EvidenceUnit
from .registry.export import build_registry, write_registry_artifacts
from .registry.lifecycle import promote
from .registry.schemas import ConceptEntry
from .registry.store import load_registry

app = typer.Typer(
    name="poea",
    help="Probabilistic Ontology Engine Abductive",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

# ---------------------------------------------------------------------------
# Registry subcommand group
# ---------------------------------------------------------------------------

registry_app = typer.Typer(name="registry", help="Registry management commands.")
app.add_typer(registry_app)


@registry_app.command("promote")
def registry_promote(
    registry: Annotated[
        Path,
        typer.Option("--registry", "-r", help="Path to concept_registry.json"),
    ] = Path("artifacts/concept_registry.json"),
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for updated artifacts"),
    ] = Path("artifacts"),
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Config YAML path"),
    ] = None,
    auto: Annotated[
        bool,
        typer.Option("--auto", help="Apply promotion changes (omit for dry-run preview)"),
    ] = False,
    include_suppressed: Annotated[
        bool,
        typer.Option(
            "--include-suppressed",
            help="Reset suppressed concepts to candidate before re-evaluating",
        ),
    ] = False,
    confidence: Annotated[
        Optional[float],
        typer.Option("--confidence", help="Override min_confidence threshold"),
    ] = None,
    min_evidence: Annotated[
        Optional[int],
        typer.Option("--min-evidence", help="Override min_supporting_evidence threshold"),
    ] = None,
    max_active: Annotated[
        Optional[int],
        typer.Option("--max-active", help="Override max_active_concepts cap"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """
    Re-apply promotion rules to candidate concepts in the registry.

    Without --auto, prints a dry-run preview of what would be promoted or
    suppressed.  With --auto, writes updated concept_registry.json and
    canonical_concepts.json.

    Use --include-suppressed to reset suppressed concepts back to candidate
    before re-evaluation (useful for threshold tuning without re-running
    consolidation).
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not registry.exists():
        err_console.print(f"[red]Registry not found: {registry}[/red]")
        err_console.print("Run: poea consolidate --concepts artifacts/raw_concepts.json")
        raise typer.Exit(1)

    cfg_path = config_path or Path("configs/induction_config.yaml")
    raw_config = _load_config(cfg_path)
    concept_cfg = raw_config.get("concepts", {})

    promo_conf = confidence if confidence is not None else concept_cfg.get("promotion_confidence", 0.75)
    promo_evidence = min_evidence if min_evidence is not None else concept_cfg.get("min_supporting_evidence", 2)
    promo_max = max_active if max_active is not None else concept_cfg.get("max_active_concepts", 30)

    entries, existing_meta = load_registry(registry)

    if include_suppressed:
        reset_count = sum(1 for e in entries if e.status == "suppressed")
        for e in entries:
            if e.status == "suppressed":
                e.status = "candidate"
        console.print(f"[yellow]Reset {reset_count} suppressed concept(s) to candidate[/yellow]")

    candidates_before = sum(1 for e in entries if e.status == "candidate")
    if candidates_before == 0:
        console.print("[yellow]No candidates to evaluate. Use --include-suppressed to re-evaluate suppressed concepts.[/yellow]")
        if not auto:
            raise typer.Exit(0)

    # Run promotion on a copy for dry-run preview
    import copy
    preview_entries = copy.deepcopy(entries)
    preview_entries, preview_counts, preview_events = promote(
        preview_entries,
        min_confidence=promo_conf,
        min_evidence=promo_evidence,
        max_active=promo_max,
    )

    promoted = sum(1 for ev in preview_events if ev["event_type"] == "promoted_to_active")
    supp_conf = preview_counts["by_confidence"]
    supp_ev = preview_counts["by_evidence"]
    supp_cap = preview_counts["by_cap"]
    active_after = sum(1 for e in preview_entries if e.status == "active")

    console.print(f"\n[bold]Promotion preview[/bold]  (conf ≥ {promo_conf}, evidence ≥ {promo_evidence}, cap {promo_max})")
    console.print(f"  Candidates evaluated:      {candidates_before}")
    console.print(f"  → Promoted to active:      {promoted}")
    console.print(f"  → Suppressed (confidence): {supp_conf}")
    console.print(f"  → Suppressed (evidence):   {supp_ev}")
    console.print(f"  → Suppressed (cap):        {supp_cap}")
    console.print(f"  Active after promotion:    {active_after}")

    if not auto:
        console.print("\n[yellow]Dry-run — pass --auto to apply changes[/yellow]")
        raise typer.Exit(0)

    # Apply and write
    entries, counts, events = promote(
        entries,
        min_confidence=promo_conf,
        min_evidence=promo_evidence,
        max_active=promo_max,
    )

    active_count = write_registry_artifacts(
        entries=entries,
        promotion_events=events,
        existing_meta=existing_meta,
        output_dir=output_dir,
        promotion_confidence=promo_conf,
        min_evidence=promo_evidence,
        max_active=promo_max,
    )

    console.print(f"\n[green]Registry updated — {active_count} active concept(s)[/green]")
    console.print(f"  → {output_dir}/concept_registry.json")
    console.print(f"  → {output_dir}/canonical_concepts.json")

    if verbose and active_count:
        active_entries = [e for e in entries if e.status == "active"]
        table = Table("name", "confidence", "evidence_count")
        for e in sorted(active_entries, key=lambda x: -x.confidence):
            table.add_row(e.name, f"{e.confidence:.2f}", str(len(e.supporting_evidence_ids)))
        console.print(table)


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------

def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with config_path.open() as f:
        return yaml.safe_load(f) or {}


@app.command()
def ingest(
    input: Annotated[Path, typer.Option("--input", "-i", help="JSON file or directory of JSON files")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output evidence.json path")] = Path("artifacts/evidence.json"),
    domain: Annotated[str, typer.Option("--domain", "-d", help="Domain tag")] = "unknown",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Load and normalize evidence records. Discards assignments and causal_claims."""
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not input.exists():
        err_console.print(f"[red]Input path does not exist: {input}[/red]")
        raise typer.Exit(1)

    try:
        units = load_from_path(input, domain_tag=domain)
    except Exception as exc:
        err_console.print(f"[red]Failed to load evidence: {exc}[/red]")
        raise typer.Exit(1)

    if not units:
        err_console.print("[yellow]Warning: no evidence records loaded[/yellow]")
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump([u.model_dump() for u in units], f, indent=2, ensure_ascii=False)

    sparse_count = sum(1 for u in units if u.metadata.get("sparse_text"))

    console.print(f"[green]Loaded {len(units)} evidence records → {output}[/green]")
    if sparse_count:
        console.print(
            f"[yellow]  {sparse_count} records are title-only (no body text)[/yellow]"
        )

    if verbose:
        table = Table("evidence_id", "title", "text_len", "sparse")
        for u in units:
            table.add_row(
                u.evidence_id,
                u.title[:60],
                str(len(u.text)),
                "✓" if u.metadata.get("sparse_text") else "",
            )
        console.print(table)


@app.command()
def induce(
    evidence: Annotated[Path, typer.Option("--evidence", "-e", help="Path to evidence.json")] = Path("artifacts/evidence.json"),
    output: Annotated[Path, typer.Option("--output", "-o", help="Output raw_concepts.json path")] = Path("artifacts/raw_concepts.json"),
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c", help="Config YAML path")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print prompt for first batch and exit")] = False,
    debug_responses: Annotated[bool, typer.Option("--debug-responses", help="Include raw LLM responses in the output artifact")] = False,
) -> None:
    """Induce candidate concepts from evidence using an LLM."""
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not evidence.exists():
        err_console.print(f"[red]Evidence file not found: {evidence}[/red]")
        err_console.print("Run: poea ingest --input <path> --output artifacts/evidence.json")
        raise typer.Exit(1)

    cfg_path = config_path or (Path("configs/induction_config.yaml"))
    raw_config = _load_config(cfg_path)
    induction_cfg = InductionConfig.from_dict(raw_config)

    with evidence.open(encoding="utf-8") as f:
        raw_units = json.load(f)

    units = [EvidenceUnit.model_validate(u) for u in raw_units]

    if not units:
        err_console.print("[red]No evidence units in input file[/red]")
        raise typer.Exit(1)

    if dry_run:
        from .concepts.prompts import SYSTEM_PROMPT, build_user_message
        batch = units[: induction_cfg.max_records_per_batch]
        console.print("[bold]--- SYSTEM ---[/bold]")
        console.print(SYSTEM_PROMPT)
        console.print("\n[bold]--- USER (first batch) ---[/bold]")
        console.print(build_user_message(batch))
        raise typer.Exit(0)

    console.print(
        f"Inducing concepts from {len(units)} evidence units "
        f"using {induction_cfg.model} "
        f"(batch size {induction_cfg.max_records_per_batch})"
    )

    inducer = ConceptInducer(config=induction_cfg, debug_responses=debug_responses)
    try:
        results = inducer.induce(units)
    except Exception as exc:
        err_console.print(f"[red]Induction failed: {exc}[/red]")
        raise typer.Exit(1)

    all_concepts = [c for r in results for c in r.concepts]
    errors = [r for r in results if r.error]

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "model": induction_cfg.model,
                "evidence_count": len(units),
                "batch_count": len(results),
                "concept_count": len(all_concepts),
                "errors": [{"batch": r.batch_index, "error": r.error} for r in errors],
                "batches": [
                    {
                        "batch": r.batch_index,
                        "evidence_ids": r.evidence_ids,
                        "concept_count": len(r.concepts),
                        "error": r.error,
                        **(
                            {"raw_response": r.raw_response}
                            if debug_responses
                            else {}
                        ),
                    }
                    for r in results
                ],
                "concepts": [c.model_dump() for c in all_concepts],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    console.print(f"[green]{len(all_concepts)} concepts extracted → {output}[/green]")
    if errors:
        console.print(f"[yellow]{len(errors)} batch(es) had errors[/yellow]")
        for e in errors:
            console.print(f"  Batch {e.batch_index}: {e.error}")

    if verbose and all_concepts:
        table = Table("name", "confidence", "evidence_count", "definition")
        for c in sorted(all_concepts, key=lambda x: -x.confidence):
            table.add_row(
                c.name,
                f"{c.confidence:.2f}",
                str(len(c.supporting_evidence_ids)),
                c.definition[:80],
            )
        console.print(table)


@app.command()
def consolidate(
    concepts: Annotated[Path, typer.Option("--concepts", help="Path to raw_concepts.json")] = Path("artifacts/raw_concepts.json"),
    consolidation_map: Annotated[Optional[Path], typer.Option("--consolidation-map", "-m", help="Consolidation map YAML")] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="Directory for output artifacts")] = Path("artifacts"),
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c", help="Config YAML path")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Build concept registry and canonical concept set from raw induction output."""
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not concepts.exists():
        err_console.print(f"[red]Concepts file not found: {concepts}[/red]")
        err_console.print("Run: poea induce --evidence artifacts/evidence.json")
        raise typer.Exit(1)

    cfg_path = config_path or Path("configs/induction_config.yaml")
    raw_config = _load_config(cfg_path)
    concept_cfg = raw_config.get("concepts", {})
    promotion_confidence = concept_cfg.get("promotion_confidence", 0.75)
    min_evidence = concept_cfg.get("min_supporting_evidence", 2)
    max_active_concepts = concept_cfg.get("max_active_concepts", 30)

    cmap_path = consolidation_map or Path("configs/consolidation_map.yaml")
    if not cmap_path.exists():
        console.print(f"[yellow]No consolidation map found at {cmap_path}; running without semantic clusters[/yellow]")
        cmap_path = None

    try:
        metrics = build_registry(
            raw_concepts_path=concepts,
            consolidation_map_path=cmap_path,
            output_dir=output_dir,
            promotion_confidence=promotion_confidence,
            min_evidence=min_evidence,
            max_active=max_active_concepts,
        )
    except Exception as exc:
        err_console.print(f"[red]Registry build failed: {exc}[/red]")
        raise typer.Exit(1)

    console.print("[bold]Registry build complete[/bold]")
    console.print(f"  Raw proposals:             {metrics.raw_proposal_count}")
    console.print(f"  Unique names:              {metrics.unique_names_raw}")
    console.print(f"  Exact duplicates merged:   {metrics.exact_duplicates_merged}")
    console.print(f"  Semantic concepts merged:  {metrics.semantic_concepts_merged}")
    console.print(f"  Rejected:                  {metrics.rejected}")
    console.print(f"  Suppressed (confidence):   {metrics.suppressed_by_confidence}")
    console.print(f"  Suppressed (evidence):     {metrics.suppressed_by_evidence}")
    console.print(f"  Suppressed (cap):          {metrics.suppressed_by_cap}")
    console.print(f"  [green]Active canonical:          {metrics.active_canonical_count}[/green]")
    console.print(f"\n  Promotion threshold:  conf ≥ {metrics.promotion_confidence_threshold}, evidence ≥ {metrics.min_supporting_evidence}, cap {metrics.max_active_concepts}")
    console.print(f"\n  → {output_dir}/concept_registry.json")
    console.print(f"  → {output_dir}/canonical_concepts.json")


@app.command("score-evidence")
def score_evidence(
    concepts: Annotated[
        Path,
        typer.Option("--concepts", "-c", help="Path to canonical_concepts.json (active concepts)"),
    ] = Path("artifacts/canonical_concepts.json"),
    evidence: Annotated[
        Path,
        typer.Option("--evidence", "-e", help="Path to evidence.json"),
    ] = Path("artifacts/evidence.json"),
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output scored_evidence.json path"),
    ] = Path("artifacts/scored_evidence.json"),
    config_path: Annotated[
        Optional[Path],
        typer.Option("--config", help="Config YAML path"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Ignore existing cached scores and re-score everything"),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """
    Score evidence records against active concepts (Assignment Bridge).

    For each evidence record, calls the LLM once with all active concepts
    batched together.  Results are cached in scored_evidence.json; re-runs
    only score new (evidence_id, concept_id) pairs.
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not concepts.exists():
        err_console.print(f"[red]Canonical concepts file not found: {concepts}[/red]")
        err_console.print("Run: poea consolidate --concepts artifacts/raw_concepts.json")
        raise typer.Exit(1)

    if not evidence.exists():
        err_console.print(f"[red]Evidence file not found: {evidence}[/red]")
        err_console.print("Run: poea ingest --input <path> --output artifacts/evidence.json")
        raise typer.Exit(1)

    # Load config
    cfg_path = config_path or Path("configs/induction_config.yaml")
    raw_config = _load_config(cfg_path)
    scoring_cfg = ScoringConfig.from_dict(raw_config)

    # Load active concepts
    with concepts.open(encoding="utf-8") as f:
        concepts_data = json.load(f)
    active_concepts = [
        ConceptEntry.model_validate(c) for c in concepts_data.get("concepts", [])
    ]

    if not active_concepts:
        err_console.print("[red]No active concepts found in concepts file[/red]")
        raise typer.Exit(1)

    # Load evidence records
    with evidence.open(encoding="utf-8") as f:
        raw_units = json.load(f)
    evidence_units = [EvidenceUnit.model_validate(u) for u in raw_units]

    if not evidence_units:
        err_console.print("[red]No evidence records found in evidence file[/red]")
        raise typer.Exit(1)

    # Load existing cache
    existing: list = []
    if not no_cache and output.exists():
        existing = load_scored_evidence(output)
        console.print(f"[dim]Loaded {len(existing)} cached record(s) from {output}[/dim]")

    console.print(
        f"Scoring {len(evidence_units)} evidence records × {len(active_concepts)} concepts "
        f"using {scoring_cfg.model}"
    )

    scorer = EvidenceScorer(config=scoring_cfg)
    try:
        records, stats = scorer.score_all(
            evidence=evidence_units,
            concepts=active_concepts,
            existing_records=existing if existing else None,
        )
    except Exception as exc:
        err_console.print(f"[red]Scoring failed: {exc}[/red]")
        raise typer.Exit(1)

    from datetime import datetime, timezone

    metadata = {
        "canonical_concepts_source": str(concepts),
        "evidence_source": str(evidence),
        "concept_count": len(active_concepts),
        "evidence_count": len(evidence_units),
        "model": scoring_cfg.model,
        "soft_observed_threshold": scoring_cfg.soft_observed_threshold,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }

    save_scored_evidence(output, records, stats, metadata)

    console.print("\n[bold]Scoring complete[/bold]")
    console.print(f"  Total pairs:    {stats.total_pairs}")
    console.print(f"  Scored (LLM):   {stats.scored}")
    console.print(f"  Cache hits:     {stats.cache_hits}")
    console.print(f"  Errors:         {stats.errors}")
    if stats.errors:
        console.print(f"  [yellow]Warning: {stats.errors} record(s) failed scoring — assigned neutral[/yellow]")
    console.print(f"\n  → {output}")

    if verbose and stats.by_concept:
        console.print("\n[bold]Concept assignment summary:[/bold]")
        table = Table("concept", "true", "false", "neutral", "neutral_rate")
        for name in sorted(stats.by_concept):
            bucket = stats.by_concept[name]
            total = bucket["true"] + bucket["false"] + bucket["neutral"]
            neutral_rate = f"{bucket['neutral'] / total:.0%}" if total else "—"
            table.add_row(
                name,
                str(bucket["true"]),
                str(bucket["false"]),
                str(bucket["neutral"]),
                neutral_rate,
            )
        console.print(table)


@app.command("run-backend")
def run_backend(
    backend_name: Annotated[
        str,
        typer.Option("--backend", "-b", help="Backend name (e.g. 'null')"),
    ] = "null",
    concepts: Annotated[
        Path,
        typer.Option("--concepts", "-c", help="Path to canonical_concepts.json"),
    ] = Path("artifacts/canonical_concepts.json"),
    scored_evidence: Annotated[
        Optional[Path],
        typer.Option(
            "--scored-evidence",
            "-s",
            help="Path to scored_evidence.json (optional; uses empty evidence if absent)",
        ),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output graph artifact path"),
    ] = Path("artifacts/poea_graph.json"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """
    Run a structure-learning backend against active concepts and scored evidence.

    Available backends: null (Phase 7).  The 'poe' backend is added in Phase 9.
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not concepts.exists():
        err_console.print(f"[red]Canonical concepts file not found: {concepts}[/red]")
        err_console.print("Run: poea consolidate --concepts artifacts/raw_concepts.json")
        raise typer.Exit(1)

    # Load concepts
    with concepts.open(encoding="utf-8") as f:
        concepts_data = json.load(f)
    active_concepts = concepts_data.get("concepts", [])

    if not active_concepts:
        err_console.print("[red]No active concepts found in concepts file[/red]")
        raise typer.Exit(1)

    # Load scored evidence (optional)
    scored: list = []
    if scored_evidence is not None:
        if not scored_evidence.exists():
            err_console.print(f"[red]Scored evidence file not found: {scored_evidence}[/red]")
            err_console.print("Run: poea score-evidence --concepts ... --evidence ...")
            raise typer.Exit(1)
        records = load_scored_evidence(scored_evidence)
        scored = [r.model_dump() for r in records]
        if verbose:
            console.print(f"[dim]Loaded {len(scored)} scored record(s) from {scored_evidence}[/dim]")
    else:
        console.print("[yellow]No scored evidence provided — running backend with empty evidence[/yellow]")

    # Resolve and invoke backend
    try:
        backend = get_backend(backend_name)
    except ValueError as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    console.print(
        f"Running [bold]{backend_name}[/bold] backend  "
        f"({len(active_concepts)} concept(s), {len(scored)} evidence record(s))"
    )

    try:
        graph = backend.learn_graph(active_concepts, scored)
    except Exception as exc:
        err_console.print(f"[red]Backend learn_graph failed: {exc}[/red]")
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(dict(graph), f, indent=2, ensure_ascii=False)

    console.print("\n[bold]Graph complete[/bold]")
    console.print(f"  Backend:    {graph.get('backend', backend_name)}")
    console.print(f"  Nodes:      {graph.get('node_count', '?')}")
    console.print(f"  Edges:      {graph.get('edge_count', '?')}")
    console.print(f"\n  → {output}")

    if verbose:
        nodes = graph.get("nodes", [])
        if nodes:
            table = Table("name", "prior_probability", "source")
            for node in nodes:
                table.add_row(
                    node.get("name", ""),
                    str(node.get("prior_probability", "")),
                    node.get("source", ""),
                )
            console.print(table)
