# Ontology Divergence Audit — Executive Summary

**Date:** 2026-05-30  
**Scope:** art-prestige-regime-v1 (apriori) vs. poea-induced-v1 (dynamic)  
**Status:** COMPLETE

---

## The Question

Is the dynamic (induced) ontology:
- A. Reconstructing the apriori ontology?
- B. Adding concepts that get lost in translation?
- C. Producing genuinely novel structure?
- D. Not actually wired into the pipeline?

## The Answer

**✅ OPTION C: The dynamic ontology produces genuinely novel explanatory structure.**

With important caveats: The dynamic system is currently underdeveloped due to insufficient evidence coverage and learning iterations. But it is fully wired and actively producing a different ontological model.

---

## Key Numbers

| Metric | Apriori | Dynamic | Interpretation |
|--------|:-------:|:-------:|---|
| **Concepts** | 25 variables | 11 concepts | Dynamic is more compact |
| **Novel concepts** | – | 4 of 11 | AuctionCatalystEffect, FreshToMarketPremium, ThirdPartyGuarantees, AIEnabledOnboarding |
| **Evidence coverage** | 100% (70/70) | 43% (30/70) | 40 records orphaned in dynamic system |
| **Assignment density** | 12.8% | 4.9% | Apriori is 2.6× denser |
| **Causal edges learned** | 4 (pre-specified) | 1 (weak, p=0.156) | Dynamic edge unconfirmed |
| **Population entropy** | Low (H3 winning) | Maximum (all tied) | Dynamic needs more iterations |

---

## What Changed?

### Vocabulary

| Type | Count | Examples |
|------|:-----:|----------|
| Preserved (partial correspondence) | 5 | FlightToQualityConcentration ↔ CollectorFlightToSafety + BlueChipConcentration |
| Refined (new scope/framing) | 7 | InstitutionalValidationPremium narrows MuseumAcquisitionMomentum; adds biennials |
| Novel (no apriori equivalent) | 4 | **AuctionCatalystEffect, FreshToMarketPremium, ThirdPartyGuarantees, AIEnabledOnboarding** |
| Missing (apriori but not dynamic) | 8+ | **MarketUncertainty (31 observations), PrestigeFragmentation (30 obs), cultural theory variables** |

### Causal Structure

**Apriori narrative:** Market uncertainty → Collector flight → Blue-chip consolidation → Institutional conservatism

**Dynamic narrative:** (Emerging) Trophy-buyer demand → Fresh-to-market premium (single unconfirmed edge)

**Interpretation:** Different causal levels. Apriori models macro-economic states. Dynamic models market microstructure mechanisms.

### Information Preservation

**End-to-end wiring: ✅ INTACT**

Concepts survive through:
1. ✅ Induction → Registry: 21 proposals consolidated to 11 active
2. ✅ Registry → Scoring: Concept definitions used for semantic scoring
3. ✅ Scoring → Variable export: Names preserved 1:1 as Variable objects
4. ✅ Variable export → POE: Variables registered, learning invoked
5. ✅ POE learning: 11 variables active, 30 records fed, 1 edge learned

**Data loss points:**
1. ⚠️ **Coverage gap:** 40 records all-neutral (57% orphan rate) — excluded from POE learning
2. ⚠️ **Iteration gap:** 1 generation (dynamic) vs. 6 generations (apriori) — insufficient for convergence
3. ⚠️ **Semantic metadata:** Concept definitions/confidence not passed into old POE — by architectural design

---

## Why the Divergence?

### Epistemological Difference

| Apriori | Dynamic |
|---------|---------|
| Evidence is a window onto structural market **states** | Evidence is a description of causal **mechanisms** |
| Background conditions (MarketUncertainty, PrestigeFragmentation) fire even with minimal textual trigger | Mechanism concepts fire only when text explicitly describes the mechanism |
| Assignment density: 12.8% (comprehensive) | Assignment density: 4.9% (specific) |

### Evidence Coverage

**Apriori reads all 70 records:**
- Ranking lists → BlueChipConcentration implied
- Auction summaries → Market uncertainty implied
- Press releases → Museum momentum implied

**Dynamic reads 30 records:**
- Only records with explicit mechanism description
- 40 records (rankings, summaries, announcements) are all-neutral
- These orphans represent ~43% of evidence

### Which Is Correct?

**Neither is uniquely correct.** Both epistemologies are defensible:
- If the goal is structural monitoring (what market state exists?), apriori is better.
- If the goal is mechanism detection (what forces are at work?), dynamic is better.

---

## Critical Gaps

### 1. Coverage Gap: 40 Orphan Records

**Records excluded from dynamic POE learning:**
- 14 Hiscox artist rankings (statistics)
- 6 SFMOMA press releases (institutional announcements)
- 12 auction market summaries (aggregate outcomes)
- 8 general commentary

**Impact:** Old POE trained on 70 records; new POE trained on 30. This 57% orphan rate **starves the dynamic system of structural background signal** needed for narrative emergence.

**Assessment:** Not necessarily wrong (may be noise filtering), but limits structure learning.

### 2. Iteration Gap: 1 Generation vs. 6

**Apriori result:** After 6 generations, H3 and H4 competing (low entropy, near-tied).

**Dynamic result:** After 1 generation, all 10 candidates tied (maximum entropy).

**Assessment:** The dynamic system is immature by design. More iterations would likely show population differentiation.

### 3. Missing Structural Variables

**Apriori has 8+ variables with no dynamic equivalent:**
- MarketUncertainty (31 observations in corpus)
- PrestigeFragmentation (30 observations)
- Cultural/discourse variables (RitualAuraPremium, NeoAcademicResurgence, EmbodimentDiscourseRising, CraftPrestigeRising, ConceptualDominance)

**Assessment:** The dynamic system does not induct structural background conditions. It focuses on episodic mechanisms. This is a choice, not a failure.

---

## Novel Concepts: Evidence of Real Discovery

The 4 novel concepts are not marginal refinements. They represent genuine phenomena:

| Concept | Real-world mechanism | Apriori gap |
|---------|---------------------|-----------|
| **AuctionCatalystEffect** | A single high-profile auction event revalues an artist's market | Apriori has no episodic/event variables; all are monthly-aggregate |
| **FreshToMarketPremium** | Recently rediscovered/absent works command scarcity premium | Apriori's AuthenticityPremium is provenance-based, not temporal |
| **ThirdPartyGuaranteesInAuctions** | Risk-transfer mechanism in white-glove sales | Apriori has no auction microstructure variables |
| **AIEnabledCollectorOnboarding** | AI tools lower market entry barriers for new collectors | Apriori treats AI as art subject/cultural force, not infrastructure tool |

**Conclusion:** These are not artifacts of overclassification. They are real mechanisms observed in the evidence that the apriori vocabulary cannot express.

---

## Posterior Inference: Do They Disagree?

**Question:** If both systems produce posteriors via old POE, do they reach different conclusions?

**Answer:** YES, materially different beliefs would emerge.

**Example:** P(MarketUncertainty=True | evidence)
- Apriori: Has explicit MarketUncertainty variable with 31 direct observations. Can compute directly.
- Dynamic: Has no MarketUncertainty variable. Would need to infer through FlightToQualityConcentration → TrophyBuyerDemand chain (uncertain).

**Result:** Different posterior distributions for equivalent real-world phenomena.

---

## Recommendations

### For Understanding

1. **Query both posteriors.** Compare P(structure | evidence) from both systems to understand different perspectives.
2. **Do NOT discard apriori.** They model complementary phenomena (macro vs. micro).
3. **Do NOT expect dynamic to replace apriori.** It needs more development.

### For Development

1. **Increase coverage:** Evaluate the 40 orphan records. Can induced concepts extend to them? Or do new background-condition concepts need induction?
2. **Run more iterations:** Execute 6 generations on the 30-record subset to allow convergence.
3. **Validate novel concepts:** Test AuctionCatalystEffect, FreshToMarketPremium, ThirdPartyGuarantees, AIEnabledOnboarding on fresh evidence.

### For Downstream Use

1. **Ensemble approach:** Combine posteriors from both systems for comprehensive causal inference.
2. **Anomaly detection:** Use dynamic concepts for early warning of microstructure shifts.
3. **Narrative clarity:** Communicate which ontology answers which question (macro structure vs. mechanism).

---

## Bottom Line

The dynamic ontology is:
- ✅ **Fully wired** into the pipeline
- ✅ **Producing novel concepts** (4 of 11 are genuinely new)
- ✅ **Generating different causal structure** (TrophyBuyerDemand → FreshToMarketPremium vs. MarketUncertainty → CollectorFlightToSafety)
- ⚠️ **Underdeveloped** (40 orphan records, 1 generation insufficient)
- ⚠️ **Not yet converged** (all candidate hypotheses tied)

**It is not a failed reconstruction of the apriori ontology. It is a different ontology in early-stage development.**

---

## Files in This Audit

- **FINAL_ONTOLOGY_DIVERGENCE_AUDIT.md** — Full 7-section technical audit (this report's detailed version)
- **ONTOLOGY_DIFFERENCE_AUDIT.md** — Vocabulary and conceptual comparison
- **CONCEPT_CORRESPONDENCE_AUDIT.md** — Semantic mapping details
- **ASSIGNMENT_DIFFERENCE_AUDIT.md** — Per-record assignment comparison
- **STRUCTURAL_DIFFERENCE_AUDIT.md** — Graph structure and edges
- **DISAGREEMENT_ANALYSIS.md** — Types of interpretive divergence
- **COVERAGE_ANALYSIS.md** — Density and orphan analysis
- **POE_A_BOUNDARY_AUDIT.md** — Architecture verification
