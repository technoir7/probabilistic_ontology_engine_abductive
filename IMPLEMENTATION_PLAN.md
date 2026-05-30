# POE-A IMPLEMENTATION PLAN

## Project

**Probabilistic Ontology Engine Abductive**

Short name:

```text
POE-A
```

Repository name:

```text
probabilistic_ontology_engine_abductive
```

---

# Mission

POE-A exists to remove the fixed vocabulary assumption from POE.

The primary goal is not to outperform POE v1 immediately.

The primary goal is to make ontology construction epistemically cleaner by ensuring that both the vocabulary and the structure are derived from evidence.

POE v1 learns relations over a human-specified concept set.

POE-A learns the concept set and then learns relations over it.

This matters even if early POE-A graphs are noisier than POE v1 graphs, because the point is to eliminate a major a priori intervention.

---

# Core Principle

The implementation order does not need to mirror the final architecture.

The final architecture may include:

```text
Evidence
    ↓
Latent Extraction       ← post-MVP
    ↓
Abductive Concept Discovery
    ↓
Cross Validation        ← post-MVP
    ↓
Concept Registry
    ↓
Evidence Scoring (Assignment Bridge)
    ↓
Structure Learning
    ↓
Ontology Graph
```

But the build order should minimize risk and produce working vertical slices quickly.

The first target is:

```text
Evidence
    ↓
Abductive Concept Discovery
    ↓
Concept Registry
    ↓
Evidence Scoring (Assignment Bridge)
    ↓
POE Structure Learning
    ↓
Ontology Graph
```

without hand-authored domain variables.

---

# Primary Success Criterion

POE-A succeeds when it can construct an ontology graph without requiring a human-specified variable vocabulary.

In other words:

```text
No prewritten art ontology variables.
No hand-authored domain node list.
No fixed vocabulary supplied before evidence ingestion.
```

The system may use general-purpose prompts, schemas, thresholds, and infrastructure.

It may not use a manually designed domain-specific variable list.

---

# Secondary Success Criteria

After the first end-to-end system works, evaluate whether POE-A improves on POE v1.

Secondary metrics:

* Concept novelty
* Concept stability
* Graph usefulness
* Causal claim quality
* Hypothesis quality
* Predictive usefulness
* Reduction of designer bias
* Ability to discover concepts absent from the original ontology

These are important, but they are not Phase 1 blockers.

---

# Architectural Target

POE-A should eventually implement this full pipeline:

```text
Raw Evidence
    ↓
Evidence Normalization
    ↓
Abductive Concept Discovery
    ↓
Concept Consolidation
    ↓
Concept Registry
    ↓
Latent / Statistical Validation   ← post-MVP
    ↓
Evidence Scoring (Assignment Bridge)
    ↓
Concept-to-Node Translation
    ↓
POE Structure Learning Backend
    ↓
Ontology Graph
    ↓
Hypothesis Competition
```

The existing POE is treated as a structure-learning backend.

POE-A owns the vocabulary-generation and evidence-scoring layers.

---

# Relationship to POE

POE v1:

```text
Human-specified variables
    ↓
Structure learning
    ↓
Ontology graph
```

POE-A:

```text
Evidence
    ↓
Abductively generated concepts
    ↓
Evidence scoring (assignment bridge)
    ↓
Structure learning
    ↓
Ontology graph
```

POE-A may initially import POE through an editable local install:

```bash
pip install -e ../probabilistic_ontology_engine
```

This does not clone POE into the new repo.

It simply allows POE-A to call POE as a local package.

No POE code should be copied into POE-A.

---

# Repository Layout

Create:

```text
probabilistic_ontology_engine_abductive/
```

Initial structure:

```text
probabilistic_ontology_engine_abductive/
  README.md
  SPEC.md
  IMPLEMENTATION_PLAN.md
  pyproject.toml

  src/
    poea/
      __init__.py

      cli.py

      evidence/
        __init__.py
        loaders.py
        normalizer.py
        schemas.py

      concepts/
        __init__.py
        inducer.py
        prompts.py
        consolidation.py
        scorer.py        ← evidence-to-assignment bridge
        schemas.py

      registry/
        __init__.py
        store.py
        diff.py
        lifecycle.py
        migrations.py

      validation/        ← post-MVP; do not create until Phase 13
        __init__.py
        latent.py
        alignment.py
        pruning.py

      backends/
        __init__.py
        interface.py
        null_backend.py
        poe_backend.py

      artifacts/
        __init__.py
        exporters.py
        reports.py

  configs/
    induction_config.yaml

  migrations/
    001_registry.sql
    002_induction_runs.sql
    003_latent_factors.sql

  tests/
    test_evidence_loader.py
    test_concept_inducer.py
    test_consolidation.py
    test_scorer.py
    test_registry.py
    test_backend_interface.py
    test_poe_adapter.py
    test_cli.py

  examples/
    art_sample/
```

---

# Phase 0: Bootstrap Repository

## Goal

Create a working Python project skeleton.

## Tasks

Initialize repo:

```bash
mkdir probabilistic_ontology_engine_abductive
cd probabilistic_ontology_engine_abductive
git init
uv init
```

Add dependencies:

```bash
uv add pydantic typer rich sqlite-utils anthropic
uv add --dev pytest ruff mypy
```

Optional later:

```bash
uv add numpy scikit-learn sentence-transformers
```

Do not add LLM provider dependencies beyond `anthropic` until needed. The `anthropic` SDK is the default provider for all LLM calls.

## Deliverables

* `README.md`
* `SPEC.md`
* `IMPLEMENTATION_PLAN.md`
* working package under `src/poea`
* basic CLI entrypoint
* pytest configured
* ruff configured

## Exit Criteria

```bash
pytest
ruff check .
```

both pass.

No POE dependency yet.

---

# Phase 1: Evidence Loader

## Goal

Load existing evidence records into a standard POE-A evidence format.

This phase should support the art-domain evidence records first.

## Input

Existing evidence files, such as:

```text
art-market-domain/data/manual_ingest_split/
```

## Standard Evidence Schema

```json
{
  "evidence_id": "string",
  "source": "string",
  "title": "string",
  "published_at": "iso8601 | null",
  "domain_tag": "string",
  "text": "string",
  "metadata": {}
}
```

## Critical Constraint: Discard Pre-Existing Annotations

The art evidence format contains `assignments` and `causal_claims` fields that encode an external domain vocabulary (POE v1 art ontology variables).

The normalizer must discard these fields entirely.

Only raw text fields — `title`, `notes`, text content — pass to downstream stages.

Reading `assignments` or `causal_claims` would give POE-A access to the vocabulary it is supposed to discover, violating the project's primary success criterion.

This constraint must be enforced in code and verified in tests.

## Tasks

Implement:

```text
src/poea/evidence/loaders.py
src/poea/evidence/schemas.py
src/poea/evidence/normalizer.py
```

Support:

* JSON files
* JSON arrays
* directories of JSON files
* existing art evidence format (text fields only)

CLI:

```bash
poea ingest --input ../art-market-domain/data/manual_ingest_split --domain art --output artifacts/evidence.json
```

## Deliverable

A normalized evidence artifact:

```text
artifacts/evidence.json
```

## Exit Criteria

* At least 50 art evidence records load successfully
* Each record receives a stable `evidence_id`
* `assignments` and `causal_claims` fields are absent from normalized output
* Tests verify the annotation-stripping behavior explicitly
* No concept induction yet
* No POE integration yet

---

# Phase 2: Abductive Concept Discovery MVP

## Goal

Generate candidate concepts directly from evidence.

This is the first core POE-A capability.

## Important Constraint

No hand-authored domain variable list may be supplied.

The prompt may describe what a good concept is.

The prompt may not provide the desired art ontology variables.

## Pipeline

```text
Evidence
    ↓
Batching
    ↓
LLM concept proposal
    ↓
Raw concept list
```

## MVP Concept Schema

```json
{
  "name": "string",
  "definition": "string",
  "confidence": 0.0,
  "supporting_evidence_ids": []
}
```

The following fields are post-MVP enrichment and must not be required for MVP-0. They are added in a separate enrichment pass after the end-to-end pipeline is working:

* `epistemic_role` — causal position (driver / outcome / mediator / context / unknown)
* `direction` — signal directionality (positive_signal / negative_signal / bidirectional / unknown)
* `frequency` — temporal pattern (persistent / episodic / shock / unknown)

Including these fields in the MVP induction prompt increases hallucination risk and prompt complexity without affecting the core pipeline. Defer them.

## Tasks

Implement:

```text
src/poea/concepts/inducer.py
src/poea/concepts/prompts.py
src/poea/concepts/schemas.py
```

CLI:

```bash
poea induce --evidence artifacts/evidence.json --output artifacts/raw_concepts.json
```

## Prompt Requirements

The LLM should be instructed to identify concepts that are:

* recurring
* explanatory
* causally relevant (mechanism variables, not topic labels)
* observable or inferable
* distinct from one another
* grounded in multiple evidence records where possible

The LLM should avoid:

* generic domain labels (e.g., "ArtMarket", "GallerySales")
* article topics
* proper nouns unless they represent reusable mechanisms
* vague abstractions
* synonyms of existing proposals inside the same batch

## Deliverable

```text
artifacts/raw_concepts.json
```

## Exit Criteria

The system produces plausible concepts from evidence without receiving a prewritten domain vocabulary.

This phase is successful even if concepts are noisy.

The point is to prove the system can create a vocabulary from evidence.

---

# Phase 3: Concept Registry MVP

## Goal

Persist induced concepts in a versioned registry.

The registry is the central artifact of POE-A.

## Registry Tables

Minimum tables:

```text
concepts
induction_runs
concept_evidence_links
concept_events
```

## Concept Statuses

```text
candidate
active
deprecated
merged_into
rejected
```

## Initial Policy

For MVP, all induced concepts enter as:

```text
candidate
```

Later automation may promote candidates to active.

## SQL Schema

```sql
CREATE TABLE concepts (
  concept_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  definition TEXT NOT NULL,
  epistemic_role TEXT,
  direction TEXT,
  frequency TEXT,
  llm_confidence REAL,
  grounded INTEGER DEFAULT 0,
  status TEXT DEFAULT 'candidate',
  merged_into TEXT,
  induction_run_id TEXT,
  domain_tag TEXT,
  schema_version INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  deprecated_at TEXT
);

CREATE TABLE induction_runs (
  induction_run_id TEXT PRIMARY KEY,
  domain_tag TEXT,
  input_artifact TEXT,
  model TEXT,
  config_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE concept_evidence_links (
  concept_id TEXT,
  evidence_id TEXT,
  support_strength REAL,
  assigned_value INTEGER,   -- 1=True, 0=False, NULL=neutral/unscored
  scoring_confidence REAL,
  PRIMARY KEY (concept_id, evidence_id)
);

CREATE TABLE concept_events (
  event_id TEXT PRIMARY KEY,
  concept_id TEXT,
  event_type TEXT,
  event_payload_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Tasks

Implement:

```text
src/poea/registry/store.py
src/poea/registry/lifecycle.py
src/poea/registry/diff.py
```

CLI:

```bash
poea registry init --db artifacts/poea_registry.sqlite
poea registry import --db artifacts/poea_registry.sqlite --concepts artifacts/raw_concepts.json
poea registry list --db artifacts/poea_registry.sqlite
poea registry diff --db artifacts/poea_registry.sqlite
```

## Deliverable

```text
artifacts/poea_registry.sqlite
```

## Exit Criteria

* Raw concepts can be imported
* Concepts persist across runs
* Registry can list concepts
* Registry records induction run metadata
* Concepts are not deleted when changed

---

# Phase 4: Concept Consolidation

## Goal

Prevent uncontrolled concept proliferation.

Without consolidation, abductive discovery will generate too many near-duplicates.

## Pipeline

```text
Raw Concepts
    ↓
Similarity Detection
    ↓
Merge Candidates
    ↓
Canonical Concepts
```

## Tasks

Implement:

```text
src/poea/concepts/consolidation.py
```

Methods:

* Pass 1: exact and normalized name matching (lowercase, strip punctuation)
* Pass 2: LLM-assisted merge comparison for concepts not resolved by Pass 1
* At the start of each induction pass, load existing registry concepts for cross-run deduplication

Embedding similarity is optional and off by default. Enable via config if the two-pass approach proves insufficient.

## Merge Policy

If two concepts are semantically equivalent:

* keep the clearer name
* synthesize a unified definition from both (do not just take the winner's)
* merge supporting evidence
* preserve the losing concept as `merged_into`
* record merge event

## CLI

```bash
poea consolidate --db artifacts/poea_registry.sqlite
```

## Deliverable

Registry with deduplicated candidate concepts.

## Exit Criteria

* obvious duplicates merge
* merge history preserved
* concept count becomes manageable
* no silent deletion

---

# Phase 5: Active Concept Selection

## Goal

Produce a usable concept set for structure learning.

Since POE-A is meant to operate without human-authored variables, the system must be able to select active concepts automatically.

## Auto-Promotion Policy

Auto-promotion is permitted in autonomous pipeline execution.

This is consistent with the primary success criterion: the system must run end-to-end without human input.

Auto-promotion is governed by the following constraints:

* Every promotion is recorded as a `concept_event` with the threshold values that triggered it
* All thresholds are configurable — nothing is hardcoded
* Promoted concepts may be manually demoted or rejected at any time
* A hard cap on active concept count (configurable, default 30) prevents uncontrolled vocabulary growth

In human-governed deployments, auto-promotion may be disabled. Operators review candidate concepts and manually promote. The registry mechanics are identical; only the trigger differs.

## Initial Promotion Rules

Promote `candidate` → `active` if:

* confidence >= configured threshold
* has supporting evidence
* not merged into another concept
* not rejected
* passes minimum distinctness checks

Default thresholds:

```yaml
promotion:
  min_confidence: 0.55
  min_supporting_evidence: 2
  max_active_concepts: 30
```

These are provisional and should be configurable.

## Tasks

Implement:

```text
src/poea/registry/lifecycle.py
```

CLI:

```bash
poea registry promote --db artifacts/poea_registry.sqlite --auto
```

## Deliverable

Registry containing active induced concepts.

## Exit Criteria

The active concept set is produced without human-authored domain variables.

Manual review may be performed, but it is not required for the pipeline to run.

---

# Phase 6: Evidence Scoring (Assignment Bridge)

## Goal

Translate normalized evidence records into concept-keyed boolean assignments.

This is the critical link between the concept registry and structure-learning backends.

Structure-learning systems (including POE) do not accept raw text. They require evidence to be expressed as assignments of observed values to specific variables. This stage produces those assignments.

## Why This Phase Exists

This phase was absent from earlier versions of the implementation plan and identified as a critical missing step in the architecture review.

Without evidence scoring, the POE adapter has no valid evidence records to pass to POE. POE would receive empty or fabricated assignments, producing a graph that reflects nothing in the evidence.

This phase must complete before the POE adapter can be built.

## Pipeline

```text
Active Concept Set (from registry)
    +
Normalized Evidence Records
    ↓
LLM scoring per (evidence, concept) pair
    ↓
Concept Assignments per Evidence Record
    ↓
POE-compatible Evidence Records
```

## Scoring Method

For each evidence record, call the LLM with all active concepts batched in a single call:

* Provide: the evidence text and the list of concept definitions
* Receive: for each concept, one of `supports_true`, `supports_false`, `neutral`

Batch scoring (all concepts for one evidence record in one call) reduces API cost compared to per-pair calls.

## Assignment Schema

```json
{
  "evidence_id": "string",
  "assignments": [
    {
      "concept_id": "string",
      "variable_name": "string",
      "assigned_value": true,
      "confidence": 0.81,
      "missingness": "OBSERVED | SOFT_OBSERVED | MISSING"
    }
  ]
}
```

Mapping:

* `supports_true` → `assigned_value: true`, `missingness: OBSERVED`
* `supports_false` → `assigned_value: false`, `missingness: OBSERVED`
* `neutral` → `assigned_value: null`, `missingness: MISSING`
* Low confidence → `missingness: SOFT_OBSERVED`

## Caching

Store scoring results in `concept_evidence_links` (adding `assigned_value` and `scoring_confidence` columns). Do not re-score on re-runs. Cache hits are the default path.

## Tasks

Implement:

```text
src/poea/concepts/scorer.py
```

CLI:

```bash
poea score-evidence --db artifacts/poea_registry.sqlite --evidence artifacts/evidence.json
```

## Exit Criteria

* Every active concept receives an assignment for every evidence record
* Neutral assignments map to `MISSING` missingness type
* Scores are stored in `concept_evidence_links` and not recomputed on re-run
* Run report includes a sample of scorer outputs for auditability

---

# Phase 7: Backend Interface

## Goal

Define the contract between POE-A and structure-learning systems.

POE-A should not hardwire itself to POE internals.

## Interface

Create:

```text
src/poea/backends/interface.py
```

```python
from typing import Any, Mapping, Protocol, Sequence


class StructureLearningBackend(Protocol):
    def learn_graph(
        self,
        concepts: Sequence[Mapping[str, Any]],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        ...

    def score_hypotheses(
        self,
        graph: Mapping[str, Any],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        ...
```

Note: the parameter is `scored_evidence`, not `evidence`. Backends receive pre-scored assignments, not raw text.

## Null Backend

Implement:

```text
src/poea/backends/null_backend.py
```

The null backend should:

* accept concepts
* accept scored evidence
* return a trivial graph artifact (one node per concept, no edges)
* allow CLI testing without POE

## Exit Criteria

Backend interface works independently of POE.

---

# Phase 8: Concept-to-Node Translation

## Goal

Translate induced concepts into POE-compatible nodes.

In POE-A:

```text
concept
    ↓
node representation
    ↓
structure learning
```

## Node Artifact

Create export format:

```json
{
  "domain_tag": "art",
  "nodes": [
    {
      "name": "AuthenticityPremium",
      "definition": "...",
      "prior_probability": 0.5,
      "boolean_state": null,
      "source": "poea_induced"
    }
  ]
}
```

## Tasks

Implement:

```text
src/poea/artifacts/exporters.py
```

CLI:

```bash
poea export-nodes --db artifacts/poea_registry.sqlite --output artifacts/nodes.json
```

## Default Priors

For MVP:

```text
prior_probability = 0.5
boolean_state = null
```

Rationale:

The first induced node state should begin at maximum uncertainty unless evidence activation is implemented.

## Exit Criteria

Active concepts export as nodes.

No hardcoded art variables.

---

# Phase 9: POE Adapter

## Goal

Connect POE-A to the existing POE structure learner.

## Dependency

Install POE locally:

```bash
pip install -e ../probabilistic_ontology_engine
```

## Adapter File

```text
src/poea/backends/poe_backend.py
```

## Responsibilities

The adapter should:

* Build `Variable` objects from active concepts using POE's `stable_variable_id(domain_id, concept_name)` for deterministic UUIDs — never `uuid4()`
* Build a seed `OntologyCandidate` with co-occurrence-seeded edges (not all-pairs; seed only edges where both concepts appeared in the same evidence record)
* Construct a dynamic domain module wrapping the induced variables and candidate
* Translate scored evidence assignments into POE `EvidenceRecord` objects with `ObservedAssignment` entries keyed to stable variable UUIDs
* Register and activate the dynamic domain module with POE
* Call `engine.learn()` and return a graph artifact

## Variable UUID Stability

Variable UUIDs must be derived deterministically from concept names.

Use:

```python
from engine.variable_identity import stable_variable_id
variable_id = stable_variable_id(domain_id, concept_name)
```

Never use `uuid4()` for variable UUIDs. Random UUIDs break POE's historical evidence matching on restart.

## Anti-Goals

Do not:

* copy POE code
* fork POE inside POE-A
* import POE internals beyond: `engine.engine`, `engine.schemas`, `engine.variable_identity`
* modify POE during this phase
* make POE-A dependent on art-domain specifics

## CLI

```bash
poea run-backend \
  --backend poe \
  --db artifacts/poea_registry.sqlite \
  --evidence artifacts/evidence.json \
  --output artifacts/poea_graph.json
```

## Exit Criteria

POE-A runs end-to-end:

```text
Evidence
    ↓
Concept Discovery
    ↓
Concept Registry
    ↓
Evidence Scoring (Assignment Bridge)
    ↓
POE Adapter
    ↓
Ontology Graph
```

without a manually specified variable list.

This is the first major project victory.

---

# Phase 10: End-to-End Pipeline Command

## Goal

Create one command that runs the whole system.

## CLI

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --registry artifacts/poea_registry.sqlite \
  --backend poe \
  --output artifacts/poea_graph.json
```

## Pipeline Steps

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

## Deliverables

```text
artifacts/evidence.json
artifacts/raw_concepts.json
artifacts/poea_registry.sqlite
artifacts/nodes.json
artifacts/poea_graph.json
artifacts/run_report.md
```

## Exit Criteria

One command produces a graph from raw evidence without hand-authored variables.

---

# Phase 11: Run Reports

## Goal

Make system behavior inspectable.

Even if POE-A is autonomous, it must be auditable.

## Report Should Include

* evidence records loaded
* concepts proposed
* concepts merged
* active concepts selected
* dropped concepts
* evidence scoring summary (assignments per concept, neutral rate)
* sample of scorer outputs (for spot-checking scorer accuracy)
* backend used
* graph summary
* warnings
* configuration
* model used
* timestamps

## CLI

```bash
poea report --run latest
```

## Deliverable

```text
artifacts/run_report.md
```

## Exit Criteria

Every pipeline run leaves an auditable trail.

---

# Phase 12: Comparative Mode

## Goal

Compare POE-A against POE v1, not as the primary justification, but as an empirical diagnostic.

## Comparison

Run:

```text
POE v1:
manual variables + evidence → graph

POE-A:
evidence → induced concepts → evidence scoring → graph
```

Compare:

* node overlap
* new concepts
* missing concepts
* graph density
* causal edge differences
* hypothesis differences
* stability across repeated runs

## CLI

```bash
poea compare \
  --poe-v1-snapshot ../art-market-domain/reports/art_snapshot_weighted.txt \
  --poea-graph artifacts/poea_graph.json \
  --output artifacts/comparison_report.md
```

## Exit Criteria

A readable comparison report exists.

This does not determine whether POE-A is valid.

It helps diagnose what changed.

---

# Phase 13: Latent Validation Layer (Post-MVP)

**This phase is post-MVP.** It must not block MVP-0 or any phase in the critical path.

## Goal

Add statistical grounding after the end-to-end abductive pipeline works.

## Methods

Implement:

* PCA over evidence embeddings
* ICA over evidence embeddings

Note: the primary evidence is text, not numeric time series. Latent extraction over text requires embedding each document first (using a sentence transformer or similar), then running dimensionality reduction over the embedding matrix. This is different from PCA over market time series.

Optional future methods:

* Sparse autoencoders
* NMF

## Tasks

Implement:

```text
src/poea/validation/latent.py
src/poea/validation/alignment.py
```

Do not create the `validation/` directory until this phase begins.

## Output

For each concept:

```json
{
  "concept_id": "...",
  "factor_alignment_id": 3,
  "alignment_strength": 0.42,
  "grounded": true
}
```

## Important Principle

Latent validation is a check, not the source of truth.

A concept may be retained even if it lacks latent support, especially if it is semantic, textual, or institutional.

## Exit Criteria

Concepts receive grounding metrics.

Registry stores latent alignment.

---

# Phase 14: Pruning and Stability (Post-MVP)

**This phase is post-MVP.**

## Goal

Improve long-run autonomous behavior.

## Add

* cross-run stability metrics
* automatic deprecation candidates
* low-support concept pruning
* concept drift detection
* unstable concept flags

## Metrics

Track:

* recurrence across runs
* name stability
* definition stability
* support stability
* graph usefulness
* merge frequency

## Exit Criteria

POE-A can run repeatedly without uncontrolled vocabulary explosion.

---

# Phase 15: Hypothesis and Mechanism Generation (Post-MVP)

**This phase is post-MVP.**

## Goal

Extend abductive generation from concepts to mechanisms.

Instead of only generating nodes, POE-A should eventually generate possible causal mechanisms.

Example:

```text
AIImageSaturation
    ↓
AntiDigitalSentiment
    ↓
CraftPrestigeRising
```

## Output

```json
{
  "mechanism_name": "AIAuthenticityBacklash",
  "claims": [
    {
      "cause": "AIImageSaturation",
      "effect": "AuthenticityPremium",
      "polarity": "positive",
      "confidence": 0.73
    }
  ]
}
```

## Exit Criteria

POE-A proposes candidate causal mechanisms before structure learning confirms or rejects them.

---

# Phase 16: Autonomous Recurring Runs (Post-MVP)

**This phase is post-MVP.**

## Goal

Enable POE-A to operate as a continuous ontology-growth system.

## Triggers

* new evidence exceeds threshold
* weekly run
* high graph entropy
* major hypothesis shift
* large concept drift

## Output

* updated registry
* updated graph
* updated reports
* concept lifecycle changes

## Exit Criteria

POE-A can maintain an evolving ontology from incoming evidence.

---

# Configuration

Create:

```text
configs/induction_config.yaml
```

Initial config:

```yaml
models:
  induction: claude-sonnet-4-6
  scoring: claude-haiku-4-5-20251001

batching:
  min_records: 20
  max_records: 60

concepts:
  min_confidence: 0.4
  promotion_confidence: 0.55
  min_supporting_evidence: 2
  max_active_concepts: 30
  dedupe_similarity: 0.85

registry:
  default_status: candidate
  allow_auto_promotion: true
  never_delete: true

backend:
  default: null
  poe_path: ../probabilistic_ontology_engine

validation:
  latent_alignment_threshold: 0.3
  retain_ungrounded_high_confidence: true
```

---

# CLI Summary

Final intended CLI:

```bash
poea ingest
poea induce
poea registry init
poea registry import
poea registry list
poea registry diff
poea consolidate
poea registry promote
poea score-evidence
poea export-nodes
poea run-backend
poea pipeline
poea report
poea compare
poea validate-latent
```

Minimum useful CLI:

```bash
poea pipeline
```

---

# Testing Strategy

## Unit Tests

Required:

```text
test_evidence_loader.py
test_evidence_normalizer.py     ← verifies pre-annotation stripping
test_concept_schema.py
test_registry.py
test_consolidation.py
test_scorer.py
test_backend_interface.py
test_export_nodes.py
```

## Integration Tests

Required:

```text
test_pipeline_null_backend.py
test_pipeline_art_sample.py
test_poe_backend_smoke.py
```

## Golden Fixtures

Create:

```text
tests/fixtures/art_evidence_sample.json
tests/fixtures/raw_concepts_sample.json
tests/fixtures/scored_evidence_sample.json
tests/fixtures/registry_expected.json
```

## No-Network Test Rule

Unit tests must not call LLM APIs.

Mock LLM responses.

Live LLM tests should be marked separately:

```bash
pytest -m live
```

---

# First Complete Milestone

The first complete milestone is not PCA.

It is not latent validation.

It is not perfect concept consolidation.

The first complete milestone is:

```text
Raw art evidence
    ↓
LLM-induced concepts
    ↓
automatic active concept selection
    ↓
evidence scoring (concept assignments per evidence record)
    ↓
POE-compatible nodes
    ↓
POE backend
    ↓
ontology graph
```

with no hand-authored domain variable vocabulary.

Call this:

```text
MVP-0: Vocabulary-Free Ontology Construction
```

---

# MVP-0 Acceptance Criteria

MVP-0 is complete when:

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```

produces:

```text
artifacts/evidence.json
artifacts/raw_concepts.json
artifacts/poea_registry.sqlite
artifacts/nodes.json
artifacts/poea_graph.json
artifacts/run_report.md
```

and the run uses:

```text
zero manually supplied art ontology variables
```

The pipeline must pass through all stages:

```text
Evidence (text only; pre-annotations discarded)
    ↓
Concept Discovery
    ↓
Concept Registry
    ↓
Evidence Scoring (Assignment Bridge)
    ↓
Nodes
    ↓
POE Graph
```

---

# What Not To Build First

Do not build first:

* full PCA system
* sparse autoencoder layer
* elaborate UI
* perfect registry governance
* multi-domain generality
* advanced hypothesis generation
* autonomous scheduled runs
* comparison dashboards
* enrichment fields (direction, frequency, epistemic_role)
* multi-tier LLM model routing

Those belong after MVP-0.

The first job is to remove the a priori vocabulary constraint.

---

# Philosophical Acceptance Test

The implementation is aligned with POE-A only if the following sentence is true:

```text
The system receives evidence before it receives concepts.
```

If concepts are supplied before evidence, the system has regressed to POE v1.

---

# Final Target

The final target is an abductive ontology engine:

```text
Evidence
    ↓
Concept Generation
    ↓
Concept Stabilization
    ↓
Evidence Scoring
    ↓
Probabilistic Structure Learning
    ↓
Ontology Graph
    ↓
Hypothesis Competition
```

POE-A is complete when it can construct and update ontology graphs from evidence without requiring a fixed, designer-authored variable vocabulary.
