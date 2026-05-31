# Structural Difference Audit

_Domain: Art Market_
_Date: 2026-05-30_
_Methodology: Compare old POE and induced POE results using existing POE backend runs_

---

## Data Sources

**Old ontology structure:** `art_prestige_regime.db` — old POE run with art-prestige-regime-v1
domain module, 70 evidence records, 6 generations, 25 variables.

**Induced ontology structure:** `artifacts/poea_graph.json` — induced POE run with
poea-induced-v1 domain module, 30 evidence records (40 all-neutral dropped), 1 generation,
11 variables.

**Important caveat:** These two runs are not directly comparable because:
1. Evidence input sizes differ (70 records vs. 30 records fed to POE)
2. Generations differ (6 vs. 1)
3. Variable count differs (25 vs. 11)
4. The old run used a curated initial graph with 5 hypotheses; the induced run used a co-occurrence seed

---

## Population Comparison

### Old Ontology Population

| Metric | Value |
|--------|------:|
| Active candidates | 10 |
| Evidence records | 70 |
| Generations | 6 |
| Dominant candidate | H3 DefensiveBlueChipConsolidation (variants) |
| Best log_score | −37.94 |
| Worst log_score | −47.40 (H5 NeoAcademicResurgence, pruned) |
| Paradigm shifts | 1 (H1 → H4, then H4 → H3 variants) |
| Pruned candidates | 1 (H5) |

**Candidate log_scores:**

| Candidate | Score | Status |
|-----------|------:|--------|
| H3 DefensiveBlueChipConsolidation | −37.94 | ACTIVE (dominant) |
| variant_add InstitutionalRiskAversion→MuseumAcquisition | −37.94 | ACTIVE |
| variant_add CuratorialMaterialityShift→MuseumAcquisition | −37.94 | ACTIVE |
| H4 PrestigeFragmentation | −38.13 | ACTIVE |
| variant_add InstitutionalRiskAversion→AuthenticityPremium | −38.13 | ACTIVE |
| variant_add AntiDigitalSentiment→AuctionSpeculationElevated | −38.13 | ACTIVE |
| H2 AINormalization | −39.46 | ACTIVE |
| variant_add AntiDigitalSentiment→FigurativeAuctionMomentum | −39.46 | ACTIVE |
| H1 CraftAuraBacklash | −43.24 | ACTIVE |
| variant_add EmbodimentDiscourseRising→CraftPrestigeRising | −43.24 | ACTIVE |
| H5 NeoAcademicResurgence | −47.40 | PRUNED |

**Structure entropy:** The 3-way log_score tie (H3/variants, H4/variants, H2/variants)
indicates the population has NOT converged to a clear winner after 6 generations.
H3 edges out H4 by only 0.19 log-score units — within BIC noise for 70 records.

### Induced Ontology Population

| Metric | Value |
|--------|------:|
| Active candidates | 10 |
| Evidence records (fed to POE) | 30 |
| Generations | 1 |
| Dominant candidate | Seed (co-occurrence based) |
| Best log_score | −21.01 |
| Worst log_score | −21.01 |
| Paradigm shifts | 0 |
| Pruned candidates | 0 |

**All 10 induced candidates share identical log_score (−21.01).** This indicates:
1. The seed + 9 variants are all equally supported (or unsupported) by the 30 evidence records
2. No structural preference has emerged from the data
3. The population has not differentiated after a single learning cycle

---

## Learned Edges Comparison

### Old Ontology — No Directly Learned Edges in This Run Configuration

The old POE run found its best candidates through BIC scoring of the pre-specified
hypotheses (H1-H5) and their variants. The dominant candidate H3 has these pre-seeded
edges:
- `MarketUncertainty → CollectorFlightToSafety` (prior 0.70)
- `CollectorFlightToSafety → BlueChipConcentration` (prior 0.70)
- `BlueChipConcentration → InstitutionalRiskAversion` (prior 0.65)
- `BlueChipInstitutionalCapture → MuseumAcquisitionMomentum` (prior 0.60)

These edges were specified in the seed candidate, not learned from data (the edge
existence probabilities update from evidence, but the edge topology was human-specified).

The **top causal edges by accumulated claim evidence** (from the snapshot):
1. `MarketUncertainty → CollectorFlightToSafety` (4 claims, accumulated 3.44, mean 0.86)
2. `AIImageSaturation → AntiDigitalSentiment` (1 claim, acc 0.88)
3. `AIImageSaturation → RitualAuraPremium` (1 claim, acc 0.88)
4. `CuratorialMaterialityShift → CraftPrestigeRising` (1 claim, acc 0.84)
5. `AIImageSaturation → AuthenticityPremium` (1 claim, acc 0.83)

### Induced Ontology — One Learned Edge

The dominant induced candidate has one active edge:
- **`TrophyBuyerDemand → FreshToMarketPremium`** (existence_probability 0.156)

This edge was seeded by co-occurrence (both concepts appeared in the same evidence
record: "Rediscovered Old Master Painting Eclipses Estimate at Auction") and confirmed
by BIC learning. The existence probability of 0.156 is below the accept threshold
(0.90) and within the "tending toward pruning" range — it has not been confirmed.

**No edge in the induced ontology maps to any edge in the old ontology.** The
`TrophyBuyerDemand → FreshToMarketPremium` relationship has no analog in the old
variable set.

---

## Structural Similarity

| Dimension | Similarity |
|-----------|-----------|
| Dominant hypothesis narrative | Divergent (old: market safety/uncertainty; induced: no clear narrative) |
| Edge topology | No shared edges possible (disjoint variable sets) |
| Number of active edges (dominant candidate) | Old: 4 (pre-specified); Induced: 1 (seeded, unconfirmed) |
| Population entropy | Old: lower (H3 cluster leading); Induced: maximum (all candidates tied) |
| Paradigm shift behavior | Old: 1 shift detected; Induced: 0 shifts (insufficient evidence differentiation) |

---

## Posterior Inference Comparison

From old POE snapshot (causal claim evidence, not pgmpy posteriors):
The old snapshot does not include pgmpy marginal posteriors. The causal prior scoring
suggests H3 (DefensiveBlueChipConsolidation) has the highest evidence support.

**Key implication for causal claims:**
- Old POE best-supported edge: `MarketUncertainty → CollectorFlightToSafety` (4 explicit claims)
- Induced POE best-supported edge: `TrophyBuyerDemand → FreshToMarketPremium` (co-occurrence + BIC)
- These edges describe completely different causal stories about the art market

---

## Structural Differences Summary

### What the old ontology found (6 generations, 70 records):

**Narrative:** Defensive blue-chip consolidation (H3) is marginally preferred.
Market uncertainty drives collector flight to safety, which drives blue-chip concentration.
The CraftAuraBacklash hypothesis (H1) was briefly dominant but lost to H3 by generation 6.
AI-related hypotheses (H2) are significantly weaker. NeoAcademic (H5) was pruned.

**Causal frontier:** The most evidence-supported edge is a macro mechanism:
MarketUncertainty → CollectorFlightToSafety. This is consistent across 4 independent
causal claims from the evidence corpus.

**Population state:** Still contested — H3 and H4 are nearly tied. The population
has NOT resolved to a dominant paradigm. This is epistemically meaningful: the evidence
is genuinely ambiguous between "market uncertainty drives conservatism" (H3) and
"prestige fragmentation drives regional divergence" (H4).

### What the induced ontology found (1 generation, 30 records):

**Narrative:** No clear narrative has emerged. All 10 candidates are equally scored.
The single learned edge (TrophyBuyerDemand → FreshToMarketPremium) is weak
(p=0.156, unconfirmed).

**Causal frontier:** The strongest relationship is between trophy buying and
fresh-to-market scarcity — a market microstructure observation absent from the
old ontology entirely.

**Population state:** Maximum entropy — the induced ontology with 30 records and
11 variables and 1 generation cannot differentiate its population yet. More evidence
cycles would be needed.

### Key Structural Insight

The old ontology found meaningful structure (H3 vs H4 competition) because:
1. Its 25 variables are designed to be sensitive to the evidence
2. 70 records fed fully (0 orphans) provide richer signal
3. 6 learning generations allow population differentiation

The induced ontology did not find meaningful structure yet because:
1. 40/70 records produce zero observations (orphan records)
2. Only 30 records carry signal for 11 variables
3. 1 learning generation is insufficient for population differentiation

**The structural gap is primarily a data coverage gap, not a variable quality gap.**
