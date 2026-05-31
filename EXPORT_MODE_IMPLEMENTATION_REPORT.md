# Export Mode Implementation Report

**Date:** 2026-05-31  
**Status:** COMPLETE — verified with live curl output

---

## Summary

The `/v1/export/narrative-snapshot` endpoint was broken: it ignored `ontology_mode` and
silently returned apriori (old POE) data regardless of what the caller requested.

This report documents the fix, design decisions, and proof of correctness.

---

## Bug Confirmed

The handler signature before this change:

```python
@app.get("/v1/export/narrative-snapshot", response_model=NarrativeSnapshotOut)
async def narrative_snapshot(domain: str = Query("ng")) -> NarrativeSnapshotOut:
```

No `ontology_mode` parameter. No dynamic dispatch. No call to `poea_dynamic`. Every call
returned old POE apriori data, regardless of `?ontology_mode=dynamic`.

All other working endpoints (`/v1/population/status`, `/v1/population/candidates`,
`/v1/inference/query`, `/v1/population/shifts`, `/v1/evidence/recent`) had already been
updated with dynamic dispatch. The export endpoint was missed.

---

## Files Changed

### 1. `probabilistic_ontology_engine/src/engine/api/app.py`

**Lines changed:** `narrative_snapshot` function signature and first dispatch block.

**Before:**
```python
@app.get("/v1/export/narrative-snapshot", response_model=NarrativeSnapshotOut)
async def narrative_snapshot(domain: str = Query("ng")) -> NarrativeSnapshotOut:
    """..."""
    engine, domain_id, display_name = _resolve_domain(domain, app.state)
```

**After:**
```python
@app.get("/v1/export/narrative-snapshot", response_model=NarrativeSnapshotOut)
async def narrative_snapshot(
    domain: str = Query("ng"),
    ontology_mode: str = Query("apriori"),
) -> NarrativeSnapshotOut:
    """..."""
    engine, domain_id, display_name = _resolve_domain(domain, app.state)
    if ontology_mode == "dynamic" and poea_dynamic.is_dynamic_available(domain.lower()):
        data = poea_dynamic.build_narrative_snapshot(display_name, domain_id)
        if data is not None:
            return NarrativeSnapshotOut.model_validate(data)
```

Pattern is identical to all other endpoints that already support dynamic dispatch.
Apriori path is unchanged — falls through to existing code when `ontology_mode != "dynamic"`
or when dynamic artifacts are unavailable.

### 2. `probabilistic_ontology_engine/src/engine/api/poea_dynamic.py`

**Added:** `build_narrative_snapshot(display_name, domain_module_id)` function.

The function assembles a `NarrativeSnapshotOut`-compatible dict from existing POE-A
artifact files. It reuses the same loaders and helpers that already exist in `poea_dynamic.py`.

---

## Design Decisions

### Honesty about probability values

`NarrativeRegimeVariableOut.probability` is named `probability` in the schema and frontend.

Old POE populates this field with real posterior probabilities from `pgmpy.VariableElimination`.
POE-A does not run posterior inference. The closest equivalent is the concept `confidence`
score: an LLM-derived support measure from the scoring pipeline.

Decision: populate `probability` with concept confidence values and make the distinction
explicit in `interpretation_hints`:

```
"DYNAMIC MODE: snapshot reflects POE-A abductive induction artifacts, not old POE posterior inference"
"probability values in current_regime_state are LLM-derived concept support scores, NOT posterior probabilities"
```

This is the correct tradeoff: keeping the schema compatible with the frontend while being
truthful to any consumer (LLM or human) reading the snapshot.

### Dominant hypothesis

Old POE has a genuine dominant via `PopulationManager` selection. POE-A does not.
The first candidate in `candidate_summaries` (already sorted by log_score in the artifact
builder) is used as the structural dominant and labeled `POE-A Candidate 1`.
`generations_dominant` is set to 0 because POE-A has no generation-based dominance tracking.

### Paradigm shifts

Set to 0 / empty list. POE-A has no paradigm shift tracking. This is accurate.

### Score gap

Computed as `log_scores[0] - log_scores[1]`. When all log scores are equal (which is
common in early POE-A runs), `score_gap_to_dominant` is 0.0. This is accurate.

### frontier_edges

Uses the same `_EXPLORE_LO` / `_EXPLORE_HI` band `[0.3, 0.7]` as all other dynamic
endpoints. With only 30 evidence records and a single edge at `existence_probability=0.156`,
no edges fall in the explore band — correctly reported as 0.

---

## Exact Code Path

```
GET /v1/export/narrative-snapshot?domain=art&ontology_mode=dynamic
  → app.narrative_snapshot()
  → _resolve_domain("art", app.state) → engine, "art_prestige_regime_v1", "Art Prestige Regime"
  → poea_dynamic.is_dynamic_available("art") → True (poea_graph.json exists)
  → poea_dynamic.build_narrative_snapshot("Art Prestige Regime", "art_prestige_regime_v1")
    → _load_graph() → artifacts/poea_graph.json
    → _load_canonical_concepts() → artifacts/canonical_concepts.json
    → assembles metadata, regime_state, dominant_hypothesis, competing_candidates,
      ontology_competition, frontier, interpretation_hints
    → returns dict
  → NarrativeSnapshotOut.model_validate(data) → HTTP 200
```

---

## Validation Results

### Import / type check

```
$ python3 -c "from engine.api import poea_dynamic; print(poea_dynamic.build_narrative_snapshot)"
<function build_narrative_snapshot at 0x7d5a65deb4c0>
```

### Pydantic model validation

```python
result = poea_dynamic.build_narrative_snapshot("Art Prestige Regime", "art_prestige_regime_v1")
snapshot = NarrativeSnapshotOut.model_validate(result)
# → OK, no ValidationError
```

### Live curl — dynamic

```
GET /v1/export/narrative-snapshot?domain=art&ontology_mode=dynamic

{
  "metadata": {
    "domain": "Art Prestige Regime",
    "domain_module_id": "art_prestige_regime_v1",
    "evidence_count": 30,
    "current_generation": 30
  },
  "current_regime_state": [
    {"name": "RegionalArtInfrastructureEmergence", "boolean_state": null, "probability": 0.9},
    {"name": "SpeculativeDemandCollapse",          "boolean_state": null, "probability": 0.9},
    {"name": "AuctionCatalystEffect",              "boolean_state": null, "probability": 0.9},
    {"name": "FlightToQualityConcentration",       "boolean_state": null, "probability": 0.85},
    {"name": "TrophyBuyerDemand",                  "boolean_state": null, "probability": 0.85},
    {"name": "InstitutionalValidationPremium",     "boolean_state": null, "probability": 0.85},
    {"name": "FreshToMarketPremium",               "boolean_state": null, "probability": 0.85},
    {"name": "AuctionConcentrationDynamics",       "boolean_state": null, "probability": 0.8},
    {"name": "ThirdPartyGuaranteesInAuctions",     "boolean_state": null, "probability": 0.8},
    {"name": "AIEnabledCollectorOnboarding",       "boolean_state": null, "probability": 0.75},
    {"name": "PostDigitalMaterialAuthenticityPremium", "boolean_state": null, "probability": 0.75}
  ],
  "dominant_hypothesis": {
    "name": "POE-A Candidate 1",
    "candidate_id": "96dfe7e9-4b1a-4aaa-894e-a555c822c7c8",
    "edge_count": 1,
    "edges": [
      {"source": "TrophyBuyerDemand", "target": "FreshToMarketPremium", "existence_probability": 0.156}
    ],
    "generations_dominant": 0,
    "log_score": -21.013
  },
  "competing_candidates": {
    "candidates": [
      {"name": "POE-A Candidate 1",  "status": "dominant", ...},
      {"name": "POE-A Candidate 2",  "status": "rising",   ...},
      ...
      {"name": "POE-A Candidate 10", "status": "falling",  ...}
    ],
    "score_gap_to_dominant": 0.0
  },
  "ontology_competition": {
    "structure_entropy": 2.303,
    "entropy_interpretation": "high",
    "active_candidates": 10,
    "paradigm_shifts_total": 0,
    "recent_shifts": []
  },
  "frontier": {"frontier_edge_count": 0, "frontier_edges": []},
  "interpretation_hints": [
    "DYNAMIC MODE: snapshot reflects POE-A abductive induction artifacts, not old POE posterior inference",
    "probability values in current_regime_state are LLM-derived concept support scores, NOT posterior probabilities",
    "ontology_mode=dynamic: 10 POE-A candidates induced from 30 evidence records",
    "structure_entropy is high (2.303): induced candidates span diverse structural hypotheses",
    "dynamic evidence base: 30 records ingested into POE-A induction pipeline",
    "no edges in explore band: induced causal structure is either sparse or well-determined"
  ]
}
```

### Live curl — apriori (unchanged behavior)

```
GET /v1/export/narrative-snapshot?domain=art&ontology_mode=apriori

{
  "metadata": {
    "domain": "Art Prestige Regime",
    "domain_module_id": "art_prestige_regime_v1",
    "evidence_count": 0,
    "current_generation": 0
  },
  "current_regime_state": [
    {"name": "InstitutionalRiskAversion",      "boolean_state": null, "probability": null},
    {"name": "MuseumFigurativeAcceptance",     "boolean_state": null, "probability": null},
    {"name": "ConceptualDominance",            "boolean_state": null, "probability": null},
    {"name": "AIArtInstitutionalAcceptance",   "boolean_state": null, "probability": null},
    {"name": "CuratorialMaterialityShift",     "boolean_state": null, "probability": null},
    ...
  ],
  "dominant_hypothesis": {
    "name": "H1: CraftAuraBacklash — AI saturation → aura premium → craft/figurative institutionalisation",
    "candidate_id": "43896255-...",
    "edge_count": 4,
    ...
  },
  "competing_candidates": {
    "candidates": [
      {"name": "H1: CraftAuraBacklash ..."},
      {"name": "H2: AINormalization ..."},
      {"name": "H3: DefensiveBlueChipConsolidation ..."},
      {"name": "H4: PrestigeFragmentation ..."},
      {"name": "H5: NeoAcademicResurgence ..."}
    ]
  },
  "ontology_competition": {
    "structure_entropy": 0.0,
    "entropy_interpretation": "low",
    "active_candidates": 5,
    "paradigm_shifts_total": 0
  }
}
```

---

## Before / After Comparison

| Field | Before (both modes) | After dynamic | After apriori |
|---|---|---|---|
| `metadata.evidence_count` | 0 (apriori) | **30** | 0 |
| `metadata.current_generation` | 0 (apriori) | **30** | 0 |
| `current_regime_state` names | InstitutionalRiskAversion, … | **RegionalArtInfrastructureEmergence, SpeculativeDemandCollapse, …** | InstitutionalRiskAversion, … |
| `dominant_hypothesis.name` | H1: CraftAuraBacklash… | **POE-A Candidate 1** | H1: CraftAuraBacklash… |
| `competing_candidates` | H1-H5 | **POE-A Candidate 1-10** | H1-H5 |
| `ontology_competition.active_candidates` | 5 | **10** | 5 |
| `interpretation_hints[0]` | "structure_entropy is low…" | **"DYNAMIC MODE: …"** | "structure_entropy is low…" |

---

## Success Criteria — Met

- [x] Export endpoint accepts `ontology_mode` parameter
- [x] Dynamic dispatch consistent with all other working endpoints
- [x] `build_narrative_snapshot()` implemented in `poea_dynamic.py`
- [x] Existing dynamic helpers reused (`_load_graph`, `_load_canonical_concepts`, `_compute_entropy`, `_normalize_log_scores`)
- [x] Apriori behavior preserved exactly
- [x] Schema compatibility preserved — frontend continues working
- [x] Dynamic snapshot contains: POE-A candidates, induced concept names, dynamic evidence counts (30)
- [x] Apriori snapshot contains: H1-H5 hypotheses, apriori variable names, apriori evidence counts (0)
- [x] No fabricated posterior probabilities — honesty enforced via `interpretation_hints`
- [x] No old POE modifications
- [x] No new ontology induction, no new learning systems, no expensive corpus jobs
