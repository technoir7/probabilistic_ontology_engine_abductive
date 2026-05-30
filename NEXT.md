# Next: Phase 10 — End-to-End Pipeline Command

---

## Objective

Create one command that runs the complete POE-A pipeline from raw evidence to
an ontology graph, without requiring any intermediate manual steps.

The pipeline command is the first demonstration of MVP-0 (Vocabulary-Free
Ontology Construction). It wires together every completed phase.

---

## Prerequisite: MVP-0 Acceptance Test

MVP-0 succeeds when this command runs to completion:

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```

and produces all required artifacts using zero manually specified art ontology
variables.

---

## What Phase 10 Must Produce

### CLI command

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --registry artifacts/poea_registry.sqlite \
  --backend poe \
  --output artifacts/poea_graph.json
```

(Note: `--registry` becomes `--concepts` or `--output-dir` in the JSON architecture.)

### Pipeline steps (from IMPLEMENTATION_PLAN.md Phase 10)

1. Load evidence (text only; discard pre-annotations)
2. Induce concepts
3. Import concepts into registry
4. Consolidate concepts
5. Promote active concepts
6. Score evidence against active concepts
7. Export nodes
8. Run backend
9. Save graph artifact
10. Generate run report

### Required artifacts

```
artifacts/evidence.json
artifacts/raw_concepts.json
artifacts/poea_registry.sqlite  → artifacts/concept_registry.json (JSON arch)
artifacts/nodes.json
artifacts/poea_graph.json
artifacts/run_report.md
```

---

## Implementation Tasks

1. Add `poea pipeline` command to `cli.py`
2. Wire all existing phase commands into a single callable sequence
3. Handle partial runs (skip stages where artifacts already exist unless `--force`)
4. Generate `artifacts/run_report.md` summarizing the pipeline run

---

## Design Notes

### Concept induction requires live LLM

`poea induce` calls the LLM. The pipeline command should:
- Skip induction if `raw_concepts.json` already exists (use `--force` to re-run)
- Skip scoring if `scored_evidence.json` already exists (use `--force` to re-score)

This allows the pipeline to be re-run cheaply after concept registry changes.

### Null backend for testing

The pipeline should work with `--backend null` so the full pipeline can be tested
without POE installation (and without live scored evidence for the null backend path).

### Run report

The run report must include (per IMPLEMENTATION_PLAN.md Phase 11 preview):
- Evidence records loaded
- Concepts proposed
- Concepts merged / active / suppressed
- Evidence scoring summary (if scoring ran)
- Backend used
- Graph summary (nodes, edges)
- Warnings
- Timestamps

---

## Exit Criteria (from IMPLEMENTATION_PLAN.md Phase 10)

One command produces a graph from raw evidence without hand-authored variables.

All required artifacts are present after the command completes.
