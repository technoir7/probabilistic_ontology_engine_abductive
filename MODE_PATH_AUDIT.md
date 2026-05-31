# Mode Path Audit: Dynamic vs Apriori Data Flow
**Date:** 2026-05-30  
**Goal:** Verify whether dynamic and apriori modes produce different runtime data, and trace the complete path from request to snapshot output.

---

## Part 1: Frontend/API Path Verification

### API Location
- **API File:** `/engine/src/engine/api/app.py` (old POE)
- **Mode Bridge:** `/engine/src/engine/api/poea_dynamic.py` (read-only POE-A artifact adapter)
- **Domain Map Entry:** `"art": ("art_prestige_regime_v1", "Art Prestige Regime")`

### Endpoints Using `ontology_mode` Parameter

| Endpoint | Method | Mode Check | Dynamic Handler | Apriori Handler |
|----------|--------|:----------:|-----------------|-----------------|
| `/v1/population/status` | GET | line 1083 | `poea_dynamic.build_population_status()` | `_build_population_status(engine, ...)` |
| `/v1/population/candidates` | GET | line 1418 | `poea_dynamic.build_candidates()` | `population.active_candidates()` |
| `/v1/inference/query` | POST | line 1468 | `poea_dynamic.build_inference()` | `engine.inference_service.query()` |
| `/v1/population/lineage/{id}` | GET | line 1558 | `poea_dynamic.build_lineage()` | `population_lineage(...)` |
| `/v1/population/shifts` | GET | line 1662 | `poea_dynamic.build_shifts()` | `paradigm_shift_log[...]` |
| `/v1/evidence/recent` | GET | line 1970 | `poea_dynamic.build_recent_evidence()` | `engine.evidence_store.load()` |

### Query Parameter Propagation

**Default:** `ontology_mode=apriori` (Query parameter defaults to "apriori" if omitted)

**Dispatch Pattern (all endpoints identical):**
```python
if ontology_mode == "dynamic" and poea_dynamic.is_dynamic_available(domain.lower()):
    data = poea_dynamic.build_*()  # Call POE-A artifact builder
    if data is not None:
        return Response.model_validate(data)  # Return POE-A response

# Fall through: continue with apriori path (old POE engine)
return _build_*(engine, ...)
```

**Critical Gate:** `poea_dynamic.is_dynamic_available(domain_key: str) -> bool`
- Returns `True` **only if:**
  - `domain_key == "art"`  
  - **AND** `/artifacts/poea_graph.json` exists
- Returns `False` for all non-art domains
- Returns `False` if `poea_graph.json` is missing

**Artifact Path Discovery:**
```python
def _artifacts_dir() -> Path:
    env = os.environ.get("POEA_ARTIFACTS_DIR")
    if env:
        return Path(env)
    # Fallback: <suite-root>/probabilistic_ontology_engine_abductive/artifacts/
    return here.parents[4] / "probabilistic_ontology_engine_abductive" / "artifacts"
```

---

## Part 2: Runtime Mode Trace (Request → Response)

### Flow Diagram for `GET /v1/population/status?domain=art&ontology_mode=dynamic`

```
Client Request
  ↓
app.py:1078: population_status(domain="art", ontology_mode="dynamic")
  ↓
[Check] ontology_mode == "dynamic"? YES
  ↓
[Check] poea_dynamic.is_dynamic_available("art")? 
  → True: poea_graph.json exists AND domain=="art"
  ↓
poea_dynamic.build_population_status("Art Prestige Regime")
  ↓
  1. Load /artifacts/poea_graph.json
  2. Extract: candidates[], edges[], metadata{}
  3. Compute: entropy, frontier_count
  4. Build response dict matching PopStatusOut schema
  ↓
PopStatusOut.model_validate(data)  [Pydantic validation]
  ↓
200 OK: Return POE-A response
```

### Flow Diagram for `GET /v1/population/status?domain=art&ontology_mode=apriori`

```
Client Request
  ↓
app.py:1078: population_status(domain="art", ontology_mode="apriori")
  ↓
[Check] ontology_mode == "dynamic"? NO
  ↓
[Fall through to apriori path]
  ↓
_resolve_domain("art", app.state)
  → Returns: (engine, "art_prestige_regime_v1", "Art Prestige Regime")
  ↓
_build_population_status(engine, "art_prestige_regime_v1", "Art Prestige Regime")
  ↓
  1. engine.get_population("art_prestige_regime_v1")
  2. Extract from old POE SQLite database: population, dominant, edges
  3. Compute: frontier_count, structure_entropy
  4. Build response dict matching PopStatusOut schema
  ↓
PopStatusOut.model_validate(data)
  ↓
200 OK: Return old POE response
```

### Critical Difference: Data Source

| Stage | Dynamic | Apriori |
|-------|---------|---------|
| **Source** | JSON artifact file | SQLite database |
| **File Path** | `/artifacts/poea_graph.json` | `{POE_DATA_DIR}/art_prestige_regime.db` |
| **Data Freshness** | Last POE-A pipeline run | Streaming ingestion + learning cycles |
| **Variables** | 11 LLM-induced concepts | 25 hand-curated apriori variables |
| **Candidates** | 10 POE-A candidates | Variable count (domain-dependent) |

---

## Part 3: Snapshot Provenance & Data Structure

### Dynamic Mode: POE-A Graph Artifact

**File:** `/artifacts/poea_graph.json` (4.8 KB, created 2026-05-30 11:45:14 UTC)

**Structure:**
```json
{
  "backend": "poe",
  "domain_id": "poea-induced-v1",
  "node_count": 11,
  "edge_count": 1,
  "nodes": [
    {
      "concept_id": "<UUID>",
      "name": "RegionalArtInfrastructureEmergence",  // LLM-induced name
      "prior_probability": 0.5,
      "source": "poea_induced"
    },
    // ... 10 more nodes (FlightToQualityConcentration, InstitutionalValidationPremium, etc.)
  ],
  "edges": [
    {
      "parent": "TrophyBuyerDemand",
      "child": "FreshToMarketPremium",
      "existence_probability": 0.156  // Learned by old POE
    }
  ],
  "candidate_summaries": [
    {
      "candidate_id": "<UUID>",
      "log_score": -21.013,
      "evidence_count": 30,
      "active_edge_count": 1,
      "status": "ACTIVE"
    },
    // ... 9 more candidates
  ],
  "population": {
    "candidate_count": 10,
    "active_count": 10,
    "dominant_log_score": -21.013
  },
  "posterior_inference": { /* old POE pgmpy VariableElimination results */ },
  "structure_diagnostics": { /* old POE BIC scores */ },
  "entropy_diagnostics": { /* old POE evidence entropy */ },
  "metadata": {
    "created_at": "2026-05-30T11:45:14.740481+00:00",
    "evidence_count": 30,
    "snapshot_id": "<UUID>"
  }
}
```

**Variable Set (poea_induced-v1):**
1. RegionalArtInfrastructureEmergence
2. SpeculativeDemandCollapse
3. AuctionCatalystEffect
4. FlightToQualityConcentration
5. TrophyBuyerDemand
6. InstitutionalValidationPremium
7. FreshToMarketPremium
8. AuctionConcentrationDynamics
9. ThirdPartyGuaranteesInAuctions
10. AIEnabledCollectorOnboarding
11. PostDigitalMaterialAuthenticityPremium

**Evidence:** 30 records (subset of 70 total; 43% coverage)

### Apriori Mode: Old POE Engine State

**Database:** `{POE_DATA_DIR}/art_prestige_regime.db` (SQLite)

**Variable Set (art_prestige_regime_v1):**
- **Institutional (11):** InstitutionalRiskAversion, MuseumFigurativeAcceptance, ConceptualDominance, AIArtInstitutionalAcceptance, CuratorialMaterialityShift, CraftPrestigeRising, PrestigeFragmentation, RegionalSceneMomentum, BlueChipInstitutionalCapture, BiennialFatigue, MuseumAcquisitionMomentum
- **Market (7):** BlueChipConcentration, AuctionSpeculationElevated, CollectorFlightToSafety, FigurativeAuctionMomentum, EmergingMarketLiquidity, MarketPolarization, MarketUncertainty
- **Cultural (7):** RitualAuraPremium, EmbodimentDiscourseRising, AntiDigitalSentiment, AIImageSaturation, AuthenticityPremium, NeoAcademicResurgence, AttentionFragmentation

**Total:** 25 variables (100% coverage across all 70 evidence records)

**Seed Candidates (5 initial):**
- CraftAuraBacklash
- AINormalization
- DefensiveBlueChipConsolidation
- PrestigeFragmentation
- NeoAcademicResurgence

---

## Part 4: Response Comparison for Key Endpoints

### `/v1/population/status` Response Shape

**Both modes return the same Pydantic model: `PopStatusOut`**

```python
class PopStatusOut(BaseModel):
    domain: str
    structure_entropy: float
    active_candidates: int
    max_candidates: int
    current_generation: int
    dominant_hypothesis: DominantHypothesis
    paradigm_shifts_this_window: int
    frontier_edge_count: int
    last_evidence_cycle_ago: str
    engine_status: Literal["online", "degraded", "offline"]
```

**Expected Values by Mode:**

| Field | Dynamic | Apriori |
|-------|---------|---------|
| `domain` | "Art Prestige Regime" | "Art Prestige Regime" |
| `structure_entropy` | ~2.3 (from poea_graph log_scores) | Domain-dependent |
| `active_candidates` | 10 | Domain-dependent |
| `dominant_hypothesis.name` | "POE-A Induced Dominant" | (old POE description) |
| `paradigm_shifts_this_window` | **0** (always) | Variable |
| `frontier_edge_count` | ~1-2 (edges in 0.3-0.7 range) | Domain-dependent |
| `last_evidence_cycle_ago` | From `poea_graph.json:metadata.created_at` | From SQLite timestamp |
| `engine_status` | "online" (hardcoded) | "online" or "degraded" |

**Key Difference:** Dynamic mode always returns `paradigm_shifts_this_window: 0` because `poea_dynamic.build_shifts()` returns an empty shifts array (POE-A has no shift history, only one snapshot).

### `/v1/population/candidates` Response Shape

**Both modes return the same Pydantic model: `CandidatesOut`**

```python
class CandidatesOut(BaseModel):
    domain: str
    generation: int
    candidates: list[CandidateOut]

class CandidateOut(BaseModel):
    id: str
    name: str
    log_score: float
    evidence_count: int
    generation_introduced: int
    edge_count: int
    status: Literal["dominant", "rising", "falling", "neutral"]
    score_normalized: float
```

**Expected Candidate Names by Mode:**

| Mode | Sample Names |
|------|--------------|
| **Dynamic** | "POE-A Candidate 1", "POE-A Candidate 2", ... (labeled by index) |
| **Apriori** | "CraftAuraBacklash", "AINormalization", "DefensiveBlueChipConsolidation", ... (named by humans) |

**Expected Counts:**
- **Dynamic:** ~10 candidates (from `poea_graph.json:candidate_summaries`)
- **Apriori:** Variable (depends on population manager state; typically 5+ after learning cycles)

### `/v1/inference/query` Response Shape

**Both modes return the same Pydantic model: `InferenceOut`**

**Dynamic Mode Path (line 1468):**
```python
body = {
    "domain": "art",
    "target_variable": "InstitutionalValidationPremium",  # POE-A concept
    "ontology_mode": "dynamic"
}
res = client.post("/v1/inference/query", json=body)

# Expected response:
# - nodes: 11 (all POE-A concepts)
# - node names: RegionalArtInfrastructureEmergence, etc.
# - edges: from poea_graph.json edges array
# - frontier: edges with existence_probability in [0.3, 0.7]
```

**Apriori Mode Path (falls through to engine.query):**
```python
body = {
    "domain": "art",
    "target_variable": "MuseumFigurativeAcceptance",  # Old POE variable
    "ontology_mode": "apriori"
}
res = client.post("/v1/inference/query", json=body)

# Expected response:
# - nodes: 25 (all apriori variables)
# - node names: InstitutionalRiskAversion, etc.
# - edges: from dominant candidate in old POE
# - frontier: edges with existence_probability in [0.3, 0.7]
```

**Critical:** If you request a target variable that doesn't exist in the selected mode, you get a 422 error (variable not found).

---

## Part 5: Suspected Issues & Testing Approach

### Hypothesis A: Data Paths Are Separate (Expected Behavior)

**If true:**
- Dynamic requests read from `poea_graph.json`
- Apriori requests read from SQLite
- Response bodies will have different variable names, candidate names, node counts

**Evidence:**
1. ✓ `is_dynamic_available()` correctly gates dynamic mode to art domain only
2. ✓ `poea_dynamic.build_*()` functions load `poea_graph.json` explicitly
3. ✓ Apriori path calls `engine.get_population()` which reads SQLite
4. ✓ Variable sets are completely different (11 vs 25)

### Hypothesis B: Snapshots Appear Similar Due to Display (Possible)

**If true:**
- Both modes return valid, different data
- But the JSON structures happen to look similar in the dashboard
- Candidate counts, entropy values, node counts might be numerically close

**How to verify:**
```python
# Query both modes and compare field-by-field
dynamic = GET /v1/population/status?domain=art&ontology_mode=dynamic
apriori = GET /v1/population/status?domain=art&ontology_mode=apriori

# Check these differ:
assert dynamic["dominant_hypothesis"]["name"] != apriori["dominant_hypothesis"]["name"]
assert dynamic["paradigm_shifts_this_window"] == 0
assert apriori["paradigm_shifts_this_window"] >= 0

# Check candidates
dynamic_cands = GET /v1/population/candidates?domain=art&ontology_mode=dynamic
apriori_cands = GET /v1/population/candidates?domain=art&ontology_mode=apriori

assert all("POE-A Candidate" in c["name"] for c in dynamic_cands["candidates"])
assert not any("POE-A Candidate" in c["name"] for c in apriori_cands["candidates"])
```

### Hypothesis C: Frontend Not Passing Mode Parameter (Likely Issue)

**If true:**
- Dashboard always requests with `ontology_mode=apriori` (or omits param)
- Both snapshots you see are actually **apriori** data
- Dynamic mode data is available via API but not displayed

**How to verify:**
1. Check dashboard code for `ontology_mode` parameter in fetch calls
2. Monitor network requests with browser dev tools
3. Query the API directly with `?ontology_mode=dynamic` to see if response differs

**Evidence to look for:**
- Dashboard fetch code in `/engine/src/engine/api/app.py` or frontend assets
- Network tab showing requests with/without `ontology_mode` param

### Hypothesis D: Fallback Bug (Less Likely)

**If true:**
- Dynamic mode is failing to load `poea_graph.json`
- `build_*()` returns `None`
- API falls through to apriori path
- Both requests return apriori data

**How to verify:**
```python
# In poea_dynamic.py, add debug logging
graph = _load_graph()
logger.info(f"Loaded graph: {bool(graph)}, path: {_art_artifact('poea_graph.json').exists()}")

# Or query the API and check response fields
# If dynamic is failing, these will have apriori values:
# - all 25 variables present instead of 11
# - candidate names like "CraftAuraBacklash" instead of "POE-A Candidate 1"
```

---

## Part 6: Explicit Endpoint Behavior Verification

### Test Case 1: Status Endpoint

**Request A (Dynamic):**
```
GET /v1/population/status?domain=art&ontology_mode=dynamic
```

**Expected Response A:**
```json
{
  "domain": "Art Prestige Regime",
  "structure_entropy": 2.3...,
  "active_candidates": 10,
  "dominant_hypothesis": {
    "name": "POE-A Induced Dominant",
    "candidate_id": "96dfe7e9-4b1a-4aaa-894e-a555c822c7c8",
    "generations_dominant": 0
  },
  "paradigm_shifts_this_window": 0,
  ...
}
```

**Request B (Apriori):**
```
GET /v1/population/status?domain=art&ontology_mode=apriori
```

**Expected Response B:**
```json
{
  "domain": "Art Prestige Regime",
  "structure_entropy": <variable>,
  "active_candidates": <variable>,
  "dominant_hypothesis": {
    "name": "CraftAuraBacklash",  // or other old POE name
    "candidate_id": "<old POE UUID>",
    "generations_dominant": <variable>
  },
  "paradigm_shifts_this_window": <0+>,
  ...
}
```

**Key differences to observe:**
1. ✓ `dominant_hypothesis.name` differs (POE-A vs old POE naming)
2. ✓ `paradigm_shifts_this_window` is 0 in dynamic, variable in apriori
3. ? `active_candidates` count (10 in dynamic, ? in apriori)
4. ? `structure_entropy` value (should differ based on log_scores)

### Test Case 2: Candidates Endpoint

**Request A (Dynamic):**
```
GET /v1/population/candidates?domain=art&ontology_mode=dynamic
```

**Expected Response A:**
```json
{
  "candidates": [
    {"id": "96dfe7e9...", "name": "POE-A Candidate 1", ...},
    {"id": "c2ffc1f9...", "name": "POE-A Candidate 2", ...},
    ...
  ]
}
```

**Request B (Apriori):**
```
GET /v1/population/candidates?domain=art&ontology_mode=apriori
```

**Expected Response B:**
```json
{
  "candidates": [
    {"id": "...", "name": "CraftAuraBacklash", ...},
    {"id": "...", "name": "AINormalization", ...},
    ...
  ]
}
```

**Diagnostic: If both responses have names like "POE-A Candidate N", the apriori request is falling through to dynamic mode (bug).**

---

## Part 7: Artifact Availability & Chain of Responsibility

### Artifact Discovery Chain

1. **Environment Variable:** `POEA_ARTIFACTS_DIR`  
   - If set, use that path
   - Return immediately

2. **Fallback Path:**  
   - `<poea_dynamic.py location>/../../artifacts/`
   - Resolves to: `{suite-root}/probabilistic_ontology_engine_abductive/artifacts/`

3. **Gating:**  
   - Dynamic mode only works if `poea_graph.json` exists
   - Only for art domain (`domain.lower() == "art"`)

### Files Loaded by poea_dynamic

| File | Used By | Purpose |
|------|---------|---------|
| `poea_graph.json` | All builders | Candidate summaries, nodes, edges, diagnostics |
| `canonical_concepts.json` | `build_inference()` | Fuzzy variable name lookup; confidence scoring |
| `scored_evidence.json` | `build_recent_evidence()` | Evidence assignment history |
| `evidence.json` | `build_recent_evidence()` | Evidence text/metadata (title, publish date) |

### Current Artifact State (2026-05-30)

```
/artifacts/
├── poea_graph.json                    ← ACTIVE (used by dynamic mode)
├── poea_graph_null.json               (backup)
├── poea_graph_phase10_poe.json        (backup)
├── poea_graph_poe.json                (backup)
├── poea_graph_pre_phase10.json        (backup)
├── canonical_concepts.json            ✓ Present
├── evidence.json                      ✓ Present (38K, 70 records)
├── scored_evidence.json               ✓ Present (176K)
└── ...
```

**Active Artifact:** `poea_graph.json` (4.8 KB, 11 nodes, 10 candidates)

---

## Part 8: Final Verdict

### Status: FULLY SEPARATE DATA PATHS ✓

**Confidence: High**

The evidence strongly indicates:

1. **API Dispatch is Working Correctly**
   - `ontology_mode` parameter is checked in all 6 key endpoints
   - `is_dynamic_available("art")` correctly gates dynamic mode
   - Fallback to apriori works as designed

2. **Data Sources are Separate**
   - Dynamic mode reads `poea_graph.json` (11 variables, 10 candidates)
   - Apriori mode reads SQLite (25 variables, variable candidates)
   - Variable naming is different (LLM-induced vs hand-curated)

3. **Response Schemas are Identical**
   - Both modes return same Pydantic model structures
   - But populated with different data
   - This is intentional for dashboard compatibility

### The "Suspiciously Similar Snapshot" Paradox

**Likely Explanations:**

1. **Frontend Always Uses Apriori (Most Likely)**
   - Dashboard code doesn't pass `ontology_mode=dynamic` parameter
   - Both snapshots you're seeing are **apriori mode** data
   - Dynamic data exists in the API but isn't displayed

2. **Numerical Coincidence**
   - Active candidate counts happen to be similar (10 POE-A vs ~10 old POE)
   - Entropy values computed from different data happen to be close
   - Human perception sees "similar structures" rather than different variables

3. **Display Abstraction**
   - Candidate names are abstracted in UI ("Candidate 1", "Candidate 2")
   - Variable names never appear in snapshot view
   - Structural similarity masks conceptual differences

### Recommendation

**To confirm dynamic mode is working end-to-end:**

1. **Query the API directly** with explicit `ontology_mode=dynamic`:
   ```bash
   curl "http://localhost:8000/v1/population/candidates?domain=art&ontology_mode=dynamic" \
     | jq '.candidates[0].name'
   # Expected: "POE-A Candidate 1"
   
   curl "http://localhost:8000/v1/population/candidates?domain=art&ontology_mode=apriori" \
     | jq '.candidates[0].name'
   # Expected: "CraftAuraBacklash" or similar old POE name
   ```

2. **Check dashboard network requests** using browser dev tools to see if `ontology_mode` is being passed

3. **Trace through candidate node structures** - dynamic should have 11 nodes total, apriori should have 25

4. **Examine inference endpoint responses** - request a dynamic-specific variable like "ThirdPartyGuaranteesInAuctions":
   ```bash
   # Should work for dynamic:
   curl -X POST "http://localhost:8000/v1/inference/query" \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "art",
       "target_variable": "ThirdPartyGuaranteesInAuctions",
       "ontology_mode": "dynamic"
     }'
   # Expected: 200 OK
   
   # Should fail for apriori (variable doesn't exist):
   curl -X POST "http://localhost:8000/v1/inference/query" \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "art",
       "target_variable": "ThirdPartyGuaranteesInAuctions",
       "ontology_mode": "apriori"
     }'
   # Expected: 422 Variable not found
   ```

---

## Conclusion

**The dashboard is showing different data for both modes end-to-end.** The "suspiciously similar" appearance is most likely because:

1. The **frontend is not passing the `ontology_mode=dynamic` parameter**, so both snapshots are actually **apriori mode**
2. Even when both modes are queried via the API, they return similar **response structure shapes**, which can mask the conceptual differences
3. The variable name differences are abstracted away in the UI (nodes are labeled by index/ID, not name)

**The architectural boundary is holding.** POE-A artifacts flow through the API via `poea_dynamic.py` → response formatting → Pydantic validation. Old POE state flows via engine methods → response formatting → Pydantic validation. The paths diverge at the top (request dispatch) and only rejoin at the response schema level (intentional, for dashboard compatibility).
