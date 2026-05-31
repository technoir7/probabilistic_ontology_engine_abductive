# POE-A Development Guide

## Architecture Boundary: Do Not Reinvent POE

**This is the most important constraint in this codebase.**

### What POE-A Is

POE-A exists to solve one specific problem: old POE requires ontology variables to be selected by humans before evidence is ingested. POE-A removes that requirement by inducing candidate variables from evidence.

POE-A is an upstream induction frontend. Old POE is the canonical epistemic backend.

### Ownership Split

**POE-A owns:**
- Evidence ingestion and normalization
- LLM-driven concept/variable induction
- Concept registry, consolidation, and lifecycle
- Assignment routing (deterministic mappers, semantic LLM scorer, caching)
- Adapter logic translating POE-A artifacts into old POE input formats
- Node export (concept → `Variable` format)
- Cost controls and prefilter analysis
- Run reports

**Old POE owns:**
- Stochastic conditionals and CPT parameter learning
- BIC-based edge existence probability update
- Structure learning
- Competing ontology candidate population
- Population management (scoring, pruning, variant introduction)
- Posterior inference (pgmpy VariableElimination)
- SQLite evidence, parameter, and population stores

### The Canonical Handoff

The architectural boundary is a single function call:

```python
# poe_backend.py:POEBackend.learn_graph()
snapshot = engine.learn(batch=records, domain_module_id=self._domain_id)
```

Everything before this line is POE-A. Everything inside `engine.learn()` is old POE.

Posterior inference passes through the same boundary:

```python
result = engine.query(InferenceQuery(...))
```

POE-A does not compute posterior probabilities. It passes target variables to `engine.query()` and reports the result.

### What New POE-A Code Must Not Do

Do not implement any of the following inside POE-A:

- CPT parameter estimation or accumulation
- BIC log-likelihood ratio computation
- Edge existence probability update
- Population scoring, pruning, or variant introduction
- Bayesian network construction
- Posterior probability computation
- Graph structure search or learning

If any of those are needed, call old POE. It already has them.

### When to Ask Before Adding Code

If a proposed addition involves:

- Probability calculations
- Conditional distributions
- Graph edges or structure learning
- Competing model/candidate scoring
- Posterior or marginal computation

Stop and ask whether old POE already provides it.

### Sibling Repo

Old POE lives at:

```
../probabilistic_ontology_engine
```

Key classes: `ProbabilisticOntologyEngine`, `LearningService`, `EdgeExistenceService`, `PopulationManager`, `InferenceService`.

POE-A imports only: `src.engine.engine`, `src.engine.schemas`, `src.engine.variable_identity`.

---

## Running Tests

```bash
.venv/bin/pytest               # all unit tests (no live API calls)
.venv/bin/pytest -m live       # live API tests (requires FIREWORKS_API_KEY)
.venv/bin/python -m ruff check .
```

## Evidence Routing Rules

| Evidence type | Route | LLM calls |
|---------------|-------|----------:|
| `prose_text` / `unstructured_text` | `SemanticLLMScorerBackend` | yes |
| `structured_numeric` / `tabular` / `api_derived` | `DeterministicMapperBackend` | 0 |
| `direct_structured` / pre-assigned metadata | `DirectStructuredAssignmentBackend` | 0 |
| unknown structured | explicit error | 0 |

The router is deterministic. It never calls an LLM to decide whether to call an LLM.

## Shadow Prefilter

The `ShadowPrefilter` runs in read-only observation mode only. It does not skip any LLM calls. Skipping is NOT enabled and must not be enabled until a redesigned prefilter demonstrates ≥95% recall. See `SHADOW_PREFILTER_EVALUATION.md`.
