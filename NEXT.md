# Next: Phase 9 — POE Adapter

---

## Objective

Connect POE-A to the existing POE structure learner.

The POE adapter is the bridge between POE-A's abductively-induced concepts
and POE's probabilistic graph learning engine. It translates:
- Induced concept nodes → POE `Variable` objects
- Scored evidence assignments → POE `EvidenceRecord` objects
- Then calls `engine.learn()` and returns a graph artifact.

---

## Inputs Required

| Input | Location | Status |
|-------|----------|--------|
| Active concept nodes | `artifacts/nodes.json` | Ready (Phase 8) |
| Scored evidence | `artifacts/scored_evidence.json` | Ready after live run (Phase 6) |
| POE package | `../probabilistic_ontology_engine` | **Requires installation** |
| Backend interface | `src/poea/backends/interface.py` | Ready (Phase 7) |

---

## Pre-condition: POE Installation

Phase 9 requires POE to be installed as a local editable package:

```bash
pip install -e ../probabilistic_ontology_engine
```

This does not clone POE into POE-A. It simply allows POE-A to call POE as a local package.

No POE code should be copied into POE-A.

---

## What Phase 9 Must Produce

### Adapter file — `src/poea/backends/poe_backend.py`

The `POEBackend` class implementing `StructureLearningBackend`.

### Responsibilities (from IMPLEMENTATION_PLAN.md)

1. Build `Variable` objects from active concepts using:
   ```python
   from engine.variable_identity import stable_variable_id
   variable_id = stable_variable_id(domain_id, concept_name)
   ```
   **Never use `uuid4()` for variable UUIDs.** Random UUIDs break POE's historical evidence matching on restart.

2. Build a seed `OntologyCandidate` with co-occurrence-seeded edges:
   - Only seed edges where both concepts appeared in the same evidence record
   - Not all-pairs

3. Construct a dynamic domain module wrapping the induced variables and candidate.

4. Translate scored evidence assignments into POE `EvidenceRecord` objects with `ObservedAssignment` entries keyed to stable variable UUIDs.

5. Register and activate the dynamic domain module with POE.

6. Call `engine.learn()` and return a graph artifact.

### Anti-goals

Do not:
- Copy POE code into POE-A
- Fork POE inside POE-A
- Import POE internals beyond: `engine.engine`, `engine.schemas`, `engine.variable_identity`
- Modify POE during this phase
- Make POE-A dependent on art-domain specifics

### CLI integration

Register `poe` in the backend factory and update `poea run-backend`:

```bash
poea run-backend \
  --backend poe \
  --concepts artifacts/canonical_concepts.json \
  --scored-evidence artifacts/scored_evidence.json \
  --output artifacts/poea_graph.json
```

---

## Exit Criteria (from IMPLEMENTATION_PLAN.md Phase 9)

POE-A runs end-to-end:

```
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

**This is the first major project victory (MVP-0 prerequisite).**

---

## Implementation Notes

### Variable UUID stability

From IMPLEMENTATION_PLAN.md:
> Variable UUIDs must be derived deterministically from concept names.
> Use `stable_variable_id(domain_id, concept_name)`.
> Never use `uuid4()` for variable UUIDs. Random UUIDs break POE's historical evidence matching on restart.

### Co-occurrence edge seeding

Seed only edges where both concepts appeared in the same evidence record:
- Iterate over scored_evidence records
- For each record, collect concepts with `assigned_value=True`
- For each pair of co-occurring True concepts, add a candidate edge

This produces a sparse seed graph rather than an all-pairs dense graph.

### Missingness translation

| POE-A missingness | POE assignment type |
|-------------------|---------------------|
| `OBSERVED` | `ObservedAssignment` |
| `SOFT_OBSERVED` | `ObservedAssignment` (with reduced weight if POE supports it) |
| `MISSING` | omit from evidence record (treated as missing data) |

### Dependency boundary

POE-A may import from:
- `engine.engine` — the main POE engine
- `engine.schemas` — Variable, OntologyCandidate, EvidenceRecord, ObservedAssignment
- `engine.variable_identity` — stable_variable_id

POE-A must not import from POE's domain modules or internal implementation details.
