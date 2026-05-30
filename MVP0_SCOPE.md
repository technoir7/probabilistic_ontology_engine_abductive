# MVP-0: Vocabulary-Free Ontology Construction

**Version:** 1.0
**Date:** 2026-05-30

---

## Definition

MVP-0 is the smallest version of POE-A that satisfies the primary success criterion:

> Construct an ontology graph from evidence without requiring a human-specified domain vocabulary.

MVP-0 is complete when the following command produces valid outputs:

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --registry artifacts/poea_registry.sqlite \
  --backend poe \
  --output artifacts/poea_graph.json
```

and the run uses zero manually supplied art ontology variables.

---

## Acceptance Criteria

All of the following must be true for MVP-0 to be accepted:

1. **No hand-authored domain vocabulary.** The system receives no list of art market variables as input. The only inputs are raw text evidence files and general-purpose configuration (thresholds, model names, batch sizes).

2. **Induced concepts are plausible.** A human reviewer can read the registry and confirm that the active concepts represent recognizable explanatory constructs present in the evidence. Perfection is not required; the concepts must not be obviously hallucinated or trivially generic (e.g., "Art," "Market," "Value").

3. **The registry persists and is auditable.** The SQLite registry records every concept, every status transition, and the induction run that produced each concept. No concept is silently deleted.

4. **The graph is produced.** `artifacts/poea_graph.json` exists and contains a non-trivial structure (more than two nodes, at least one edge). The quality of the graph at MVP-0 is not evaluated — only its existence.

5. **A run report exists.** `artifacts/run_report.md` documents the evidence loaded, concepts proposed, concepts merged, concepts promoted, the backend used, and the model used.

6. **Tests pass with null backend.** `pytest` (no LLM calls) passes. The full pipeline runs end-to-end with the null backend in CI.

---

## What Is In MVP-0

### Evidence Ingestion

- Load JSON files from a directory (the art evidence split format)
- Extract raw text fields only: `title`, `notes`, document text content
- **Explicitly discard** `assignments` and `causal_claims` fields — these are pre-existing POE v1 annotations and must not inform concept induction
- Assign stable `evidence_id` to each record (deterministic hash of source + title)
- Produce `artifacts/evidence.json`

### Concept Induction

- Batch evidence records (configurable batch size, default 20-40 per batch)
- For each batch: call LLM with a structured induction prompt
- Prompt instructs the LLM to identify recurring, explanatory, causally relevant concepts
- Prompt explicitly prohibits returning the pre-existing variable list
- Capture: concept name, definition, confidence score, supporting evidence IDs
- Produce `artifacts/raw_concepts.json`

**MVP concept schema (minimal):**

```json
{
  "name": "string",
  "definition": "string",
  "confidence": 0.0,
  "supporting_evidence_ids": []
}
```

`epistemic_role`, `direction`, and `frequency` are excluded from MVP-0. They can be added as an enrichment pass in a later phase without changing the core pipeline.

### Concept Consolidation

- Pass 1: Exact and normalized name matching (lowercase, strip punctuation)
- Pass 2: LLM-assisted merge comparison for near-duplicates
- Merge policy: retain clearer name, combine supporting evidence, mark loser as `merged_into`
- Record every merge as a `concept_event`
- Produce deduplicated candidate concept set

Embedding similarity is optional and off by default at MVP-0. It can be enabled via config if the two-pass approach proves insufficient.

### Concept Registry

- SQLite database with four tables: `concepts`, `induction_runs`, `concept_evidence_links`, `concept_events`
- All concepts enter as `candidate`
- Never delete. Never silently overwrite.
- CLI commands: `registry init`, `registry import`, `registry list`, `registry diff`

### Active Concept Selection (Auto-Promotion)

- Promote `candidate → active` if:
  - `confidence >= 0.55` (configurable)
  - supported by at least 2 evidence records
  - not merged into another concept
  - not rejected
- Auto-promotion is permitted in MVP-0 because MVP-0 must run without human intervention
- Every auto-promotion is recorded as a `concept_event` with the promotion criteria met
- Configurable threshold allows human-calibrated tightening without code changes

### Evidence Scoring (New — Not in Original Plan)

This is the critical missing step identified in ARCHITECTURE_REVIEW.md Finding 1.

- For each active concept and each evidence record, determine whether the evidence supports the concept being True or False
- Method: LLM call with a structured scoring prompt: "Given this concept definition and this evidence text, does the evidence support this concept? Answer: supports_true, supports_false, or neutral."
- Produce `ObservedAssignment` entries (concept_id → True/False/neutral) for each evidence record
- Output: a list of POE-compatible evidence records with concept-keyed assignments
- Neutral assignments may be excluded from the POE evidence record (missing data is handled by POE's `MISSING` missingness type)

Evidence scoring is in the critical path. It runs after active concept selection and before the POE adapter.

### Concept-to-Node Translation

- Export active concepts as a `nodes.json` artifact
- Each node: `name`, `definition`, `prior_probability: 0.5`, `source: poea_induced`
- No hardcoded art variables
- Produce `artifacts/nodes.json`

### POE Adapter (Concept-Driven Domain Module)

- Translate active concepts into POE `Variable` objects (BOOLEAN type, `[True, False]` support)
- Generate stable variable UUIDs using `stable_variable_id(domain_id, concept_name)` (POE's own deterministic hash function)
- Build a seed `OntologyCandidate` with all active concepts as variables and all-pairs directed edges as the initial topology
- Construct a dynamic domain module wrapping the induced variables and candidate
- Translate scored evidence records into POE `EvidenceRecord` objects
- Call `engine.register_domain()`, `engine.activate_domain()`, `engine.ingest_batch()`, `engine.learn()`
- Return a graph artifact serialized from the dominant candidate

### End-to-End Pipeline Command

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --registry artifacts/poea_registry.sqlite \
  --backend poe \
  --output artifacts/poea_graph.json
```

Pipeline steps in order:
1. Load and normalize evidence → `evidence.json`
2. Induce concepts → `raw_concepts.json`
3. Import concepts into registry
4. Consolidate concepts
5. Promote active concepts
6. Score evidence against active concepts
7. Export nodes → `nodes.json`
8. Run POE backend → `poea_graph.json`
9. Generate run report → `run_report.md`

### Null Backend

- Accepts concepts and evidence records
- Returns a trivial graph artifact with one node per concept and no edges
- Used for all CI tests; never calls POE

### Run Report

- Human-readable Markdown
- Contents: evidence loaded (count), concepts proposed, merged, dropped, promoted, backend used, model used, timestamps, config values, warnings

---

## What Is Explicitly Excluded from MVP-0

### Latent Validation (PCA / ICA)

Statistical grounding of concepts against latent factors is deferred to Phase 12. Adding it to MVP-0 would require:
- Embedding all evidence documents
- Running dimensionality reduction over the embedding matrix
- Implementing concept-to-factor alignment scoring

This is substantial additional complexity that does not affect whether the core pipeline produces a graph. Defer entirely.

### Comparison Mode

Running POE v1 alongside POE-A and comparing outputs is a diagnostic tool, not a capability. It has no role in MVP-0. Add after the first successful end-to-end run.

### Hypothesis and Mechanism Generation

Generating candidate causal mechanisms (e.g., "A → B → C") is Phase 14. It requires a working graph as input. Defer until after MVP-0 is validated.

### Autonomous Recurring Runs / Scheduling

Trigger-based scheduling (new evidence threshold, weekly cadence, entropy triggers) is Phase 15. MVP-0 is a one-shot command. Scheduling can be added via cron or a loop layer after the pipeline itself works reliably.

### Multi-Domain Generality

MVP-0 targets the art domain. No cross-domain registry merging, no domain namespacing beyond `domain_tag`, no multi-domain pipeline orchestration.

### Sparse Autoencoders

Optional future latent extraction method. Not relevant until Phase 12+.

### Advanced Registry Governance

Human review workflows, approval queues, merge audit UIs. The registry records everything needed to build these later. MVP-0 does not implement them.

### `epistemic_role`, `direction`, `frequency` Concept Fields

These fields add prompt complexity without affecting the MVP pipeline. Deferred to a post-MVP enrichment pass.

### Tiered Multi-Model LLM Routing

The configuration specifies three model tiers (induction, prototype, prefilter). MVP-0 uses a single configurable model for all LLM calls. Multi-tier routing is a cost optimization for later.

---

## MVP-0 Deliverables

| Artifact | Description |
|----------|-------------|
| `artifacts/evidence.json` | Normalized evidence records (text only) |
| `artifacts/raw_concepts.json` | Raw concept proposals from LLM |
| `artifacts/poea_registry.sqlite` | Versioned concept registry |
| `artifacts/nodes.json` | Active concepts as POE-compatible nodes |
| `artifacts/poea_graph.json` | Ontology graph from POE backend |
| `artifacts/run_report.md` | Human-readable audit of the run |

---

## Definition of "Done"

MVP-0 is done when a developer who did not write the code can run:

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```

and produce all six artifacts listed above, having supplied no art market variable names anywhere in the process.
