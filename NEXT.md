# Next: Phase 7 — Backend Interface

---

## Objective

Define the contract between POE-A and structure-learning systems.

POE-A must not hardwire itself to POE internals. The backend interface is a pluggable protocol that any structure-learning system can implement.

---

## Inputs Available

| Input | Location | Status |
|-------|----------|--------|
| Active concept set | `artifacts/canonical_concepts.json` | Ready (11 concepts) |
| Scored evidence | `artifacts/scored_evidence.json` | Ready (after live run) |
| Concept-keyed assignments | inside scored_evidence.json | Ready |

---

## What Phase 7 Must Produce

### 1. Protocol definition — `src/poea/backends/interface.py`

```python
from typing import Any, Mapping, Protocol, Sequence

class StructureLearningBackend(Protocol):
    def learn_graph(
        self,
        concepts: Sequence[Mapping[str, Any]],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]: ...

    def score_hypotheses(
        self,
        graph: Mapping[str, Any],
        scored_evidence: Sequence[Mapping[str, Any]],
        config: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]: ...
```

Note: the parameter is `scored_evidence`, not raw `evidence`. Backends receive pre-scored
assignments, not raw text.

### 2. Null backend — `src/poea/backends/null_backend.py`

The NullBackend must:
- Accept active concepts
- Accept scored evidence assignments
- Return a trivial graph artifact (one node per concept, no edges)
- Allow CLI testing without POE

### 3. Backend registration / factory

A mechanism to select backend by name (e.g., `"null"`, `"poe"`) for use by the Phase 10 pipeline command.

---

## Implementation Tasks

1. Create `src/poea/backends/` directory with `__init__.py`
2. Implement `src/poea/backends/interface.py` — StructureLearningBackend protocol
3. Implement `src/poea/backends/null_backend.py` — NullBackend
4. Add `poea run-backend` CLI command (null backend only; POE backend in Phase 9)
5. Add tests — `tests/test_backend_interface.py`

### CLI

```bash
poea run-backend \
  --backend null \
  --concepts artifacts/canonical_concepts.json \
  --scored-evidence artifacts/scored_evidence.json \
  --output artifacts/poea_graph.json
```

---

## Exit Criteria (from IMPLEMENTATION_PLAN.md Phase 7)

- Backend interface works independently of POE
- NullBackend returns a trivial graph (one node per concept, no edges)
- CLI testing works without a POE installation

---

## Phase 7 Unblocks

Phase 8 (Concept-to-Node Translation) and Phase 9 (POE Adapter) both implement the backend interface. Phase 10 (End-to-End Pipeline) depends on all backends being wired to the CLI.

The NullBackend from Phase 7 allows Phase 10 to be partially tested without Phase 9 complete.
