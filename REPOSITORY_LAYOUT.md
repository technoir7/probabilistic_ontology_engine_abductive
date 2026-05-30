# POE-A Repository Layout

**Version:** 1.0
**Date:** 2026-05-30
**Scope:** MVP-0 and immediate post-MVP phases

---

## Design Principles

1. Only create directories and files that will be populated during the current or next phase.
2. Keep the `poea` package flat enough that contributors can read the module list and understand the system without a map.
3. Backend adapters are isolated behind an interface. No POE internals leak into core pipeline modules.
4. The registry is the single source of truth for concept state. No other module should maintain concept state independently.

---

## Directory Tree

```
probabilistic_ontology_engine_abductive/
│
├── SPEC.md                          # Authoritative specification (VIE/POE-A)
├── IMPLEMENTATION_PLAN.md           # Build plan
├── ARCHITECTURE_REVIEW.md           # This review (architectural authority)
├── REPOSITORY_LAYOUT.md             # This document
├── MVP0_SCOPE.md                    # MVP-0 definition
├── RISK_REGISTER.md                 # Risk register
├── IMPLEMENTATION_SEQUENCE.md       # Phased build sequence
│
├── README.md                        # Project overview and quickstart
├── pyproject.toml                   # Package metadata, dependencies, tool config
│
├── configs/
│   └── induction_config.yaml        # Runtime configuration
│
├── migrations/
│   ├── 001_registry.sql             # concepts, concept_events tables
│   ├── 002_induction_runs.sql       # induction_runs table
│   └── 003_evidence_links.sql       # concept_evidence_links table
│
├── src/
│   └── poea/
│       ├── __init__.py
│       ├── cli.py                   # Top-level CLI entrypoint (typer)
│       │
│       ├── evidence/
│       │   ├── __init__.py
│       │   ├── schemas.py           # EvidenceUnit pydantic model
│       │   ├── loaders.py           # Load JSON files / directories
│       │   └── normalizer.py        # Extract text, discard pre-annotations
│       │
│       ├── concepts/
│       │   ├── __init__.py
│       │   ├── schemas.py           # Concept pydantic model (MVP-minimal)
│       │   ├── inducer.py           # LLM-based concept proposal
│       │   ├── prompts.py           # Prompt templates for induction
│       │   ├── consolidation.py     # Merge near-duplicate concepts
│       │   └── scorer.py           # Score (evidence, concept) → assignment
│       │
│       ├── registry/
│       │   ├── __init__.py
│       │   ├── store.py             # SQLite registry CRUD
│       │   ├── lifecycle.py         # status transitions, auto-promotion
│       │   └── diff.py              # Registry diff between runs
│       │
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── interface.py         # StructureLearningBackend protocol
│       │   ├── null_backend.py      # Trivial backend for testing
│       │   └── poe_backend.py       # POE adapter (Phase 8)
│       │
│       └── artifacts/
│           ├── __init__.py
│           └── exporters.py         # nodes.json, run_report.md
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── art_evidence_sample.json
│   │   ├── raw_concepts_sample.json
│   │   └── registry_expected.json
│   │
│   ├── test_evidence_loader.py
│   ├── test_evidence_normalizer.py
│   ├── test_concept_schema.py
│   ├── test_concept_inducer.py      # mocked LLM
│   ├── test_consolidation.py
│   ├── test_scorer.py               # mocked LLM
│   ├── test_registry.py
│   ├── test_lifecycle.py
│   ├── test_backend_interface.py
│   ├── test_export_nodes.py
│   ├── test_poe_backend.py          # mocked POE
│   ├── test_pipeline_null_backend.py
│   └── test_pipeline_art_sample.py  # live integration (marked `live`)
│
├── examples/
│   └── art_sample/
│       └── README.md
│
└── artifacts/                        # gitignored — runtime outputs
    ├── evidence.json
    ├── raw_concepts.json
    ├── poea_registry.sqlite
    ├── nodes.json
    ├── poea_graph.json
    └── run_report.md
```

---

## Module Ownership

### `evidence/`

**Owns:** raw data ingestion and normalization to the standard `EvidenceUnit` format.

**Does not own:** concept induction, scoring, registry operations.

**Key constraint:** The normalizer must strip pre-existing variable annotations from art-market evidence files. Only the raw text fields (`title`, `text`, `notes`) should pass to downstream modules. The `assignments` and `causal_claims` fields present in art evidence files represent a POE v1 vocabulary and must be discarded.

**Dependency rule:** No imports from `concepts/`, `registry/`, or `backends/`.

---

### `concepts/`

**Owns:** concept induction from evidence text, concept consolidation, and evidence scoring.

**Does not own:** registry persistence, backend translation.

Three distinct responsibilities live here:
- `inducer.py`: LLM-based concept proposal from evidence batches
- `consolidation.py`: detection and merging of near-duplicate concepts
- `scorer.py`: translating (evidence_unit, concept) pairs into boolean assignments for POE

`scorer.py` is the evidence-to-assignment bridge described in ARCHITECTURE_REVIEW.md Finding 1. It is a new module not present in the original implementation plan. It belongs here because it is a concept-level operation: given a concept's definition and an evidence document, does the document support the concept being True or False?

**Dependency rule:** Imports from `evidence/schemas` only. No imports from `registry/` or `backends/`.

---

### `registry/`

**Owns:** all concept state persistence, status transitions, and history.

**Key invariant:** Concepts are never deleted. Every state change is recorded in `concept_events`. Merges record both the winner and the loser's concept_id.

`lifecycle.py` owns the auto-promotion logic. The MVP threshold (`min_confidence: 0.55`, `min_supporting_evidence: 2`) is configurable. Auto-promotion writes to the registry as a transition event, producing an audit trail.

**Dependency rule:** Imports from `concepts/schemas` and `evidence/schemas`. No imports from `backends/`.

---

### `backends/`

**Owns:** the contract between POE-A and structure-learning systems, plus all adapter implementations.

`interface.py` defines the `StructureLearningBackend` protocol. The protocol is intentionally broad — adapters are free to do significant translation work internally.

`null_backend.py` returns a trivial graph artifact and is the default for testing. All pipeline tests except smoke tests use the null backend.

`poe_backend.py` is responsible for:
1. Building `Variable` objects from active concepts (BOOLEAN type, [True, False] support, stable UUID from concept name hash)
2. Building seed `OntologyCandidate` objects (all-pairs edges as initial topology)
3. Converting scored evidence into POE `EvidenceRecord` objects (using output from `concepts/scorer.py`)
4. Constructing and registering a dynamic domain module with POE
5. Running `engine.learn()` and returning a graph artifact

`poe_backend.py` imports POE through the narrowest available interface: `from engine.engine import ProbabilisticOntologyEngine` and `from engine.schemas import Variable, DependencyEdge, OntologyCandidate, EvidenceRecord, ObservedAssignment`. Nothing else.

**Dependency rule:** Imports from `registry/` and `concepts/schemas` and `evidence/schemas`. The POE import is isolated inside `poe_backend.py` only — not visible to any other module.

---

### `artifacts/`

**Owns:** serialization of pipeline outputs to disk.

`exporters.py` produces `nodes.json` and `run_report.md`. Reports are human-readable Markdown, not JSON. Reports are generated from the registry state at run completion.

**Dependency rule:** Imports from `registry/`, `concepts/schemas`, `evidence/schemas`. No imports from `backends/`.

---

### `cli.py`

**Owns:** the command-line interface only. No business logic.

Each CLI command delegates immediately to the appropriate module. CLI flags map to config overrides, not to hardcoded values.

---

## Deferred Modules (Not in MVP-0)

The following modules appear in the implementation plan but are explicitly excluded from the initial repository layout:

| Module | Phase | Reason for Deferral |
|--------|-------|---------------------|
| `validation/latent.py` | Phase 12 | PCA/ICA over text requires embedding pipeline not in MVP |
| `validation/alignment.py` | Phase 12 | Depends on latent.py |
| `validation/pruning.py` | Phase 13 | Depends on cross-run stability metrics |
| `evidence/chunker.py` | Future | Text chunking not needed if full-document induction works |
| `evidence/store.py` | Future | File-based evidence storage is sufficient for MVP |
| `concepts/dedupe.py` | Merged into `consolidation.py` | Not a separate module at MVP scale |
| `registry/migrations.py` | Phase 3+ | SQL migration runner; add when schema evolution is needed |

---

## Dependency Direction Summary

```
evidence/schemas
    ↓ (imported by)
concepts/schemas, concepts/inducer, concepts/scorer
    ↓ (imported by)
registry/store, registry/lifecycle
    ↓ (imported by)
backends/poe_backend, artifacts/exporters
    ↓ (called by)
cli.py
```

POE internals are imported only inside `backends/poe_backend.py`.

This direction is strictly one-way. No module imports from a module below it in this chain.

---

## Configuration

`configs/induction_config.yaml` is the single configuration file. Runtime values (thresholds, model names, batch sizes) must not be hardcoded inside modules. Every threshold that affects pipeline behavior must be present in the config and readable by the relevant module.

The config file is committed. Secrets (API keys) are environment variables, never config file values.

---

## Artifact Gitignore

```
artifacts/
*.sqlite
*.sqlite-shm
*.sqlite-wal
```

Artifacts are runtime outputs. They are not committed. The `examples/art_sample/` directory may contain a small committed fixture set for demonstration purposes.

---

## Test Organization

Tests mirror the source structure. Each module has a corresponding unit test file. Integration tests that exercise the full pipeline live at the top level of `tests/`.

LLM-dependent tests are marked `@pytest.mark.live` and excluded from default CI runs:

```bash
pytest                     # no LLM calls
pytest -m live             # includes LLM calls
```

All unit tests mock LLM responses. The mock fixture interface should match the actual LLM response schema so that unit tests break correctly when the schema changes.
