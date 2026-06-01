# MR Dynamic Induction Plan

**Date:** 2026-05-31  
**Status:** Planning only — no code written

---

## Final Verdict

**B. MR requires moderate adapter work but is still the best next domain.**

The major infrastructure already exists. What is missing is a SQLite evidence
extractor and a concept bootstrap script — not architecture. The right induction
strategy for MR is the deterministic path, not the LLM text path. This matters
enormously for cost and for epistemic integrity.

---

## Architecture Diagram

```
OLD POE SIDE                          POE-A SIDE
──────────────────────                ──────────────────────────────────────────
macro_regime.db                       
  └─ evidence_records table           
       4,119 rows                     
       source_type: API               
       8 soft-bool assignments        
                │                     
                │  [MISSING]          
         SQLite exporter              
         (extract_mr_evidence.py)     
                │                     
                ▼                     
         mr_evidence/                 
           mr_evidence.json           ←── EvidenceUnit list
           (api_derived type)               evidence_id, source, title,
                │                           text, metadata.evidence_type
                │                           metadata.old_poe_snapshot
                │                     
       ┌────────┴──────────────────────────────┐
       │                                       │
       │  STAGE 1: Concept bootstrap           │
       │  [MISSING]                            │
       │  Option A: init from domain variables │
       │  Option B: human-authored concepts    │
       │                                       │
       │  → canonical_concepts.json (mr)       │
       │    8+ concepts from domain variables  │
       └────────┬──────────────────────────────┘
                │
                ▼
       poea score-evidence                     
         AssignmentRouter.default()            
           evidence_type=api_derived           
             → DeterministicMapperBackend      
               → OldPOEDomainMapperAdapter     ← ALREADY EXISTS (poe_compat.py)
                   domain: macro-regime-v1     ← ALREADY REGISTERED
                   MacroRegimePipeline         ← ALREADY EXISTS
                   .build_evidence_record()    ← ALREADY EXISTS
                │
                ▼
         scored_evidence.json (mr)
         0 LLM calls
                │
                ▼
       poea run-backend --backend poe          
         POEBackend.learn_graph()              ← ALREADY EXISTS (poe_backend.py)
         domain_id: macro-regime-v1            
                │
                ▼
         poea_graph_mr.json                   
         canonical_concepts_mr.json           
                │
                ▼
       poea_dynamic.py                        
         _artifacts_dir() → mr artifacts dir  ← needs multi-domain support
         is_dynamic_available("mr")           ← currently hardcoded to art only
         build_*() functions                  ← already domain-agnostic
                │
                ▼
       Frontend: MR dynamic mode shows
         induced concept names
         dynamic candidate structures  
         4,119 evidence record count
```

---

## 1. Where MR Evidence Currently Lives

**Primary source:** old POE SQLite database.

Live DB location during server operation:
```
/tmp/poe_test/macro_regime.db  (Railway-deployed path or local test path)
```

Known backup with data:
```
/home/aaron/Documents/code/epistemic-monitor-suite/backups/2026-05-27/macro_regime.db
```

**Table:** `evidence_records`  
**Row count:** 4,119  
**Date range:** 2024-05-26 to 2026-05-25  
**Schema:**
```sql
evidence_id    TEXT    -- UUID
domain_module  TEXT    -- "macro-regime-v1"
timestamp      TEXT    -- ISO 8601 UTC
source_type    TEXT    -- "API"
source_ref     TEXT    -- "FRED:T10Y2Y+CPIAUCSL+...@week-ending-2026-04-03"
confidence     REAL    -- 1.0 for full FRED data
assignments    TEXT    -- JSON: list of 8 SOFT_OBSERVED boolean assignments
```

**Sample assignment (one of 8 per record):**
```json
{
  "variable_id": "e385c558-0083-5dea-bc0c-874a0eea58f9",
  "observed_value": false,
  "missingness": "SOFT_OBSERVED",
  "confidence": 1.0,
  "probabilities": { "true": 0.150, "false": 0.850 }
}
```

There is **no prose text** in MR evidence. Each record is a set of soft-boolean
signals derived from 8 FRED series. The `source_ref` is the only human-readable
field.

---

## 2. How ART Evidence Entered POE-A Induction

**Reference path (ART):**

```
art-market-domain/data/manual_ingest/
  └─ multiple JSON files
       each file: list of dicts with {title, text, published_at, url, ...}
       evidence_type: prose_text (set by normalizer when domain_tag=="art")
               │
               ▼
poea ingest --input <dir> --domain art
  → load_from_path() → normalize_record()
  → EvidenceUnit.text = full prose article
  → metadata["evidence_type"] = "prose_text"
               │
               ▼
poea induce --evidence artifacts/evidence.json
  → ConceptInducer.induce(units)
  → LLM reads prose text, extracts structural mechanisms
  → raw_concepts.json: 21 raw concepts
               │
               ▼
poea consolidate
  → build_registry() → 11 active canonical concepts
               │
               ▼
poea score-evidence --backend poe
  → AssignmentRouter.default()
  → evidence_type=prose_text → SemanticLLMScorerBackend
  → LLM scores each record against each concept
  → 70 LLM calls, ~$0.20
               │
               ▼
poea run-backend --backend poe --domain-id art_prestige_regime_v1
  → POEBackend.learn_graph()
  → 11 nodes, 1 edge
  → poea_graph.json
```

**The key:** ART induction worked because the evidence IS prose text. The LLM
can read art market reports and discover that "TrophyBuyerDemand" and
"AuctionCatalystEffect" are structural mechanisms. This is genuine concept
discovery.

---

## 3. Whether MR Can Reuse the ART Pipeline Unchanged

**No, and this is the most important architectural finding.**

The ART pipeline uses LLM concept induction on prose text. MR evidence contains
no prose text — only numerical soft-boolean assignments derived from FRED series.

**Running LLM induction on MR evidence would be epistemically wrong:**

```
MR evidence.text (if converted naively):
  "YieldCurveInverted: False (p=0.150)
   InflationShock: False (p=0.288)
   LiquidityStress: True (p=0.873)
   ..."
```

The LLM would read this text and "induce" concepts like... the 8 variables that
already exist. It would reproduce the existing apriori ontology at $10+ cost.
This is not value. The concepts are already known and precisely defined.

**The correct path for MR is deterministic, not inductive:**

MR evidence already encodes exactly what happened: 8 soft-boolean signals with
calibrated probabilities. POE-A should route this through the deterministic
mapper (`OldPOEDomainMapperAdapter`) to map assignments onto concepts, then run
the POE backend for structure learning.

The "dynamic" insight for MR is not from newly discovered concepts. It is from
observing which CAUSAL STRUCTURES best explain 4,119 weeks of evidence — a
question that old POE already answers but which can now be surfaced in the
dynamic view.

---

## 4. Which Adapters Already Exist

All the following are already implemented and usable for MR:

### poe_compat.py — OldPOEDomainMapperAdapter

```python
# src/poea/assignments/poe_compat.py:25
_OLD_POE_DOMAIN_SPECS: tuple[OldPOEDomainMapperSpec, ...] = (
    OldPOEDomainMapperSpec(
        "macro-regime-v1",
        "macro_regime_v1",
        "MacroRegimePipeline",
        "MacroRegimeSnapshot"
    ),
    ...
)
```

`discover_old_poe_domain_mappers()` returns an adapter keyed on `"macro-regime-v1"`,
`"macro_regime_v1"`, and `"macro_regime_v1"` that:
1. Calls `MacroRegimePipeline.build_evidence_record(snapshot)` or uses pre-built records
2. Translates old POE `EvidenceRecord` → POE-A `ScoredRecord`

### assignments/router.py — DeterministicMapperBackend

Already handles `evidence_type = "api_derived"` by routing to the OldPOEDomainMapperAdapter.

### backends/poe_backend.py — POEBackend

Already accepts any domain_id. Running with `--domain-id macro-regime-v1` will
reuse the variable UUIDs from `MacroRegimeV1.get_variables()` — so the resulting
graph nodes will match the existing old POE domain exactly.

### concepts/inducer.py, consolidate — not needed

Concept induction is an LLM step. It is NOT needed for MR. MR concepts come
from the domain variable definitions directly.

---

## 5. Which Adapters Are Missing

### Missing #1: SQLite Evidence Extractor

**File to create:** `scripts/extract_mr_evidence.py`

No code exists to read old POE SQLite and produce `EvidenceUnit` JSON. This is
the main missing piece.

What it must do:
- Open `macro_regime.db`
- Read `evidence_records` table
- For each row:
  - Construct `EvidenceUnit` with:
    - `evidence_id`: from row (UUID string)
    - `source`: `"macro_regime.db"`
    - `title`: constructed from source_ref, e.g. `"Macro Regime Week 2026-04-03"`
    - `published_at`: from timestamp
    - `domain_tag`: `"mr"`
    - `text`: constructed description (see below)
    - `metadata.evidence_type`: `"api_derived"`
    - `metadata.old_poe_evidence_record`: the full serialized `EvidenceRecord`
      dict (this is what `OldPOEDomainMapperAdapter._build_old_poe_record()` reads)
- Write list to `mr_artifacts/evidence.json`

The `text` field for induction purposes should be a minimal representation:
```
"Macro Regime Evidence — week ending 2026-04-03.
Source: FRED:T10Y2Y+CPIAUCSL+WALCL+BAMLH0A0HYM2+VIXCLS+DEXUSEU+UNRATE+NASDAQCOM"
```
(No numeric data — the LLM must not see this. Numeric values go in `old_poe_evidence_record`.)

### Missing #2: Concept Bootstrap from Domain Variables

**File to create:** `scripts/init_mr_concepts.py` (or a new CLI command)

For MR, canonical concepts = the 8 domain variables. These already have precise
definitions in `domain.py`. We do not need LLM induction.

What it must produce — `mr_artifacts/canonical_concepts.json`:
```json
{
  "metadata": {
    "domain_tag": "mr",
    "source": "macro_regime_v1 domain variables",
    "promoted_at": "2026-05-31T..."
  },
  "concepts": [
    {
      "concept_id": "e385c558-0083-5dea-bc0c-874a0eea58f9",
      "name": "YieldCurveInverted",
      "definition": "10Y minus 2Y Treasury yield spread is negative (inverted). Signal: structural monetary tightening.",
      "confidence": 1.0,
      "supporting_evidence_ids": [],
      "occurrence_count": 4119,
      "status": "active",
      "merged_into": null,
      "source_concept_ids": []
    },
    ... (8 total, one per variable)
  ]
}
```

The concept_ids MUST match the variable UUIDs from `stable_variable_id("macro-regime-v1", name)`.
This ensures the `OldPOEDomainMapperAdapter` alignment works: variable_id → concept_id → POE node.

### Missing #3: Multi-Domain Artifact Discovery

**File to modify:** `probabilistic_ontology_engine/src/engine/api/poea_dynamic.py`

Currently hardcoded to ART:
```python
# poea_dynamic.py:27-32
def _art_artifact(name: str) -> Path:
    return _artifacts_dir() / name

def is_dynamic_available(domain_key: str) -> bool:
    return domain_key == "art" and _art_artifact("poea_graph.json").exists()
```

Needs domain-keyed artifact lookup:
```python
def _domain_artifact_dir(domain_key: str) -> Path:
    base = _artifacts_dir()
    if domain_key == "art":
        return base  # existing layout unchanged
    return base / domain_key  # e.g., artifacts/mr/poea_graph.json

def is_dynamic_available(domain_key: str) -> bool:
    return _domain_artifact_dir(domain_key) / "poea_graph.json"
```

This is a small change (10-15 lines) but it must be done to enable MR dynamic mode.

### Missing #4: MR Config File

**File to create:** `configs/mr_induction_config.yaml`

```yaml
backend:
  domain_id: macro-regime-v1   # matches old POE domain — MUST be exact
  default: poe
  poe_path: ../probabilistic_ontology_engine

concepts:
  # No LLM induction for MR — use domain variables directly
  # promotion_confidence not applicable
  max_active_concepts: 8

scoring:
  # api_derived → deterministic → 0 LLM calls
  soft_observed_threshold: 0.5
```

---

## 6. Required Artifact Formats

The following files must be produced, in `artifacts/mr/`:

| Artifact | Format | Source | Notes |
|---|---|---|---|
| `evidence.json` | `list[EvidenceUnit]` | SQLite extractor | 4,119 records |
| `canonical_concepts.json` | POE-A canonical concepts | Domain variable bootstrap | 8 concepts, IDs match variable UUIDs |
| `scored_evidence.json` | POE-A scored records | Deterministic mapping | 0 LLM calls |
| `nodes.json` | POE-A nodes artifact | `poea export-nodes` | 8 nodes |
| `poea_graph.json` | POE-A graph artifact | `poea run-backend --backend poe` | same format as ART |
| `run_report.md` | Markdown report | `poea report` | |

No `raw_concepts.json` or `concept_registry.json` needed (induction skipped).

---

## 7. Implementation Sequence

### Step 0: Confirm live DB access
```bash
sqlite3 /tmp/poe_test/macro_regime.db "SELECT COUNT(*) FROM evidence_records"
# Expected: 4119 (or similar)
```

### Step 1: Write `scripts/extract_mr_evidence.py` (2-3 hours)
- Read SQLite `evidence_records`
- For each row: deserialize assignments JSON, rebuild dict with `old_poe_evidence_record`
- Produce `artifacts/mr/evidence.json`
- Test: `python scripts/extract_mr_evidence.py && wc -l artifacts/mr/evidence.json`

### Step 2: Write `scripts/init_mr_concepts.py` (1 hour)
- Import `MacroRegimeV1.get_variables()` from old POE
- Write `canonical_concepts.json` with 8 concepts, IDs matching variable UUIDs
- Set all `status: "active"` directly (no promotion needed)
- Test: validate JSON structure matches POE-A schema

### Step 3: Create `configs/mr_induction_config.yaml` (15 minutes)
- Domain-specific config pointing to `macro-regime-v1`
- No LLM induction params needed

### Step 4: Run scoring (deterministic, 0 LLM calls)
```bash
.venv/bin/python -m poea score-evidence \
  --concepts artifacts/mr/canonical_concepts.json \
  --evidence artifacts/mr/evidence.json \
  --output artifacts/mr/scored_evidence.json \
  --config configs/mr_induction_config.yaml
# Expected: 0 LLM calls, 4119 records × 8 concepts scored deterministically
```

### Step 5: Export nodes
```bash
.venv/bin/python -m poea export-nodes \
  --concepts artifacts/mr/canonical_concepts.json \
  --output artifacts/mr/nodes.json \
  --domain mr
```

### Step 6: Run POE backend
```bash
.venv/bin/python -m poea run-backend \
  --backend poe \
  --concepts artifacts/mr/canonical_concepts.json \
  --scored-evidence artifacts/mr/scored_evidence.json \
  --output artifacts/mr/poea_graph.json \
  --domain-id macro-regime-v1 \
  --config configs/mr_induction_config.yaml
# Expected: 8 nodes, 5-10 edges, learning from 4119 records
```

### Step 7: Update `poea_dynamic.py` for multi-domain (1 hour)
- Generalize `_art_artifact()` → `_domain_artifact(domain_key, name)`
- Generalize `is_dynamic_available(domain_key)` to check `artifacts/{domain_key}/poea_graph.json`
- Verify all existing `build_*()` functions are already domain-key-aware
  (they are: they just load graph, concepts, scored_evidence from file)

### Step 8: Validate
```bash
# Start server, then:
curl "http://localhost:8000/v1/population/candidates?domain=mr&ontology_mode=dynamic"
# Should return MR concepts (8 macro variables)

curl "http://localhost:8000/v1/export/narrative-snapshot?domain=mr&ontology_mode=dynamic"
# Should return evidence_count≈4119, concept names = YieldCurveInverted etc.
```

---

## 8. Estimated Implementation Effort

| Task | Effort | Risk |
|---|---|---|
| `extract_mr_evidence.py` | 2-3 hours | Low — SQLite read + JSON write |
| `init_mr_concepts.py` | 1 hour | Low — trivial import + write |
| `configs/mr_induction_config.yaml` | 15 min | Low |
| Multi-domain `poea_dynamic.py` update | 1 hour | Low — localized change |
| Validation and debugging | 1-2 hours | Medium |
| **Total** | **5-7 hours** | **Low-Medium** |

---

## 9. Estimated Induction Runtime

| Stage | Duration | Notes |
|---|---|---|
| SQLite extract | < 1 minute | 4,119 rows, no I/O bottleneck |
| Concept bootstrap | < 1 second | Local dict write |
| Score-evidence (deterministic) | 2-5 minutes | 4,119 × 8 assignments, no LLM |
| POE backend (learn_graph) | 5-20 minutes | Old POE Bayesian learning, 4,119 records, 8 variables |
| Export nodes | < 1 second | |
| Artifact write | < 1 second | |
| **Total** | **~10-25 minutes** | Dominated by old POE structure learning |

---

## 10. Estimated LLM/API Cost

| Phase | LLM calls | Cost |
|---|---|---|
| Evidence extraction | 0 | $0.00 |
| Concept bootstrap | 0 | $0.00 |
| Scoring (deterministic, api_derived) | 0 | $0.00 |
| POE backend | 0 | $0.00 |
| **Total** | **0** | **$0.00** |

MR is a fully deterministic induction. The `OldPOEDomainMapperAdapter` translates
evidence to concept assignments using `MacroRegimePipeline.build_evidence_record()`,
which is a pure function with no external calls.

**Contrast with ART:** ART cost ~$0.28 for 70 records. Scaling ART's approach to
MR's 4,119 records with semantic scoring would cost approximately:
4,119 × $0.004/record ≈ $16.50. The deterministic path costs $0.

---

## 11. Major Risks

### Risk 1: UUID alignment
**Description:** The `canonical_concepts.json` concept IDs must exactly match the
`variable_id` values from `stable_variable_id("macro-regime-v1", name)`. If they
don't, the `OldPOEDomainMapperAdapter.translate_old_poe_evidence_record()` will
produce unmatched assignments and all scores will be MISSING.

**Mitigation:** Import the exact same `stable_variable_id` function in the concept
bootstrap script. Verify by cross-checking one concept_id against a SQLite assignment:
```python
from src.engine.variable_identity import stable_variable_id
assert str(stable_variable_id("macro-regime-v1", "YieldCurveInverted")) \
    == "e385c558-0083-5dea-bc0c-874a0eea58f9"  # from actual SQLite data
```

### Risk 2: Neutral rate
**Description:** If the deterministic mapper produces 95%+ MISSING assignments
(as in ART's semantic scoring), the POE backend will have almost no signal.
Unlike ART where neutrals came from evidence/concept mismatch, MR should have
high signal because each record directly encodes 8 boolean assignments that
exactly match the 8 domain variables.

**Expected outcome:** Near-zero neutral rate (every record has an assignment for
every variable). If neutrals appear, the UUID alignment is broken.

### Risk 3: Evidence record not in correct format
**Description:** `OldPOEDomainMapperAdapter._build_old_poe_record()` looks for
`metadata.old_poe_evidence_record`. If the extractor stores this field incorrectly
or the schema changed, the adapter will fall through to the `raise OldPOEMapperError`.

**Mitigation:** The extractor must serialize the assignment list using the exact
schema expected by `_coerce_old_evidence_record()` → `EvidenceRecord.model_validate()`.
Test one record end-to-end before processing all 4,119.

### Risk 4: MR has 4,119 records but old POE backend may be slow
**Description:** `POEBackend.learn_graph()` calls `engine.learn(batch=records, ...)`.
Processing 4,119 records through old POE's Bayesian structure learning may take
longer than expected or exhaust memory.

**Mitigation:** POE backend already handles MR's 4,119 records in production
(the live MR engine has been running for 2 years). The issue is that
`learn_graph()` calls it in batch mode vs. incremental mode. May need to
chunk or test on a subset (500 records) first.

### Risk 5: `poea_dynamic.py` multi-domain changes break ART
**Description:** Generalizing `_art_artifact()` to domain-keyed lookup could
break the existing ART path if the path resolution changes.

**Mitigation:** Keep ART's `artifacts/` root path unchanged. Add MR as a
subdirectory `artifacts/mr/`. Test ART dynamic mode after the change.

---

## 12. Validation Strategy

### Unit validation (before running full pipeline)
1. Verify UUID alignment: `stable_variable_id("macro-regime-v1", "YieldCurveInverted") == "e385c558-..."`
2. Verify OldPOEDomainMapperAdapter imports without errors for MR
3. Test one evidence record through the full mapping chain on a single record

### Pipeline validation (after scoring)
1. `scored_evidence.json` should have 4,119 records × 8 concepts = 32,952 pairs
2. Expected neutral rate: < 5% (vs. 95% for ART — these variables exactly match the evidence)
3. LLM calls in routing metadata: should be 0

### Backend validation
1. `poea_graph.json` should have 8 nodes (one per variable)
2. Edge count: > 0 (MR has 4,119 records of learning signal — should find structure)
3. Population: ≥ 5 candidates (old POE creates the initial 5 seed candidates for MR)

### API validation
```bash
# Dynamic candidates differ from apriori
curl ".../v1/population/candidates?domain=mr&ontology_mode=dynamic"
# → should return MR concept names (YieldCurveInverted, InflationShock, etc.)
# → evidence_count ≈ 4119 (not 0)

curl ".../v1/export/narrative-snapshot?domain=mr&ontology_mode=dynamic"
# → metadata.evidence_count ≈ 4119
# → interpretation_hints contain "DYNAMIC MODE"
# → dominant_hypothesis from POE structure learning
```

---

## Why MR and Not Another Domain

| Domain | Evidence | Type | Induction path | Cost | Verdict |
|---|---|---|---|---|---|
| **MR** | 4,119 | FRED numeric | Deterministic (0 LLM) | $0 | **Best** |
| AI | ~742 | FRED numeric | Deterministic (0 LLM) | $0 | Good, but smaller |
| ER | ~324 | FRED numeric | Deterministic (0 LLM) | $0 | Smaller |
| GP | ~200 | GDELT events + FRED | Could do LLM induction on GDELT text | ~$1-3 | Medium effort, smaller |
| ART | 70 done | Prose text | Already done | Done | N/A |

MR is the right choice:
1. Largest evidence base by far (4,119 vs 742 next)
2. Most paradigm shifts (6) = most learning signal
3. Largest prior study period (2 years)
4. Deterministic path = $0 cost, no LLM quality variance
5. Adapter already registered in `poe_compat.py`

---

## Implementation Prerequisites

Before starting:

1. **Confirm access to MR evidence in SQLite** (live DB or backup)
2. **Confirm old POE is importable** from within POE-A venv:
   ```bash
   .venv/bin/python -c "from src.engine.variable_identity import stable_variable_id; print('OK')"
   ```
3. **Confirm old POE's macro_regime_v1 module is importable:**
   ```bash
   .venv/bin/python -c "from src.domains.macro_regime_v1.domain import get_variables; print(list(get_variables().keys()))"
   ```
4. **Confirm FIREWORKS_API_KEY is NOT required for deterministic path** (it isn't — check router skips scorer for api_derived)

---

## Summary

MR requires writing two new scripts and one config file, plus a small localized
change to `poea_dynamic.py`. No new architecture. No LLM calls. No redesign.

The epistemic justification for MR is different from ART:
- ART: new concepts were DISCOVERED from prose evidence that was previously unanalyzed
- MR: the concepts are already known; the value is in the CAUSAL STRUCTURE learned from 4,119 observations — which edge existence probabilities converged, which hypothesis (T_monetary vs T_credit vs T_ai_boom) dominated, whether paradigm shifts are visible

This is a valid and honest dynamic view that the frontend can display distinctly from
the apriori seed candidates.
