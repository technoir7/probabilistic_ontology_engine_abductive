# POE-A Boundary and Architecture Audit

_Date: 2026-05-30_
_Scope: Full boundary audit — no code changes made_

---

## Final Verdict

**A. POE-A is functioning as a variable-induction frontend feeding old POE semantics.**

No duplicate POE-core machinery was found. The architectural boundary is clear, explicit, and well-enforced. Old POE's epistemic engine — CPT parameter learning, BIC-based edge existence, population management, and pgmpy inference — exists only in the sibling repository and is called through a single thin adapter.

**One important capability gap exists:** `engine.query()` is never called. Old POE's inference layer (posterior queries, conditional queries, intervention queries via pgmpy VariableElimination) is unused. This is an MVP-0 scope decision, not architectural drift. It does not require a refactor, but it does represent the most valuable piece of old POE machinery that POE-A has not yet connected to.

No refactor is recommended. The boundary is correct.

---

## Task 1: Old POE Baseline

### Sibling Repository

```
/home/aaron/Documents/code/epistemic-monitor-suite/probabilistic_ontology_engine
```

### Core Engine Files

| File | Purpose |
|------|---------|
| `src/engine/engine.py` | `ProbabilisticOntologyEngine` — top-level orchestrator |
| `src/engine/schemas.py` | All data schemas: `Variable`, `DependencyEdge`, `OntologyCandidate`, `EvidenceRecord`, `ObservedAssignment`, `OntologyPopulation`, enums |
| `src/engine/services/learning.py` | `LearningService` — Level 1: CPT sufficient-statistics accumulation, log-likelihood, EM |
| `src/engine/services/edge_existence.py` | `EdgeExistenceService` — Level 2: BIC log-likelihood ratio, sigmoid/logit, edge pruning |
| `src/engine/services/population_manager.py` | `PopulationManager` — Level 3: population of competing `OntologyCandidate` objects, scoring, pruning, variant introduction |
| `src/engine/services/inference.py` | `InferenceService` — pgmpy `VariableElimination` over CPT Bayesian network; population-weighted aggregation |
| `src/engine/stores/evidence_store.py` | SQLite evidence persistence |
| `src/engine/stores/parameter_store.py` | SQLite CPT count tables |
| `src/engine/stores/population_store.py` | SQLite candidate population persistence |
| `src/engine/variable_identity.py` | `stable_variable_id()` — deterministic UUID derivation from domain and variable name |

### Old POE Epistemic Architecture (from `SPEC.md`)

Old POE operates at three levels of belief simultaneously:

```
Level 3: Structure   — competing OntologyCandidates, each scored by cumulative evidence fit
                        low-scoring candidates discarded; variants of survivors introduced
Level 2: Edge        — within each candidate, every dependency edge has existence_probability in [0,1]
                        updated by BIC log-likelihood ratio after each learning batch
                        edges below threshold are pruned
Level 1: Parameter   — within each edge, the CPT is updated by Bayesian sufficient statistics
                        (Laplace-smoothed count tables); standard Bayesian parameter learning
```

A fourth layer — inference — answers downstream queries via `pgmpy VariableElimination`.

### Active Old POE Domains (10 total)

All 10 domains use hand-authored variable vocabularies:

| Domain | Key | Variables |
|--------|-----|-----------|
| `macro_regime_v1` | MR | YieldCurveInverted, InflationShock, LiquidityStress, … (8 variables) |
| `natural_gas_v1` | NG | TempAnom, HeatingDem, StorageDraw, PriceUp |
| `ai_regime_v1` | AI | SemiconductorMomentum, HyperscalerCapexAccelerating, … (8 variables) |
| `sovereign_debt_v1` | SD | USYieldSpiking, SpreadWidening, … (8 variables) |
| `credit_cycle_v1` | CC | multiple variables |
| `energy_regime_v1` | ER | multiple variables |
| `labor_market_v1` | LM | multiple variables |
| `crypto_regime_v1` | CR | multiple variables |
| `geopolitics_v1` | GP | multiple variables |
| `sf_urban_v1` | SF | multiple variables |

POE-A's purpose is to remove the requirement for these hand-authored variable sets while feeding the same engine.

---

## Task 2: Actual Architectural Boundary

### Pipeline Stage Classification

| Stage | Files | Classification |
|-------|-------|---------------|
| Evidence loading and normalization | `evidence/loaders.py`, `evidence/normalizer.py`, `evidence/schemas.py` | POE-A induction/frontend |
| LLM concept induction | `concepts/inducer.py`, `concepts/prompts.py` | POE-A induction/frontend |
| Concept registry and consolidation | `registry/store.py`, `registry/consolidation.py`, `registry/lifecycle.py` | POE-A induction/frontend |
| Active concept selection | `registry/lifecycle.py` | POE-A induction/frontend |
| Evidence scoring — semantic path | `concepts/scorer.py`, `concepts/scorer_prompts.py` | POE-A assignment logic |
| Evidence scoring — deterministic path | `assignments/router.py`, `assignments/poe_compat.py` | POE-A assignment logic |
| Evidence scoring — prefilter analysis | `assignments/prefilter.py`, `assignments/prefilter_eval.py` | POE-A assignment analysis |
| Node translation | `artifacts/exporters.py` | POE-A adapter preparation |
| **POE adapter** | **`backends/poe_backend.py`** | **Handoff into old POE** |
| Structure learning | `src.engine.engine.ProbabilisticOntologyEngine` | Old POE backend |
| CPT parameter update | `src.engine.services.learning.LearningService` | Old POE backend |
| Edge existence update | `src.engine.services.edge_existence.EdgeExistenceService` | Old POE backend |
| Population management | `src.engine.services.population_manager.PopulationManager` | Old POE backend |
| Inference (pgmpy) | `src.engine.services.inference.InferenceService` | Old POE backend — **currently unused** |
| Reporting | `artifacts/reports.py` | POE-A reporting |
| Null backend (testing) | `backends/null_backend.py` | Legitimate test fixture |
| Backend interface protocol | `backends/interface.py` | POE-A adapter contract |

### Where the Handoff Happens

The handoff into old POE semantics occurs at one function:

```
src/poea/backends/poe_backend.py
class POEBackend
    def learn_graph(...)   ← line 162
```

**Before this call:** POE-A owns everything.  
**Inside this function:** POE-A constructs `Variable`, `OntologyCandidate`, `EvidenceRecord`, and `InducedDomainModule` objects, then calls:

```python
engine = ProbabilisticOntologyEngine(db_path=..., random_seed=...)
engine.register_domain(domain)          # old POE: builds CPTs, restores parameters
engine.activate_domain(self._domain_id)
snapshot = engine.learn(batch=records)  # old POE: Level 1 + 2 + 3
population = engine.get_population()    # old POE: extract dominant candidate
```

**After this call:** POE-A reads the resulting `OntologyPopulation` and serializes it to a graph artifact JSON.

The boundary is sharp, explicit, and exactly where the design intended it.

---

## Task 3: Search for Duplicate POE-Core Machinery

### Search Results

Searched all POE-A Python source for: `OntologyCandidate`, `OntologyPopulation`, `EvidenceRecord`, `stochastic`, `conditional`, `BIC`, `log_score`, `log_likelihood`, `CPT`, `Bayesian`, `structure_learn`, `pgmpy`.

**Files matched:**

| File | Match type | Classification |
|------|-----------|---------------|
| `backends/poe_backend.py` | Imports and calls old POE schemas and engine | **C. Legitimate old POE backend reuse** |
| `artifacts/reports.py` | Reads `candidate_summaries` and `log_score` from graph artifact JSON | **A. Thin adapter / reporting only** |
| `assignments/poe_compat.py` | Calls old POE `Pipeline.build_evidence_record`, translates to POE-A format | **B. Compatibility wrapper** |

### POE-Core Machinery Absent from POE-A

| Mechanism | Old POE location | Present in POE-A? |
|-----------|-----------------|------------------|
| CPT sufficient statistics accumulation | `services/learning.py:LearningService.accumulate()` | No |
| Bayesian EM for missing variables | `services/learning.py:LearningService.accumulate_em()` | No |
| BIC log-likelihood ratio for edges | `services/edge_existence.py:EdgeExistenceService._update_edge()` | No |
| Sigmoid/logit edge probability update | `services/edge_existence.py` | No |
| Edge pruning below threshold | `services/edge_existence.py:prune_below_threshold()` | No |
| Population candidate scoring | `services/population_manager.py:PopulationManager.update_score()` | No |
| Low-scorer pruning | `services/population_manager.py:prune_low_scorers()` | No |
| Variant introduction (explore-exploit) | `services/population_manager.py:introduce_variants()` | No |
| pgmpy VariableElimination inference | `services/inference.py:InferenceService.query()` | No |
| SQLite parameter store | `stores/parameter_store.py` | No |
| SQLite population store | `stores/population_store.py` | No |
| SQLite evidence store | `stores/evidence_store.py` | No |

**No duplicate implementation exists in POE-A for any of these mechanisms.**

---

## Task 4: Is POE-A Rebuilding POE?

**No.**

There is no parallel graph construction, no parallel structure learning, no parallel ontology reasoning, and no parallel conditional inference anywhere in POE-A source code.

The null backend (`backends/null_backend.py`) returns a trivial zero-edge graph. It is a test fixture explicitly documented as such. It performs no probabilistic inference, no CPT learning, no edge existence computation. It is not a shadow POE.

The `score_hypotheses()` method in `POEBackend` reads pre-computed `candidate_summaries` from the graph artifact. It does not re-implement scoring — it exposes what POE already computed in `learn_graph()`.

Development has not drifted toward building a second weaker POE.

---

## Task 5: Evaluation of the Final Graph Artifact

### Source and Method

The graph artifact at `artifacts/poea_graph.json` is produced by old POE's evidence-driven structure learning.

```
Learn call: engine.learn(batch=30_records, domain='poea-induced-v1')
```

Input evidence: 30 of 70 scored records (the 40 all-neutral records are dropped by `_translate_scored_evidence` because they have no `OBSERVED` or `SOFT_OBSERVED` assignments).

### Graph Artifact Analysis

| Field | Value | Epistemic basis |
|-------|-------|----------------|
| `backend` | `poe` | Old POE backend |
| `node_count` | 11 | One per active induced concept |
| `edge_count` | 1 | Dominant candidate's enabled edges |
| Edge | TrophyBuyerDemand → FreshToMarketPremium | BIC-learned |
| Edge `existence_probability` | 0.1559 | Below `accept_above=0.90`; uncertain edge |
| `candidate_count` | 10 | Population managed by `PopulationManager` |
| `active_count` | 10 | No candidates pruned (single batch) |
| `dominant_log_score` | -21.013 | Cumulative log-likelihood across 30 records |
| Evidence per candidate | 30 | One learning cycle |

### Edge Inference Mechanism

The single edge (TrophyBuyerDemand → FreshToMarketPremium, prob=0.1559) is produced by:

1. `_build_cooccurrence_edges()` creates a seed edge from co-occurrence in scored evidence
2. `LearningService.accumulate()` updates CPT count tables from 30 evidence records
3. `EdgeExistenceService.update()` computes BIC log-likelihood ratio for the edge
4. `EdgeExistenceService._update_edge()` applies `sigmoid(logit(prior) + log_lr)` → 0.1559

An existence_probability of 0.1559 means old POE assessed this edge as uncertain (prior 0.5, evidence pushed it down slightly). The edge is retained in the population but not "accepted" (threshold 0.90).

### Classification

**B. Hybrid** — primarily old POE evidence-driven structure learning, with a heuristic seed.

The seed OntologyCandidate uses co-occurrence edges (which variable pairs appear in the same evidence record with non-MISSING assignments). This is a heuristic initialization, equivalent to what old POE's domain modules provide. After the seed, old POE's full Level 1 + 2 + 3 machinery runs over the 30 evidence records.

### Important Constraint

The 95.1% neutral assignment rate means only 30 of 70 art evidence records carry any scoreable signal. With 11 variables and 30 records, the effective evidence-per-variable ratio is low (~2.7 records per variable). This limits statistical power, not architectural correctness.

---

## Task 6: Routing Audit

### Verification Results

All routing behaviors are correct.

**Art prose evidence (70 records):**

```
evidence_type: prose_text  →  semantic / SemanticLLMScorerBackend
All 70 records: mode=semantic (verified)
LLM calls made: 70 (one per record, all concepts batched)
```

**Old POE structured domains (10 domains):**

```
macro-regime-v1:       deterministic / deterministic_mapper  ✓
natural-gas-v1:        deterministic / deterministic_mapper  ✓
ai-regime-v1:          deterministic / deterministic_mapper  ✓
sovereign-debt-v1:     deterministic / deterministic_mapper  ✓
credit-cycle-v1:       deterministic / deterministic_mapper  ✓
energy-regime-v1:      deterministic / deterministic_mapper  ✓
labor-market-v1:       deterministic / deterministic_mapper  ✓
crypto-regime-v1:      deterministic / deterministic_mapper  ✓
geopolitics-v1:        deterministic / deterministic_mapper  ✓
sf-urban-v1:           deterministic / deterministic_mapper  ✓
LLM calls: 0  ✓
```

**Unknown structured evidence:**

```
evidence_type: structured_numeric, domain: unknown-domain
→ mode=deterministic → error: "No deterministic mapper registered for 'unknown-domain'"
LLM calls: 0  ✓
Routing errors: 1 (correct: fail loudly)
```

**Cache behavior:**

```
Rerun with existing_records covering active concepts → cache_hits=N, fireworks_calls_made=0  ✓
```

**Direct structured assignment:**

```
assignment_mode: direct_structured + structured_assignments metadata
→ mode=direct_structured / DirectStructuredAssignmentBackend, 0 LLM calls  ✓
```

### Routing Invariants

| Rule | Status |
|------|--------|
| Deterministic is default route | ✓ |
| Prose explicitly opted into semantic | ✓ |
| Unknown structured fails loudly | ✓ |
| Old POE mappers reused, not rebuilt | ✓ |
| LLM never decides routing | ✓ |
| Cache prevents repeat calls | ✓ |

**No routing violations found.**

---

## Task 7: Shadow Prefilter Evaluation

### Setup

- Evidence: `artifacts/evidence.json` (70 art prose records)
- Scored baseline: `artifacts/scored_evidence.json` (70 records, 38 observed non-neutral pairs)
- Concepts: `artifacts/canonical_concepts.json` (11 active concepts)
- Evaluator: `poea.assignments.prefilter_eval.PrefilterEvaluator`

### Pair Statistics

| Metric | Value |
|--------|------:|
| Total evidence/concept pairs | 770 |
| Observed non-neutral (true+false) | 38 |
| Neutral | 732 (95.1%) |
| True assignments | 35 |
| False assignments | 3 |

### Threshold Sensitivity Analysis

| Threshold | Skip% | Skipped pairs | Skipped records | False negatives | Recall | Est. Fireworks savings |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.0% | 0 | 0 | 0 | 100.0% | $0.0000 |
| 0.01 | 36.1% | 278 | 2 | 5 | 86.8% | $0.0043 |
| 0.03 | 61.0% | 470 | 5 | 12 | 68.4% | $0.0109 |
| 0.05 | 73.5% | 566 | 20 | 17 | 55.3% | $0.0435 |
| 0.10 | 93.9% | 723 | 48 | 26 | 31.6% | $0.1044 |

_Skipped records = records where all 11 concept pairs fall below threshold. Only these save a Fireworks call._
_Savings = skipped_records × ~$0.0022/call._

### False Negative Examples (threshold=0.01, the minimum non-trivial)

All 5 false negatives at threshold=0.01 have relevance=0.0 (no concept keywords in evidence text):

| Evidence | Concept | Verdict | Why missed |
|----------|---------|---------|-----------|
| "Marian Goodman's Gerhard Richters Total $78.8M in $162.7M Christie's Sale" | AuctionConcentrationDynamics | TRUE | Sparse title; LLM infers concentration from auction scale; 0 definition keywords matched |
| "SFMOMA Announces Landmark Jacob Hashimoto Installation" | InstitutionalValidationPremium | TRUE | LLM infers validation from SFMOMA context; 0 keywords matched |
| "How Did Phillips Pull Off a $115.2M White Glove Sale?" | SpeculativeDemandCollapse | FALSE | LLM infers absence of collapse from "white glove" (100% sold); 0 keywords matched |
| "How Did Phillips Pull Off a $115.2M White Glove Sale?" | TrophyBuyerDemand | TRUE | LLM infers trophy buying from scale + "white glove"; 0 keywords matched |
| "Marian Goodman's $35.1M Richter Leads Christie's $162.7M Trio" | TrophyBuyerDemand | TRUE | LLM infers trophy buying from sale scale; 0 keywords matched |

### Finding

At no positive threshold does the prefilter achieve ≥95% recall with any record-level savings.

The root cause: the LLM scores from semantic implication (financial scale, institutional names, market jargon) that keyword overlap cannot detect. The 5 false negatives at threshold=0.01 all have zero keyword overlap yet carry real epistemic signal.

**Recommendation: C. Redesign prefilter. Skipping is NOT enabled.**

The analysis is preserved in `SHADOW_PREFILTER_EVALUATION.md`.

---

## Task 8: Test Results

```
311 passed, 1 skipped, 121 warnings
```

All routing, adapter, caching, and pipeline tests pass. POE integration tests pass (including live POE structure learning with evidence). Shadow prefilter evaluation tests pass (30 tests).

---

## Architectural Summary

### What POE-A Is

```
Evidence (raw text, art articles)
    ↓
Evidence Normalization (POE-A: strips annotations, marks evidence_type)
    ↓
Concept Induction (POE-A: LLM, Fireworks, domain-agnostic prompt)
    ↓
Registry + Consolidation (POE-A: JSON artifacts, lifecycle rules)
    ↓
Active Concept Selection (POE-A: configurable thresholds)
    ↓
Assignment Router (POE-A: deterministic → old POE mappers; prose → LLM scorer)
    ↓
Evidence Scoring (POE-A: ScoredRecord artifacts with OBSERVED/MISSING assignments)
    ↓
Node Translation (POE-A: concept → POE Variable format with prior_probability=0.5)
    ↓
POE Adapter: poe_backend.py (thin adapter building Variable/OntologyCandidate/EvidenceRecord)
    ↓ ← handoff into old POE
Old POE: engine.learn() → LearningService → EdgeExistenceService → PopulationManager
    ↓
Graph Artifact (extracted from OntologyPopulation — real POE log-scores, real BIC edges)
    ↓
Reports (POE-A: reads candidate_summaries and edge list from artifact)
```

### What POE-A Is Not

POE-A does not implement:
- CPT parameter learning
- BIC edge scoring
- Population management / candidate pruning and introduction
- pgmpy inference (currently unused but available through old POE)

### What Old POE Still Contributes

Old POE provides all epistemic machinery:
- Stochastic conditionals (CPT tables, Laplace-smoothed counts)
- Conditional probability learning (sufficient statistics accumulation)
- Structure learning (BIC-based edge existence, log-likelihood scoring)
- Competing ontologies (OntologyCandidate population)
- Ontology comparison (log_score ranking, dominant candidate selection)
- Evidence-driven inference (unused: pgmpy VariableElimination)
- Explore-exploit edge proposal (PopulationManager.introduce_variants)
- Persistence across restarts (SQLite stores)

---

## Capability Gap: Unused Inference Layer

Old POE's `InferenceService` provides:
- `MARGINAL` queries: posterior P(X=true) given evidence
- `CONDITIONAL` queries: P(X | Y=true)
- `MAP` queries: most probable assignment
- `INTERVENTION` queries (do-calculus style)
- Population-weighted aggregation across OntologyCandidates

POE-A currently calls `engine.learn()` but never calls `engine.query()`.

`score_hypotheses()` in `poe_backend.py` returns pre-computed `candidate_summaries` from the graph artifact (log-scores and edge counts), not live inference results.

This is an MVP-0 scoping decision, not drift. The full inference capability is available and can be connected in Phase 12 (comparative mode) or a dedicated inference query phase.

The connection would be:
```python
result = engine.query(InferenceQuery(
    target_variables=[...],
    conditioned_on=[...],
    query_type=QueryType.MARGINAL,
    population_aggregation=PopulationAggregation.WEIGHTED_AVERAGE,
))
```

This is the highest-value old POE capability not yet connected.

---

## Routing Violations: None Found

All routing rules are correctly enforced:

| Rule | Status |
|------|--------|
| Structured → deterministic mapper | ✓ Enforced |
| Prose → semantic scorer | ✓ Enforced |
| Unknown structured → explicit error | ✓ Enforced |
| Deterministic default | ✓ Enforced |
| LLM never routes | ✓ Enforced |
| Old POE mappers reused | ✓ All 10 domains |
| Cache hit → no LLM call | ✓ Verified |

---

## What Should Happen Next

In priority order:

1. **Connect `engine.query()` (high value, low risk)**: Wire old POE's inference layer to POE-A reports. Marginal posteriors P(concept=true | all_evidence) from the dominant candidate would make the graph artifact an actual epistemic artifact rather than a structural scaffold.

2. **Improve evidence observation rate (quality)**: The 95.1% neutral rate is the primary quality limiter. Only 30 of 70 evidence records carry signal into POE. A domain with richer evidence (structured API data, financial series) would produce more informative CPT updates. This is the correct place to focus quality work.

3. **Shadow prefilter redesign (medium priority)**: The current lexical prefilter cannot safely skip any pairs. A record-level historical neutral-rate accumulator (skip records with N consecutive all-neutral prior runs) would be safe and require no LLM.

4. **Phase 12 comparative mode**: Compare induced concepts against old POE's hand-authored concept sets, graph by graph. This is the designed next phase.

---

_Audit complete. No code changes made. All findings are from reading code and running existing tests._
