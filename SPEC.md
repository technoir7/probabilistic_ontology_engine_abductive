# Probabilistic Ontology Engine Abductive (POE-A)

**Status:** Research Prototype

**Repository:** `probabilistic_ontology_engine_abductive`

**Relationship to Existing Systems:** Upstream sibling project to `probabilistic_ontology_engine`

---

# Purpose

The Probabilistic Ontology Engine Abductive (POE-A) is an upstream epistemic system whose purpose is to discover candidate explanatory variables directly from evidence rather than requiring those variables to be specified a priori by a human designer.

The system exists to address a major limitation of the current Probabilistic Ontology Engine (POE):

> POE assumes the variable vocabulary is already known.

POE-A attempts to discover that vocabulary.

The intended result is not autonomous truth discovery.

The intended result is a continuously evolving candidate variable set that can be evaluated, revised, merged, deprecated, and tested against downstream causal structure learners.

---

# Core Research Question

Current ontology engines answer:

> Given variables, what causal structure best explains the evidence?

POE-A addresses an earlier question:

> What variables should exist at all?

The project therefore operates one layer higher in the epistemic stack.

---

# Non-Goals

POE-A is not intended to:

* Replace causal structure learning
* Replace Bayesian inference
* Autonomously determine truth
* Eliminate human review
* Produce final ontologies without validation
* Replace domain expertise
* Rewrite ontology state automatically

POE-A is a hypothesis generator.

Not a truth engine.

---

# Epistemic Position

The system rejects two extreme positions.

## Pure Hand-Crafted Ontologies

Human experts define all variables before evidence is examined.

### Advantages

* Interpretable
* Stable
* Domain aware

### Disadvantages

* Designer bias
* Vocabulary lock-in
* Poor discovery of novel variables

## Pure Latent Models

Variables emerge entirely from unsupervised factor extraction.

### Advantages

* Data-driven
* Discovers unexpected structure

### Disadvantages

* Difficult interpretation
* Unstable naming
* Weak semantic coherence

## Hybrid Approach

POE-A adopts a hybrid approach.

Variables are proposed semantically by LLMs and evaluated against latent structure extracted from evidence.

The goal is to combine:

* Human interpretability
* Semantic coherence
* Statistical grounding
* Discovery of novel variables

---

# System Boundary

## Inputs

* Text documents
* Research reports
* Articles
* Press releases
* Market data
* Time series
* Structured datasets
* Existing ontology state

## Outputs

* Candidate variables
* Variable definitions
* Confidence estimates
* Latent alignment metrics (post-MVP)
* Registry updates
* Variable diffs

The output of POE-A is **not a causal graph**.

The output is a **versioned variable vocabulary**.

---

# Relationship to POE

The Probabilistic Ontology Engine Abductive is not a replacement for the Probabilistic Ontology Engine.

The systems operate at different epistemic layers.

POE answers:

```text
Given a variable vocabulary,
what causal structure best explains the evidence?
```

POE-A answers:

```text
Given evidence,
what variables should exist at all?
```

POE-A therefore sits upstream of POE.

The output of POE-A is a versioned node registry.

Any structure-learning system capable of consuming a node registry may be used downstream.

POE is the initial backend implementation but is not a required dependency.

Dependency direction:

```text
Evidence
    ↓
POE-A
    ↓
Node Registry
    ↓
Structure Learning Backend
    ↓
Graph
```

Not:

```text
Evidence
    ↓
POE
```

---

# Repository Architecture

POE-A is a sibling project.

Not a fork.

```text
epistemic-monitor-suite/

    probabilistic_ontology_engine/

    art-market-domain/

    probabilistic_ontology_engine_abductive/
```

POE-A may call POE.

POE never depends on POE-A.

Dependency direction is intentionally one-way.

---

# Backend Interface Philosophy

Structure learning is treated as a pluggable capability.

POE-A owns the backend contract.

Backends implement the contract.

Examples:

* POEBackend
* Bayesian DAG Backend
* Constraint Discovery Backend
* Graph Neural Network Backend
* Future Experimental Systems

The induction system must never depend directly on backend internals.

All backend-specific logic belongs inside adapters.

---

# Architectural Principle

POE-A owns:

```text
Evidence
    ↓
Variable Discovery
    ↓
Variable Validation
    ↓
Node Registry
    ↓
Evidence Scoring
```

External systems own:

```text
Evidence Scoring Output
    ↓
Structure Learning
    ↓
Hypothesis Competition
    ↓
Regime Detection
```

Variable discovery and structure learning are distinct epistemic tasks.

They should remain separate.

---

# Architecture Overview

```text
Raw Data Sources
      │
      ▼
┌─────────────────────┐
│  Ingestion Layer    │
│  (text only; strip  │
│   pre-annotations)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Concept        │
│  Induction Layer    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Concept            │
│  Consolidation      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Node Registry       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Evidence Scoring    │← assigns concept True/False
│ (Assignment Bridge) │  per evidence record
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Backend Interface   │
└────────┬────────────┘
         │
         ▼
Structure Learning Backend

── Post-MVP ─────────────────────────────

┌─────────────────────┐
│  Latent Extraction  │← statistical grounding
│  PCA / ICA / SAE    │  added after MVP-0
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Cross Validation    │
│ + Pruning           │
└─────────────────────┘
```

---

# Stage 1: Ingestion and Chunking

## Input

Raw evidence:

* Time series
* Text documents
* Reports
* Releases
* Structured records

## Processing

* Normalize numeric signals to rolling-window z-scores
* Chunk text into 512–1024 token evidence units
* Assign batch IDs
* Assign ingestion timestamps
* Preserve source metadata

## Pre-Annotation Constraint

Some evidence sources (including art-domain evidence files) contain pre-existing variable annotations (`assignments`, `causal_claims`) that encode an external domain vocabulary.

These fields must be discarded during ingestion.

Reading pre-existing annotations would give POE-A access to the vocabulary it is supposed to discover, defeating the project's purpose.

Only raw text fields (title, notes, text content) pass to downstream stages.

## Output Schema

```json
{
  "batch_id": "uuid",
  "source": "string",
  "timestamp": "iso8601",
  "domain_tag": "string",
  "content_type": "numeric | text | mixed",
  "payload": "data"
}
```

---

# Stage 2: Unsupervised Latent Extraction (Post-MVP)

This stage identifies latent structure without semantic assumptions.

**This stage is post-MVP.** It is not required for MVP-0. It is added after the end-to-end abductive pipeline is working.

## Methods

* PCA
* ICA

Optional future methods:

* Sparse Autoencoders
* NMF
* Topic Models
* Representation Learning

## Output

For each factor:

```json
{
  "factor_id": 1,
  "explained_variance_ratio": 0.12,
  "top_signal_loadings": [],
  "sign": "positive"
}
```

## Retention Rules

Retain factors that:

* Explain at least 2% variance individually

OR

* Contribute to first 80% cumulative variance

Typically:

```text
5–15 retained factors
```

---

# Stage 3: LLM Concept Induction

The LLM proposes semantic concepts directly from evidence.

The LLM does not see latent factors during this stage.

Latent validation occurs later (post-MVP).

## Requirements

A concept must:

* Recur across evidence
* Possess causal relevance
* Be observable or inferable
* Be distinct from other concepts

## MVP Output Schema

```json
{
  "concepts": [
    {
      "name": "AuthenticityPremium",
      "definition": "...",
      "confidence": 0.84,
      "supporting_evidence_ids": []
    }
  ]
}
```

The following fields are post-MVP enrichment and must not be required for MVP-0:

* `direction` — signal directionality (positive / negative / bidirectional)
* `frequency` — temporal pattern (persistent / episodic / shock)
* `epistemic_role` — causal position (driver / outcome / mediator / context)

These fields add prompt complexity without affecting the core pipeline. They are added in a post-MVP enrichment pass.

---

# Concept Consolidation

Individual batches generate concept proposals.

A second-pass consolidation stage:

* Merges duplicates
* Resolves naming conflicts
* Drops weak proposals
* Produces canonical candidates

Rules:

* Must appear in at least 2 batches
* Prefer most precise terminology
* Merge semantic duplicates
* At the start of each induction pass, load existing registry concepts for cross-run deduplication — consolidation applies across runs, not only within a single run

---

# Stage 4: Cross Validation and Pruning (Post-MVP)

**This stage is post-MVP.** It is not required for MVP-0. It is added after the end-to-end abductive pipeline is working.

Candidate concepts are compared against latent factors.

## Goal

Determine whether semantic concepts have statistical support.

## Alignment Procedure

For each concept:

1. Retrieve supporting evidence
2. Retrieve latent factor exposure
3. Compute alignment score
4. Determine grounding status

Outputs:

```text
Grounded
Ungrounded
Needs Review
```

---

# Pruning Rules (Post-MVP)

| Condition                          | Action               |
| ---------------------------------- | -------------------- |
| Confidence < 0.4                   | Drop                 |
| Appears in fewer than 2 batches    | Drop                 |
| Definition similarity > 0.85       | Merge                |
| No alignment and confidence < 0.6  | Review               |
| No alignment and confidence >= 0.6 | Retain as Ungrounded |

Ungrounded concepts are not automatically discarded.

They may represent semantic phenomena absent from measured signals.

---

# Stage 5: Node Registry

The registry is the primary output of POE-A.

The registry is treated as a scientific record rather than a configuration file.

## Status Values

```text
candidate
active
deprecated
merged_into
rejected
```

## Policy

* Never delete nodes
* Preserve lineage
* Record provenance
* Track induction runs
* Preserve merge history

---

# Registry Schema

```sql
CREATE TABLE node_registry (
  node_id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  definition TEXT NOT NULL,
  direction TEXT,
  frequency TEXT,
  llm_confidence FLOAT,
  factor_alignment_id INT,
  alignment_strength FLOAT,
  grounded BOOLEAN,
  status TEXT,
  merged_into UUID,
  induction_run_id UUID,
  domain_tag TEXT,
  schema_version INT,
  created_at TIMESTAMP,
  deprecated_at TIMESTAMP
);
```

---

# Stage 6: Evidence Scoring (Assignment Bridge)

This stage is the critical link between the concept registry and structure learning.

## Purpose

Structure-learning backends (including POE) require evidence to be expressed as assignments of observed values to specific variables. They do not accept raw text.

The evidence scoring stage translates each evidence record into a set of concept-keyed boolean assignments by asking: does this evidence document support this concept being True or False?

## Inputs

* Active concept set from the registry
* Normalized evidence records from ingestion

## Method

For each (evidence record, active concept) pair:

* Call LLM with the concept definition and the evidence text
* Receive: `supports_true`, `supports_false`, or `neutral`
* Map `neutral` to the missing-data missingness type used by the downstream backend

Scoring calls should be batched: score all active concepts for a single evidence record in one LLM call to reduce API cost.

Results are cached in the registry (`concept_evidence_links`) so they are not recomputed on re-runs.

## Output

For each evidence record, a set of concept assignments:

```json
{
  "evidence_id": "...",
  "assignments": [
    {
      "concept_id": "...",
      "variable_name": "AuthenticityPremium",
      "assigned_value": true,
      "confidence": 0.81,
      "missingness": "OBSERVED"
    }
  ]
}
```

`neutral` assignments use `missingness: "MISSING"`.

Low-confidence assignments use `missingness: "SOFT_OBSERVED"`.

## Critical Note

The evidence scorer is an interpretation layer. Its output is the data that structure learning trains on. Systematically biased scoring will produce a biased graph regardless of concept quality. Scorer output must be exposed in run reports and be auditable.

---

# Human Oversight

Human review is required for production ontology governance.

## Autonomous Execution

Automatic promotion is permitted in autonomous pipeline execution (MVP-0 and beyond), subject to the following constraints:

* Every auto-promotion is recorded as a `concept_event` with the criteria that triggered it
* Auto-promotion thresholds are configurable and must not be hardcoded
* Auto-promoted concepts may be manually demoted or rejected at any time
* A hard cap on active concept count prevents uncontrolled vocabulary growth

## Human-Governed Deployments

In deployments requiring human review before ontology changes take effect, the system may recommend:

* Additions
* Merges
* Deprecations

The system may not autonomously modify active ontology state without producing a full audit trail.

Automatic promotion and human-governed promotion are two operating modes of the same registry. The mode is configurable, not architectural.

---

# Backend Interface

POE-A exposes active registry snapshots and scored evidence to structure-learning systems.

Minimal backend contract:

```python
class StructureLearningBackend:
    def learn_graph(...):
        pass

    def score_hypotheses(...):
        pass
```

Backend implementations:

* POEBackend
* NullBackend
* Future Backends

---

# Downstream Integration

Structure-learning systems consume:

```text
Node Registry (active concepts)
+
Scored Evidence Records
```

and produce:

```text
Graph
+
Hypotheses
+
Scores
```

POE-A remains agnostic to implementation details.

---

# Induction Run Cadence

| Trigger                   | Action                        |
| ------------------------- | ----------------------------- |
| 50+ new records           | Incremental induction         |
| Weekly                    | Full rolling-window induction |
| Dominant hypothesis shift | Targeted induction            |
| Excess structure entropy  | Full induction                |

---

# Failure Modes

| Failure                | Mitigation                      |
| ---------------------- | ------------------------------- |
| Concept hallucination  | Latent alignment (post-MVP)     |
| Concept drift          | Registry versioning             |
| Duplicate concepts     | Consolidation                   |
| Cost explosion         | Batch limits + LLM result cache |
| API interruption       | Idempotent processing           |
| Semantic instability   | Human review                    |
| Scorer bias            | Audit trail + spot-check        |

---

# Success Criteria

The project succeeds if:

* Novel useful concepts emerge
* Registry quality improves over time
* Human review remains tractable
* Downstream causal models improve
* Induced vocabularies outperform manually defined vocabularies

The project fails if:

* Concept proliferation becomes unmanageable
* Semantic coherence collapses
* Review burden becomes excessive
* Model quality degrades

---

# Deliverables

## Core Components

* ingestor.py
* variable_inducer.py
* consolidation.py
* scorer.py           ← evidence-to-assignment bridge
* cross_validator.py  (post-MVP)
* latent_extractor.py (post-MVP)
* node_registry.py
* backend_interface.py
* poe_backend.py

## Database

* node_registry schema
* latent_factor schema (post-MVP)
* induction_run schema

## Configuration

* induction_config.yaml

## CLI

```bash
poea induce
poea score-evidence
poea diff
poea export
poea run-backend
poea pipeline
poea report
```

---

# MVP-0 Pipeline Status

The current MVP-0 implementation exposes an end-to-end pipeline command:

```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```

The implementation uses the documented JSON artifact architecture rather than
the original SQLite registry placeholder. The current pipeline artifacts are:

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

`poea pipeline` reuses existing intermediate artifacts unless `--force` is
passed. With `--backend null`, the command can run without live scored evidence
for local tests. With `--backend poe`, scored evidence is generated or reused
before invoking POE.

`poea report --run latest` regenerates `artifacts/run_report.md` from existing
artifacts without re-running induction, scoring, consolidation, node export, or
backend learning. The report includes concept status counts, assignment rates,
sample scorer outputs, backend graph and candidate summaries, artifact paths,
timestamps, warnings, and POE-learning inclusion/omission diagnostics.

This preserves the core acceptance condition:

```text
The system receives evidence before it receives concepts.
```

The pipeline still must not receive a hand-authored domain variable list.

---

# Long-Term Vision

Current architecture:

```text
Human
    ↓
Variables
    ↓
Structure Learning
```

Target architecture:

```text
Evidence
    ↓
Variable Discovery
    ↓
Evidence Scoring
    ↓
Structure Learning
    ↓
Hypothesis Competition
    ↓
Regime Detection
```

The Probabilistic Ontology Engine Abductive becomes the vocabulary-generation and evidence-scoring layer of a larger epistemic operating system.

Structure learning becomes one replaceable component inside that system.
