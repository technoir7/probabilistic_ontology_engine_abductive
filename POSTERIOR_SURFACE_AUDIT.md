# Posterior Surface Audit

_Date: 2026-05-30_
_Scope: What old POE computes vs. what POE-A currently surfaces_

---

## What Old POE Computes

Old POE produces the following information after a learning cycle. All of this
exists in old POE's internal state after `engine.learn()` and `engine.query()`
are called. Nothing here is invented by POE-A.

### Level 1 — Parameter Learning

| Computed by | Location | Description |
|-------------|----------|-------------|
| `LearningService.accumulate()` | `services/learning.py` | CPT count tables per variable per candidate |
| `CPTData.get_cpt_dict()` | `stores/parameter_store.py` | Full normalized CPT: P(X\|Pa(X)) for all parent configs |
| `CPTData.mle_log_likelihood()` | `stores/parameter_store.py` | Log-likelihood of all data under MLE |
| `CPTData.bic_score()` | `stores/parameter_store.py` | BIC score for a single variable |
| `CPTData.bic_score_without_parent()` | `stores/parameter_store.py` | BIC score after dropping one parent |

**Key number available:** For the dominant art candidate with 11 variables and 30
evidence records, old POE has learned P(TrophyBuyerDemand=True) ≈ current CPT value,
P(FreshToMarketPremium=True | TrophyBuyerDemand=True/False), etc.

### Level 2 — Edge Existence

| Computed by | Location | Description |
|-------------|----------|-------------|
| `EdgeExistenceService.update()` | `services/edge_existence.py` | BIC log-likelihood ratio → existence_probability per edge |
| `DependencyEdge.existence_probability` | `schemas.py` | Current P(edge exists) in [0,1] |
| `DependencyEdge.existence_prior` | `schemas.py` | Prior P(edge exists) before evidence |
| `DependencyEdge.existence_update_count` | `schemas.py` | Evidence batches that touched this edge |
| `DependencyEdge.explore_weight` | `schemas.py` | Exploration priority (higher = more uncertain) |
| `DependencyEdge.enabled` | `schemas.py` | Whether edge survived pruning |

**Key number available:** For each candidate, every edge has an `existence_probability`.
For the art domain, the one active edge (TrophyBuyerDemand → FreshToMarketPremium) has
existence_probability ≈ 0.156. This is a BIC-scored belief, not a heuristic.

### Level 3 — Population / Structure

| Computed by | Location | Description |
|-------------|----------|-------------|
| `PopulationManager.update_score()` | `services/population_manager.py` | log_score per candidate = cumulative log-likelihood |
| `OntologyPopulation.score_weights()` | `schemas.py` | Softmax-normalized weights for WEIGHTED_AVERAGE |
| `OntologyPopulation._avg_score()` | `schemas.py` | BIC-penalized average log-likelihood |
| `OntologyPopulation.dominant()` | `schemas.py` | Highest BIC-scoring active candidate |
| `OntologyPopulation.summary()` | `schemas.py` | structure_entropy, active_candidates, paradigm_shift_count |
| `build_structure_diagnostics()` | `services/structure_diagnostics.py` | Full BIC decomposition per candidate |
| `CandidateDiagnostic.avg_ll` | `services/structure_diagnostics.py` | log_score / evidence_count |
| `CandidateDiagnostic.bic_score_strict` | `services/structure_diagnostics.py` | avg_ll − bic_penalty × 1.00 |
| `CandidateDiagnostic.bic_score_explore` | `services/structure_diagnostics.py` | avg_ll − bic_penalty × 0.25 |
| `CandidateDiagnostic.edge_structure` | `services/structure_diagnostics.py` | Sorted (parent, child) pairs |

**Key insight:** Two BIC scores exist for each candidate. The strict score uses full
BIC penalty (encourages sparsity). The explore score uses 0.25× penalty (encourages
richer structure). Comparing them shows whether the dominant candidate's simplicity
reflects genuine data sparsity or over-regularisation.

### Inference Layer

| Computed by | Location | Description |
|-------------|----------|-------------|
| `InferenceService.query()` | `services/inference.py` | pgmpy VariableElimination marginals |
| `engine.query(MARGINAL, WEIGHTED_AVERAGE)` | `engine.py` | Population-weighted posteriors per variable |
| `engine.query(MARGINAL, ACTIVE_ONLY)` | `engine.py` | Dominant-candidate-only posteriors |
| `InferenceService._explain()` | `services/inference.py` | Active edge path explanations |

### Evidence Diagnostics

| Computed by | Location | Description |
|-------------|----------|-------------|
| `build_entropy_diagnostics()` | `services/evidence_diagnostics.py` | Per-variable entropy, MI matrix, unique patterns |
| `build_evidence_geometry_diagnostics()` | `services/evidence_geometry.py` | Shannon entropy, temporal transitions, state diversity |

---

## What POE-A Currently Surfaces

### In the Graph Artifact (`poea_graph.json`)

| Field | Source | Description |
|-------|--------|-------------|
| `nodes` | POE-A | Variable names, prior_probability=0.5 |
| `edges` | Old POE dominant candidate | Active edges with existence_probability |
| `edge_count` | Old POE | Count of active edges in dominant candidate |
| `candidate_summaries[].log_score` | Old POE | Cumulative log-likelihood |
| `candidate_summaries[].evidence_count` | Old POE | Evidence records processed |
| `candidate_summaries[].active_edge_count` | Old POE | Enabled edges in candidate |
| `candidate_summaries[].status` | Old POE | ACTIVE / PRUNED / ARCHIVED |
| `population.dominant_log_score` | Old POE | Max log_score among active |
| `posterior_inference.posteriors` | Old POE `engine.query()` | P(True) / P(False) per variable |
| `posterior_inference.population_summary` | Old POE | structure_entropy, paradigm_shift_count |

### In the Run Report

| Section | Content |
|---------|---------|
| Graph Summary | Edge count, edge table, backend info |
| Posterior Inference | P(True)/P(False) per variable, dominant direction |
| Backend Candidates | Per-candidate log_score, evidence_count, edge_count |
| Routing/Cost Summary | Fireworks calls, shadow prefilter shadow analysis |

---

## What Is Available But Not Surfaced

The following old POE outputs are available after `engine.learn()` but not currently
embedded in the graph artifact or run report.

### High Priority — Clear Interpretive Value

| Available from | Description | Why useful |
|----------------|-------------|-----------|
| `build_structure_diagnostics(pop, ...)` | BIC strict + explore per candidate | Shows whether sparsity is real or artifact of small N |
| `OntologyPopulation.summary().structure_entropy` | Population entropy H over score weights | Low entropy = clear winner; high entropy = candidates equally plausible |
| `CandidateDiagnostic.edge_structure` | Which edges each candidate has | Shows where candidates disagree |
| `CandidateDiagnostic.avg_ll` | Raw average log-likelihood | Disentangles evidence fit from BIC penalty |
| `DependencyEdge.existence_probability` for ALL candidates | Not just dominant | Shows contested edges |

### Medium Priority — Contextual Interpretability

| Available from | Description | Why useful |
|----------------|-------------|-----------|
| `build_entropy_diagnostics(records, variables)` | Per-variable observed entropy and MI matrix | Shows which variables are most informative and most correlated |
| Variable uncertainty ranking from posteriors | Sort variables by |P(True) − 0.5| | Immediate interpretive view: what is POE most and least certain about |
| `CPTData.get_cpt_dict()` dominant candidate | Full conditional probability tables | Shows learned relationships between parent and child |

### Lower Priority — Diagnostic / Developer

| Available from | Description | Why useful |
|----------------|-------------|-----------|
| `DependencyEdge.explore_weight` | How much exploration priority each edge has | Shows which edges POE is still investigating |
| `DependencyEdge.existence_update_count` | How many evidence batches touched each edge | Shows evidence coverage per edge |
| `pop.paradigm_shift_count` | How many times dominant candidate changed | Stability indicator |
| Mutation cycle diagnostics | dag_violations, duplicate_rejections | Shows explore-exploit activity |

---

## What Is Difficult to Interpret

### Current Artifact Problems

1. **log_score is cumulative, not normalized.** The number −21.01 tells a human nothing
   without knowing evidence_count. Old POE's `avg_ll = log_score / evidence_count` is
   more interpretable. `build_structure_diagnostics()` already computes this.

2. **All 10 candidates show identical log_score.** With only 30 evidence records
   feeding into 11 variables, the BIC penalty dominates and most candidates look
   equivalent. The `bic_score_explore` column (0.25× penalty) would reveal if
   richer structures would win under relaxed regularization.

3. **existence_probability=0.156 is opaque.** The report shows this number but not
   what it means relative to the prune threshold (0.05) or accept threshold (0.90).
   Providing context (frontier / accepting / pruning) would help.

4. **Posterior inference P(True) is missing from current artifact.** The
   `posterior_inference` key is present in newly written code but the existing
   `poea_graph.json` was created before the last commit, so it's empty. A fresh
   `poea pipeline` run is needed.

5. **Variable uncertainty is not ranked.** The posteriors section lists P(True) for
   each variable but does not sort by uncertainty or flag highly uncertain variables.

---

## Summary

Old POE computes substantially more than POE-A currently exposes. The additions
with highest interpretive value:

1. **BIC decomposition per candidate** (`build_structure_diagnostics` — pure function, zero cost)
2. **Variable uncertainty ranking** (sort posteriors by |P(True) − 0.5|, already have data)
3. **Structure entropy and stability** (`pop.summary()`, already called)
4. **Evidence entropy / MI** (`build_entropy_diagnostics` — pure function, zero cost)
5. **Edge context labels** (frontier / accepting / rejected relative to thresholds)
