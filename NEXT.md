# Next: Phase 11 — Run Reports

---

## Objective

Make pipeline behavior inspectable after every run.

Phase 10 now writes a basic `artifacts/run_report.md` as part of `poea pipeline`.
Phase 11 should turn that report into a first-class reporting capability with
deeper audit detail and a dedicated report command.

---

## Current Baseline

Implemented in Phase 10:

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```

The command produced:

```text
artifacts/evidence.json
artifacts/raw_concepts.json
artifacts/concept_registry.json
artifacts/canonical_concepts.json
artifacts/scored_evidence.json
artifacts/nodes.json
artifacts/poea_graph.json
artifacts/run_report.md
```

Latest run summary:

- Evidence records: 70
- Raw concepts: 21
- Active concepts: 11
- Scored concept/evidence pairs: 770
- Scoring errors: 0
- Graph nodes: 11
- Graph edges: 1

---

## Phase 11 Requirements

From `IMPLEMENTATION_PLAN.md`, run reports should include:

- evidence records loaded
- concepts proposed
- concepts merged
- active concepts selected
- dropped concepts
- evidence scoring summary
- assignments per concept
- neutral rate
- sample scorer outputs for spot-checking scorer accuracy
- backend used
- graph summary
- warnings
- configuration
- model used
- timestamps

---

## Implementation Tasks

1. Add a dedicated command:

```bash
poea report --run latest
```

2. Expand report generation beyond the Phase 10 baseline:

- Include concept-level scoring table from `scored_evidence.json`.
- Include sample scored evidence records.
- Include active, suppressed, rejected, and merged concept counts.
- Include backend candidate summaries when present in the graph artifact.
- Include report inputs and artifact modification timestamps.

3. Keep reports read-only.

The report command should inspect existing artifacts. It must not re-run
induction, scoring, consolidation, or backend learning.

4. Add tests for:

- report generation from complete artifacts
- report generation when optional artifacts are missing
- neutral-rate calculation
- sample scorer-output rendering

---

## Exit Criteria

Every pipeline run leaves an auditable trail, and `poea report --run latest`
can regenerate or refresh the report from existing artifacts without live API
calls.
