# MR Dynamic Ontology Feasibility Audit

**Date:** 2026-05-31  
**Method:** Direct inspection of source code, SQLite schema, and 4,119 live evidence records  
**No code was modified.**

---

## Executive Finding

MR cannot support a genuinely independent dynamic ontology using existing
infrastructure or existing evidence. Any POE-A induction run on MR evidence —
whether from SQLite or re-fetched from FRED — would reproduce the existing 8
apriori variables with different names at material cost. This is not a
limitation that adapter work can fix. It is structural.

---

## 1. Exact MR Ingestion Path — Complete Trace

### Stage 0: FRED API (external)

Eight series are fetched concurrently by `FREDClient.fetch_all_series()`:

```
T10Y2Y       → daily spread values    (e.g., -0.43 percentage points)
CPIAUCSL     → monthly CPI index      (e.g., 316.2, index 1982-84=100)
WALCL        → weekly balance sheet   (e.g., $7,200 billion)
BAMLH0A0HYM2 → daily HY OAS spread   (e.g., 3.02%)
VIXCLS       → daily VIX level        (e.g., 12.5)
DEXUSEU      → daily USD/EUR rate     (e.g., 1.084)
UNRATE       → monthly unemployment   (e.g., 3.9%)
NASDAQCOM    → daily index level      (e.g., 16,742)
```

**Storage status:** These values exist only in FRED's servers. They are received
in HTTP responses and immediately passed to `compute_snapshot()`. No file,
database, or cache receives them. They are ephemeral.

---

### Stage 1: `MacroRegimeSnapshot` — In-memory only, never persisted

`compute_snapshot()` in `pipeline.py` produces a `MacroRegimeSnapshot` dataclass:

```
t10y2y_weekly_median     → weekly median of daily T10Y2Y values
cpi_yoy_pct              → 12-month YoY % change from CPIAUCSL
walcl_13w_change_pct     → 13-week % change in Fed balance sheet
hy_spread_zscore         → 52-week rolling z-score of BAMLH0A0HYM2
vix_signal               → (vix - 90d_median) / max(IQR, 1.0)
dexuseu_zscore           → 52-week rolling z-score of DEXUSEU
unrate_signal            → -(unrate - 12m_mean) / 0.30
nasdaq_return_zscore     → z-score of 13-week NASDAQ return
```

These are the **last point at which human-interpretable continuous values exist.**

**Storage status:** These fields are used internally to compute probabilities.
`build_evidence_record()` reads them and discards the snapshot object.
They are never written to disk, SQLite, log files, or any cache.

---

### Stage 2: Where Each Variable Is Created

Each FRED series is transformed into a single ontology variable through a
fixed-form feature engineering step followed by a sigmoid transform:

| Variable | FRED Source | Transformation | Stored as |
|---|---|---|---|
| `YieldCurveInverted` | `T10Y2Y` | `signal = -median(T10Y2Y_week) / 0.30` | `P(True) = sigmoid(signal)` |
| `InflationShock` | `CPIAUCSL` | `signal = (CPI_yoy_pct - 3.5) / 0.75` | `P(True) = sigmoid(signal)` |
| `LiquidityStress` | `WALCL` | `signal = -(WALCL_13w_chg_pct) * 5.0` | `P(True) = sigmoid(signal)` |
| `CreditSpreadStress` | `BAMLH0A0HYM2` | `signal = zscore(HY_spread, 52w)` | `P(True) = sigmoid(signal)` |
| `VolatilityShock` | `VIXCLS` | `signal = (VIX - 90d_median) / IQR` | `P(True) = sigmoid(signal)` |
| `DollarStrength` | `DEXUSEU` | `signal = zscore(DEXUSEU, 52w)` | `P(True) = sigmoid(signal)` |
| `EquityRiskOn` | `UNRATE` | `signal = -(UNRATE - 12m_mean) / 0.30` | `P(True) = sigmoid(signal)` |
| `AIRiskOn` | `NASDAQCOM` | `signal = zscore(13w_return, historical)` | `P(True) = sigmoid(signal)` |

Every variable has a one-to-one bijection with a single FRED series. The
ontology vocabulary and the evidence vocabulary are the **same vocabulary**,
constructed simultaneously by the same engineer.

---

### Stage 3: `EvidenceRecord` in SQLite — What is actually stored

`evidence_records` table in `macro_regime.db`:

```
evidence_id    TEXT    -- UUID (not the FRED timestamp)
domain_module  TEXT    -- "macro-regime-v1"
timestamp      TEXT    -- week-ending date as ISO 8601
source_type    TEXT    -- "API"
source_ref     TEXT    -- "FRED:T10Y2Y+CPIAUCSL+...@week-ending-2026-04-03"
confidence     REAL    -- mean of per-variable data confidence
assignments    TEXT    -- JSON, 8 entries
```

Each assignment:
```json
{
  "variable_id":     "e385c558-0083-5dea-bc0c-874a0eea58f9",
  "observed_value":  false,
  "missingness":     "SOFT_OBSERVED",
  "confidence":      1.0,
  "probabilities":   { "true": 0.150, "false": 0.850 }
}
```

**Confirmed absent from every column in every row:**
- T10Y2Y actual spread value
- CPI index level or YoY percentage
- WALCL dollar amount or percentage change
- BAMLH0A0HYM2 raw spread
- VIX level
- DEXUSEU rate
- UNRATE percentage
- NASDAQCOM index level
- Any intermediate signal value from `MacroRegimeSnapshot`
- Any rolling mean, standard deviation, or IQR

The database contains **only sigmoid-transformed soft probabilities.**

---

## 2. Dependency Chain

```
FRED API
  │
  │  (HTTP, in-memory only, 730 weekly calls over 2 years)
  │
  ▼
Raw FRED time series
  T10Y2Y:       [-0.43, -0.38, -0.21, ...]  (daily values)
  CPIAUCSL:     [316.2, 315.8, 314.1, ...]  (monthly index)
  WALCL:        [7200, 7180, 7220, ...]      (weekly billions)
  BAMLH0A0HYM2: [3.02, 3.15, 2.88, ...]    (daily spread)
  VIXCLS:       [12.5, 14.2, 11.8, ...]     (daily)
  DEXUSEU:      [1.084, 1.079, 1.091, ...]  (daily)
  UNRATE:       [3.9, 3.8, 4.0, ...]        (monthly)
  NASDAQCOM:    [16742, 16800, 16600, ...]  (daily)
  │
  │  compute_snapshot() → MacroRegimeSnapshot
  │  [IN MEMORY ONLY — NEVER PERSISTED]
  │
  ▼
Intermediate engineered features (MacroRegimeSnapshot)
  t10y2y_weekly_median:   -0.430
  cpi_yoy_pct:             3.244
  walcl_13w_change_pct:   -0.919
  hy_spread_zscore:        0.152  ← z-score, original value not recoverable
  vix_signal:             -0.842  ← z-score, original value not recoverable
  dexuseu_zscore:          0.198  ← z-score, original value not recoverable
  unrate_signal:          -0.033  ← delta signal, original value not recoverable
  nasdaq_return_zscore:    0.325  ← z-score, original value not recoverable
  │
  │  _soft_bool(signal) = sigmoid(signal) for each variable
  │
  ▼
Ontology variable assignments (EvidenceRecord)
  YieldCurveInverted:  P(True)=0.807  (observable=False)
  InflationShock:      P(True)=0.416  (observable=False)
  LiquidityStress:     P(True)=0.990  (observable=True)
  CreditSpreadStress:  P(True)=0.194  (observable=False)
  VolatilityShock:     P(True)=0.257  (observable=False)
  DollarStrength:      P(True)=0.554  (observable=True)
  EquityRiskOn:        P(True)=0.391  (observable=False)
  AIRiskOn:            P(True)=0.610  (observable=True)
  │
  │  engine.ingest(record); engine.learn([record], domain_id)
  │
  ▼
POE learning (parameters, CPT counts, BIC edge existence updates)
  variable_name → alpha, counts_json, parent_ids_json
  [stored in parameters table]
  │
  ▼
Population state
  4,119 evidence records ingested
  730 unique weekly signal points (some weeks have duplicate records)
  450 active candidates (5 seed + ~445 variants)
  6 paradigm shifts
  Current dominant: "T_ai_boom: AI productivity narrative dominant"
```

---

## 3. Does Raw Evidence Exist Before Ontology Assignment?

**No. Not anywhere that is accessible without calling FRED.**

The `MacroRegimeSnapshot` is the only moment where pre-ontology signals exist.
It is a Python dataclass instantiated and discarded within a single async
function call. It is not logged, not cached, not serialized.

**Partial reconstruction from stored probabilities is possible for 3 of 8 variables:**

The sigmoid is invertible via logit: `signal = ln(p / (1-p))`.
For variables whose signal is linearly derived (not z-score-based), the
original feature value can be recovered exactly:

```
YieldCurveInverted:  t10y2y_median = -logit(p) × 0.30
InflationShock:      cpi_yoy_pct   = logit(p) × 0.75 + 3.5
LiquidityStress:     walcl_chg_pct = -logit(p) / 5.0
```

For z-score variables (5 of 8), inversion yields the z-score only:
```
CreditSpreadStress:  z = logit(p)  ← z = (HY_spread - μ) / σ
                                        μ, σ from 52w rolling window — NOT STORED
VolatilityShock:     z = logit(p)  ← z = (VIX - median) / IQR
                                        median, IQR from 90d window — NOT STORED
DollarStrength:      z = logit(p)  ← z = (DEXUSEU - μ) / σ — NOT STORED
EquityRiskOn:        z = logit(p)  ← z = -(UNRATE - 12m_mean) / 0.30 — NOT STORED
AIRiskOn:            z = logit(p)  ← z = (13w_return - μ) / σ — NOT STORED
```

The rolling window statistics that would permit raw value recovery are
computed from FRED history during `compute_snapshot()` and discarded along
with the snapshot.

**The only path to full raw evidence is re-fetching FRED.** FRED's API
provides full history and is still accessible for all 8 series.

---

## A. Can MR Support a Genuinely Independent Dynamic Ontology?

**No — not with existing infrastructure or existing evidence types.**

The reason is definitional. The MR ontology and the MR evidence were designed
together: the 8 FRED series were selected precisely because each one is an
unambiguous proxy for exactly one ontology variable. There is a one-to-one
named correspondence:

```
T10Y2Y       →  YieldCurveInverted   (by design)
CPIAUCSL     →  InflationShock       (by design)
WALCL        →  LiquidityStress      (by design)
BAMLH0A0HYM2 →  CreditSpreadStress   (by design)
VIXCLS       →  VolatilityShock      (by design)
DEXUSEU      →  DollarStrength       (by design)
UNRATE       →  EquityRiskOn         (by design)
NASDAQCOM    →  AIRiskOn             (by design)
```

If raw FRED data were re-fetched and presented to the POE-A LLM inducer, the
LLM would read descriptions like:

```
Week ending 2024-05-26:
10Y-2Y Treasury spread: -0.43% (negative = inverted curve)
CPI 12-month YoY: +3.24%
Fed balance sheet 13-week change: -0.92%
HY OAS spread: 3.02%
VIX: 12.5
USD/EUR: 1.084
Unemployment: 3.9%
NASDAQ 13-week return: +8.2%
```

The LLM would induce concepts named something like:
- "YieldCurveInversion" (= YieldCurveInverted)
- "InflationaryPressure" (= InflationShock)
- "FedBalanceSheetContraction" (= LiquidityStress)
- "CreditMarketStress" (= CreditSpreadStress)
- "MarketFear" (= VolatilityShock)
- "DollarStrength" (= DollarStrength, same name)
- "LaborMarketTightness" (= EquityRiskOn)
- "TechMomentum" (= AIRiskOn)

**This is not concept discovery. It is reverse-engineering of known
engineering at $10+ cost.**

Contrast with ART: art market news articles contained references to trophy
buyers, auction house dynamics, regional scenes, and third-party guarantees
that the initial apriori ontology had no term for. The LLM found structure
that was genuinely absent from the ontology. For MR, the structure is
identical to what was put in.

---

## B. What Exact Evidence Would POE-A See?

**Path 1: From SQLite (no re-fetch)**

POE-A would receive 4,119 `EvidenceUnit` objects, each with:
```
text: "Macro Regime Evidence — week ending 2026-04-03"
metadata.evidence_type: "api_derived"
metadata.old_poe_evidence_record: {
    8 SOFT_OBSERVED soft-boolean assignments,
    P(True) values, no raw numeric values
}
```

The `text` field contains no substantive content. There is nothing for a
concept inducer to read. Concept induction would fail or produce hallucinated
concepts with no evidentiary support.

The deterministic path would pass these records to `OldPOEDomainMapperAdapter`,
which translates the 8 assignments back to the 8 known variables. Output:
the existing ontology, re-labeled as "dynamic".

**Path 2: From FRED re-fetch (new API calls)**

POE-A would receive 730 `EvidenceUnit` objects (one per unique week), each
with constructed prose describing 8 known FRED series values. The LLM would
induce the same 8 concepts with different names.

This path requires ~730 FRED API calls (FRED has no batch endpoint), plus
LLM induction calls (~73 batches × induction cost), plus scoring calls
(730 records × N concepts). The resulting ontology would not be meaningfully
different from the apriori one.

---

## C. What Files Must Be Changed?

The question is which files for which path.

### For the deterministic path (reproduces existing ontology, $0 LLM cost)

**New files required:**

| File | Purpose |
|---|---|
| `scripts/extract_mr_evidence.py` | Read SQLite `evidence_records` → `EvidenceUnit` JSON with `evidence_type=api_derived` and embedded `old_poe_evidence_record` |
| `scripts/init_mr_concepts.py` | Bootstrap `canonical_concepts.json` from `MacroRegimeV1.get_variables()` — concept IDs must match variable UUIDs exactly |
| `configs/mr_induction_config.yaml` | Domain-specific config: `backend.domain_id=macro-regime-v1` |

**Modified files:**

| File | Change |
|---|---|
| `probabilistic_ontology_engine/src/engine/api/poea_dynamic.py` | Generalize artifact lookup: `_art_artifact(name)` → `_domain_artifact(domain_key, name)` to support `artifacts/mr/` subdirectory |

**No changes to:** `poe_compat.py` (already has MR adapter), `router.py`
(already handles `api_derived`), `poe_backend.py` (domain-agnostic).

### For a genuinely independent path (not currently achievable)

The blockers are documented in Section E. New infrastructure required:
a prose news source for macroeconomic context (e.g., Fed statements, economic
commentary, Bloomberg/Reuters macro news), a loader for that source, and a
separate evidence collection effort. This does not exist in the codebase.

---

## D. Estimated Implementation Effort

### Deterministic path (reproduces existing ontology)

| Task | Effort |
|---|---|
| `extract_mr_evidence.py` | 2-3 hours |
| `init_mr_concepts.py` | 1 hour |
| `configs/mr_induction_config.yaml` | 15 minutes |
| `poea_dynamic.py` multi-domain update | 1 hour |
| Validation and debugging | 1-2 hours |
| **Total** | **5-7 hours** |

LLM cost: $0.00. No concept induction, no semantic scoring.

### Genuinely independent path (new prose evidence source)

| Task | Effort |
|---|---|
| Identify and evaluate prose news source for macro context | 1-2 days |
| Implement news/prose ingest adapter | 1-3 days |
| Backfill ~2 years of macro news evidence | unknown (depends on source) |
| Run POE-A induction pipeline on prose evidence | 1-2 hours compute |
| Validate concept quality vs. apriori | 1-2 days |
| **Total** | **1-3 weeks** |

LLM cost: ~$5-20 depending on evidence volume and scoring approach.

---

## E. Would the Resulting Dynamic Ontology Be Independent?

**Deterministic path: No.**

The deterministic path explicitly reuses the 8 apriori variables as POE-A
concepts. The concept IDs in `canonical_concepts.json` would be set to the
same UUIDs as `MacroRegimeV1` domain variables. The `OldPOEDomainMapperAdapter`
maps old POE assignments directly onto these concepts. The resulting
`poea_graph.json` would show the same 8 nodes with names identical to the
apriori ontology.

The "dynamic" view would differ from the current apriori view only in:
- `evidence_count`: 4,119 (not 0)
- `current_generation`: 4,119 (not 0)
- `structure_entropy`: computed from actual posterior learning
- `competing_candidates`: variants evolved during POE learning

It would NOT differ in:
- Concept names (identical to apriori variables)
- Concept definitions (taken from domain module docstring)
- The fundamental question being answered (same 8 variables)

This is more accurately described as "surfacing the POE learning state in
the dynamic view" than "dynamic ontology induction."

**FRED re-fetch path: No, and expensive.**

Even if raw FRED data were re-fetched and presented to the LLM inducer, the
resulting concepts would be semantically equivalent to the existing 8 variables.
The 8 series are the complete macro regime vocabulary — there is nothing else
to find in them. The cost would be ~$10-20, the runtime ~2-4 hours, and the
output would be a renamed copy of the apriori ontology.

**Prose evidence path: Potentially yes, but requires new infrastructure.**

If a substantive prose corpus of macro commentary were ingested — Fed meeting
minutes, economic analyst reports, Treasury commentary — the LLM inducer might
find structural patterns not currently represented:

- Fiscal policy trajectory vs. monetary policy (currently merged into LiquidityStress)
- International spillovers / contagion effects (not in current 8 variables)
- Housing market as leading indicator (absent)
- Corporate earnings trend separate from equity momentum
- Consumer confidence vs. actual consumption

These would be genuinely new variables. But the evidence source does not
exist in the codebase and building it is a separate multi-week project.

---

## Blockers

**Blocker 1 (fundamental): Evidence vocabulary = ontology vocabulary**

The MR evidence was designed to have exactly 8 meaningful features, one per
ontology variable. There is no surplus signal in the data. Induction cannot
discover what was not put there.

**Blocker 2 (data): Raw FRED values not stored**

The only locally available evidence is post-sigmoid boolean assignments. Raw
numeric values are ephemeral and live only in FRED's API. Accessing them
requires new API calls, a FRED API key, and a re-fetch pipeline.

**Blocker 3 (cost/quality): Re-fetching for LLM induction is wasteful**

Even if FRED were re-fetched, presenting structured numeric tables to a
concept inducer designed for prose text is not the intended use case. The
inducer prompt (`SYSTEM_PROMPT` in `concepts/prompts.py`) is tuned for finding
causal mechanisms in narrative text. Feeding it tables of numbers and series
codes produces lower-quality induction at higher cost.

**Blocker 4 (infrastructure): No prose evidence source for MR**

The codebase contains no client, loader, or ingestion pipeline for
macroeconomic prose evidence. The closest adjacent capability is the GDELT
client in Geopolitics, which fetches news summaries. A macro news source
(Fed statements, economic commentary) does not exist.

---

## Summary Table

| Question | Answer |
|---|---|
| A. Genuinely independent dynamic ontology possible? | **No** — not with existing evidence or infrastructure |
| B. What evidence would POE-A see? | 8 sigmoid-transformed booleans per week; no raw values; no prose |
| C. Files to change? | 3 new files + 1 modified file (deterministic path only) |
| D. Implementation effort? | 5-7 hours (deterministic); 1-3 weeks (genuinely independent) |
| E. Would dynamic ontology be independent of apriori? | **No** — deterministic path reproduces apriori; FRED re-fetch reproduces it with different names |

---

## Recommendation

MR is the right **next domain to expose in dynamic view**, but with honest
framing: the dynamic view would surface what POE actually learned from 4,119
weeks of evidence (structure entropy, dominant hypothesis, edge existence
convergence, 6 paradigm shifts). This is real and valuable. It is not the
same as genuinely inducing a new ontology.

If genuine independent induction is the goal for MR, the prerequisite is a
prose evidence source for macroeconomic conditions. That is a separate project.
The most viable candidates are:

1. **Fed FOMC minutes** (public, quarterly, substantial narrative text)
2. **Treasury/CEA economic reports** (public, quarterly)
3. **GDELT macro news** (already has a client for Geopolitics — adaptable)

Of these, FOMC minutes are the highest quality source and are freely
downloadable from the Fed's public website. They would give the LLM genuine
causal narrative about monetary regime shifts that the 8 FRED numbers alone
cannot provide.
