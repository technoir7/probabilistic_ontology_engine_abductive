# Next: Phase 12 — Comparative Mode

---

## Objective

Compare POE-A against POE v1 as an empirical diagnostic.

Phase 11 is complete: `poea report --run latest` regenerates
`artifacts/run_report.md` from existing artifacts without live API calls or
pipeline re-execution.

Assignment architecture correction is complete: POE-A now has deterministic,
direct-structured, semantic, and hybrid assignment backends behind
`AssignmentRouter`. Structured domains use deterministic/direct assignment by
default and can reuse old POE deterministic mappers from
`../probabilistic_ontology_engine/src/domains/`. Semantic LLM scoring is opt-in
for explicit prose/unstructured evidence. Art-market ingestion with `--domain art`
marks all article evidence as `prose_text`, routing to semantic scoring.

Semantic scoring optimization is also complete: prompt compaction reduced input
tokens by ~26% per call (~$0.052 per 70-record run). A shadow prefilter reports
would-be-skipped pairs (58-64% of semantic pairs) without actually skipping any
calls. Skipping can be enabled after false-negative validation confirms safety.

---

## Current Baseline

Latest POE-A run artifacts report:

- Evidence records: 70
- Raw concepts: 21
- Active concepts: 11
- Scored concept/evidence pairs: 770
- Scoring errors: 0
- Graph nodes: 11
- Graph edges: 1
- Records included in POE learning: 30
- Records omitted from POE learning: 40
- Neutral assignment rate: 95.1%
- All-neutral scored records: 40

The high neutral rate and POE-learning omission count should be treated as
diagnostics when comparing against POE v1.

The comparison should distinguish assignment mode effects where possible:
deterministically assigned structured evidence is expected to have different
missingness and neutral-rate behavior from prose evidence scored semantically.

---

## Phase 12 Requirements

From `IMPLEMENTATION_PLAN.md`, comparative mode should compare:

```text
POE v1:
manual variables + evidence -> graph

POE-A:
induced variables + scored evidence -> graph
```

The report should identify:

- nodes present only in POE v1
- nodes present only in POE-A
- overlapping or semantically similar nodes
- edge count differences
- hypothesis differences
- surprising POE-A discoveries
- POE-A failure modes

---

## Expected Command

```bash
poea compare \
  --poea-graph artifacts/poea_graph.json \
  --poe-v1-snapshot ../art-market-domain/reports/art_snapshot_weighted.txt \
  --output artifacts/comparison_report.md
```

---

## Exit Criteria

A readable comparison report exists.
