# Query Template Design

_Date: 2026-05-30_
_Scope: Useful questions POE-A can ask old POE after learning_

---

## Principle

All query templates below use **existing old POE capabilities only**. No new
inference logic exists in POE-A. Each template maps to a specific old POE
function or API call.

POE-A's role is to:
1. Format the question as an `InferenceQuery` or diagnostic call
2. Pass it to old POE
3. Present the result in a human-readable format

---

## Template 1: Variable Marginal Posteriors

**Question:** What does old POE currently believe about each variable?

**Old POE call:**
```python
result = engine.query(InferenceQuery(
    domain_module_id=domain_id,
    target_variables=all_variable_names,
    query_type=QueryType.MARGINAL,
    population_aggregation=PopulationAggregation.WEIGHTED_AVERAGE,
))
```

**Output shape:**
```json
{
    "VariableName": {"True": 0.72, "False": 0.28}
}
```

**Interpretation tiers:**
- P(True) > 0.65 → "active" (concept present in evidence)
- P(True) < 0.35 → "absent" (concept actively absent)
- 0.35 ≤ P(True) ≤ 0.65 → "uncertain" (insufficient evidence)

**Status:** Implemented in `_run_posterior_query()`, embedded in graph artifact.

---

## Template 2: Variable Uncertainty Ranking

**Question:** Which variables is old POE most and least certain about?

**Old POE data source:** posterior_inference.posteriors (already computed by Template 1)

**Derivation in POE-A (presentation only):**
```python
uncertainty = {name: abs(p_true - 0.5) for name, p_true in posteriors.items()}
sorted_by_uncertainty = sorted(uncertainty.items(), key=lambda x: x[1])
```

`abs(P(True) − 0.5)` = 0 means maximum uncertainty (P=0.5); = 0.5 means
maximum certainty (P=0 or P=1).

**No new inference.** This is arithmetic over old POE's already-computed posteriors.

**Status:** Implemented in report section `_append_posterior_inference()` (direction field),
but not yet as an explicit ranked table. Planned for Phase 3.

---

## Template 3: Structure Comparison Across Candidates

**Question:** Which candidates disagree most, and on what edges?

**Old POE call:**
```python
from src.engine.services.structure_diagnostics import build_structure_diagnostics
diags = build_structure_diagnostics(
    pop=engine.get_population(domain_id),
    mutation_stats={},
    total_evidence_records=len(records),
    env_mode="strict",
    env_bic_multiplier=1.0,
)
```

**Useful fields per candidate:**
- `edge_structure` — sorted (parent, child) pairs in this candidate
- `bic_score_strict` — how this candidate scores under full BIC penalty
- `bic_score_explore` — how it would score under relaxed BIC (0.25× penalty)
- `is_dominant` — whether this is the current winner

**Population disagreement metric:**
```python
all_edges = {edge for c in diags.candidates for edge in c.edge_structure}
contested_edges = {
    edge: sum(1 for c in diags.candidates if edge in c.edge_structure)
    for edge in all_edges
}
# Edges present in some but not all candidates are contested
```

**Status:** `build_structure_diagnostics` exists in old POE. Not yet called from
poe_backend.py. Planned for Phase 3.

---

## Template 4: BIC Score Decomposition

**Question:** Is the dominant candidate winning because it fits evidence better,
or because it has fewer parameters?

**Old POE source:** `build_structure_diagnostics()` → `CandidateDiagnostic`

**Key comparison:**
- `avg_ll` — raw fit quality (higher is better evidence fit)
- `bic_score_strict` — avg_ll minus full BIC penalty (sparse structures win)
- `bic_score_explore` — avg_ll minus 0.25× BIC penalty (richer structures emerge)

**Interpretation:**
- If dominant under strict AND explore: simplicity reflects genuine data
- If dominant under strict only: BIC penalty driving the result; with more
  evidence richer structures might emerge
- If explore would prefer a different candidate: current dominance is
  artifact of small N, not better fit

**Status:** Pure function available in old POE. Planned for Phase 3.

---

## Template 5: Edge Existence Context

**Question:** Which edges are accepted, frontier, or heading toward pruning?

**Old POE source:** `DependencyEdge.existence_probability` + `EdgeExistenceThresholdConfig`

**Context labels (using default thresholds: prune=0.05, accept=0.90, explore=(0.3, 0.7)):**
```python
def edge_label(p: float, thresholds) -> str:
    if p >= thresholds.accept_above:   return "accepted"
    if p <= thresholds.prune_below:    return "pruning"
    if thresholds.explore_band[0] <= p <= thresholds.explore_band[1]:
        return "frontier"
    return "tending_toward_pruning" if p < 0.3 else "tending_toward_acceptance"
```

**For the art domain current artifact:**
- TrophyBuyerDemand → FreshToMarketPremium: p=0.156 → **tending toward pruning**
  (below explore band lower bound of 0.3; not yet at prune threshold of 0.05)

**Status:** All data available in graph artifact. Label computation is pure
presentation arithmetic. Planned for Phase 3.

---

## Template 6: Evidence Entropy and Mutual Information

**Question:** Which variable pairs have the strongest empirical co-occurrence?
Which variables are most informative?

**Old POE call:**
```python
from src.engine.services.evidence_diagnostics import build_entropy_diagnostics
diag = build_entropy_diagnostics(records, variables)
# diag["pairwise_mutual_information"] — list of {variable_x, variable_y, MI}
# diag["variables"][name]["entropy"] — per-variable Shannon entropy
```

**Requires:** Old POE `EvidenceRecord` objects (available during `learn_graph()`).

**Interpretation:**
- High MI(X, Y) → X and Y co-occur in evidence; edge X→Y or Y→X is plausible
- Low entropy for variable X → X has a dominant state; little signal for learning
- High entropy → variable is genuinely mixed; good for CPT learning

**Status:** Pure function in old POE. Not yet called from poe_backend.py.
Planned for Phase 3.

---

## Template 7: Conditional Query (Currently Unused)

**Question:** If TrophyBuyerDemand is active, what does that imply for related variables?

**Old POE call:**
```python
result = engine.query(InferenceQuery(
    domain_module_id=domain_id,
    target_variables=["FreshToMarketPremium", "AuctionCatalystEffect"],
    conditioned_on=[ObservedAssignment(
        variable_id=trophy_variable.variable_id,
        observed_value=True,
        missingness=MissingnessType.OBSERVED,
    )],
    query_type=QueryType.MARGINAL,
    population_aggregation=PopulationAggregation.ACTIVE_ONLY,
    explain=True,  # get path explanations
))
```

**Returns:** P(FreshToMarketPremium=True | TrophyBuyerDemand=True), with active
edge path explanations.

**Status:** Fully implemented in old POE `InferenceService`. Not exposed by POE-A.
Suitable for post-pipeline query API. Would need variable_id lookup from concept
registry. Deferred to Phase 12 (comparative mode) or dedicated query phase.

---

## Template 8: Population Stability

**Question:** Is the dominant candidate stable or are we in a paradigm shift?

**Old POE source:** `pop.summary()` → `paradigm_shift_count`, `structure_entropy`

**Interpretation:**
- `paradigm_shift_count = 0` → dominant candidate has never changed
- `structure_entropy` near 0 → population has converged to one strong candidate
- `structure_entropy` near log(N) → all N candidates are equally plausible

For the art domain with 1 learning batch:
- `paradigm_shift_count` will be 0 (single batch, no shift)
- `structure_entropy` will be near log(10) ≈ 2.3 (10 equally-scored candidates)

**Status:** Available from `pop.summary()` which is called during posterior query.
Embedded in `population_summary`. Already in run report. No additional implementation needed.

---

## Implementation Priority

| Template | Old POE call | Phase 3 scope | Status |
|----------|-------------|--------------|--------|
| 1. Marginals | `engine.query()` | Done | Implemented |
| 2. Uncertainty ranking | Arithmetic over posteriors | Report only | Planned |
| 3. Structure comparison | `build_structure_diagnostics()` | Artifact + report | Planned |
| 4. BIC decomposition | `build_structure_diagnostics()` | Artifact + report | Planned |
| 5. Edge context labels | Arithmetic over edge data | Report only | Planned |
| 6. Evidence entropy/MI | `build_entropy_diagnostics()` | Artifact + report | Planned |
| 7. Conditional query | `engine.query(conditioned_on=...)` | Deferred | Not yet |
| 8. Population stability | `pop.summary()` | Done | Implemented |

Templates 3, 4, and 6 require additional calls in `poe_backend.py`.
Templates 2, 5, and 8 require only presentation changes in `reports.py`.
Template 7 requires a more complex adapter and is deferred.
