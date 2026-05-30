# Concept Quality Report

**Source:** `artifacts/raw_concepts.json`
**Model:** `accounts/fireworks/models/deepseek-v4-pro`
**Evidence corpus:** 70 records, 7 batches of 10
**Date:** 2026-05-30

---

## Summary

| Metric | Value |
|--------|-------|
| Total concepts (raw, with duplicates) | 21 |
| Unique concept names | 19 |
| Names appearing more than once | 2 (`FlightToQualityConcentration`, `InstitutionalValidationPremium`) |
| Batches with errors | 0 of 7 |
| Mean confidence | 0.788 |
| Median confidence | 0.800 |
| Min confidence | 0.60 |
| Max confidence | 0.90 |

### Confidence Distribution

```
0.60–0.64 | █                    (1)
0.65–0.69 |                      (0)
0.70–0.74 | █████                (5)
0.75–0.79 | ███                  (3)
0.80–0.84 | ███                  (3)
0.85–0.89 | ██████               (6)
0.90–0.94 | ███                  (3)
```

Confidence is bimodal: 5 concepts at 0.70 and 6 at 0.85, with little spread below 0.70. No concept was assigned above 0.90. This clustering suggests the model uses a coarse ordinal scale (0.60/0.70/0.75/0.80/0.85/0.90) rather than a continuous calibration. The distribution does not discriminate well between weak and strong concepts.

### Concepts Per Batch

| Batch | Records | Concepts |
|-------|---------|----------|
| 0 | 10 | 5 |
| 1 | 10 | 4 |
| 2 | 10 | 2 |
| 3 | 10 | 3 |
| 4 | 10 | 3 |
| 5 | 10 | 2 |
| 6 | 10 | 2 |

Average 3.0 concepts per batch. Output volume was lower than the 7–12 per batch estimated in the readiness review. The model exercised restraint — this is better than the reverse.

---

## Evidence Coverage

| Metric | Value |
|--------|-------|
| Total evidence records | 70 |
| Records cited by at least one concept | 50 |
| Records never cited | 20 |
| Coverage percentage | 71.4% |

### Uncited Records

20 evidence records were cited by no concept. 8 are sparse (title-only); 12 are rich (have body text):

| evidence_id | Type | Title |
|-------------|------|-------|
| dd355ccee678f0b5 | rich | The Art Basel and UBS Art Market Report 2026 |
| 2ccdad8b8306e11c | rich | Foreword by Thierry Ehrmann |
| 3d5a505dccadd4f8 | rich | Confidence may be returning – but for how long? |
| 429a0115d8a2b5e3 | rich | More women in this year's HAT 100 |
| 4549f654fcce3636 | rich | Hiscox Artist Top 100 Rankings |
| 5ef674cc7f1bb886 | rich | Asian demand takes a hit |
| 7aae7858bfee7755 | rich | The flipping era has ended |
| 7c610c5f4463baac | rich | Lower end of market thriving |
| 7a43425e43220e0c | rich | Last Call to Join SFMOMA's Museumwide Art Bash Party |
| 9b8731a06c066716 | rich | Top 25 prices paid at auction for artworks made after 2000 (2019–2024) |
| 127489693e8d9ca4 | rich | Top 25 prices paid at auction for artworks made after 2000 (2024) |
| d88799c640f6c6cc | rich | Non-Western art market presence |
| 35a0294d8ffbf218 | rich | Global Debut of RM x SFMOMA Exhibition |
| 034c8bed965532a8 | sparse | Gala Season! Shaggy and Jewel Hit the Whitney... |
| 050415c995aeaede | sparse | Tracey Emin, Katharina Grosse, and More Rally to Raise $2.7 Million |
| 05ec6cd8def1f72a | sparse | Robert Mnuchin's Storied Art Gallery Townhouse Lists for $35 Million |
| 063e695beef6a9a5 | sparse | Is A Random Unknown Artist More Valuable Than Picasso? AI Thinks So. |
| 6461c5b9005711bc | sparse | The New York Fairs Are Done. What Remains? |
| 7d86bea9dcbad88d | sparse | U.K. Arts Center Lands Seismic $122.4M Gift |
| 8b996e182656aa20 | sparse | Art Basel Qatar Names Wassan Al-Khudhairi Artistic Director |

**Notable gap:** "The Art Basel and UBS Art Market Report 2026" (`dd355ccee678f0b5`) — the primary benchmark document — was never cited. Its `notes` field contains only one meta-sentence ("Evidence extracted from uploaded Art Basel..."), not actual report content. Its text was too thin to ground any specific concept. This is a data quality issue in the source, not a model failure.

Also notable: "The flipping era has ended" and "Lower end of market thriving" — both directly relevant to `SpeculativeDemandCollapse` and `AccessiblePriceLiquidityEngine` respectively — were uncited. Both are in Batch 2, which produced only 2 concepts despite containing these informative records.

### Top Evidence Records by Concept Support Count

| Rank | evidence_id | Concepts | Title |
|------|-------------|---------|-------|
| 1 | 21594d4217f1abcb | 4 | The Art Market in 2025 |
| 2 | 57e77a22f8832c4d | 2 | Long-term Value Consolidation |
| 2 | e19c65a64f0e3161 | 2 | More women artists at auction |
| 2 | e23b207c6afffe59 | 2 | New York and London increase market share |
| 2 | 62d9b8268a847301 | 2 | Christie's Posts 'Rock Solid' Contemporary Sale |
| 2 | 98ffda436ff34e47 | 2 | Marian Goodman's Gerhard Richters Total $78.8M |
| 2 | 6898a9ac6a3f2bb4 | 2 | Trophy Buyers Drive Decorative Art Sales |
| 2 | 06d57cbc7e2f36fe | 2 | Top movers: Maurizio Cattelan |
| 2 | 9c0275e0716537bf | 2 | Top movers: Lucian Freud |
| 2 | 72dc79b9cdfae8c5 | 2 | Top movers: Agnes Martin |

"The Art Market in 2025" is the hub record — it spans the broadest thematic range and serves as grounding for four separate concepts.

---

## Concept Rankings

Sorted by supporting evidence count (descending), then confidence.

| # | Name | Conf | Evidence Count | Supporting IDs |
|---|------|------|---------------|----------------|
| 1 | PostDigitalMaterialAuthenticityPremium | 0.75 | 8 | 6d099a3199a3d5e2, 94c095369ef873ad, a297d389640f7a96, e43eac72d27663e7, 2aeb34951e43644f, c0f72350a8358e59, 1e197f01c0cac25e, 084b48882a3c67a2 |
| 2 | AuctionCatalystEffect | 0.90 | 6 | 62d9b8268a847301, 98ffda436ff34e47, 06d57cbc7e2f36fe, 6898a9ac6a3f2bb4, 9c0275e0716537bf, 72dc79b9cdfae8c5 |
| 3 | HistoricalControversyAsPrestigeAmplifier | 0.60 | 5 | a297d389640f7a96, e43eac72d27663e7, 2aeb34951e43644f, 1e197f01c0cac25e, 6d099a3199a3d5e2 |
| 4 | SpeculativeDemandCollapse | 0.90 | 4 | 6cd02386601b5f00, fae2d9fdb99a3969, 0f6860dbe224841f, e19c65a64f0e3161 |
| 5 | TrophyBuyerDemand | 0.85 | 4 | bc034aecfc683111, 62d9b8268a847301, 98ffda436ff34e47, 6898a9ac6a3f2bb4 |
| 6 | FlightToQualityConcentration (batch 5) | 0.85 | 4 | c04f9d2830a56c47, e070da0373bc0259, f8fdc50bde7d2121, 52990e25e59d2886 |
| 7 | RegionalArtInfrastructureEmergence | 0.90 | 3 | 716b444c1af03678, 23e560a35f25504d, 21594d4217f1abcb |
| 8 | PrestigeMarketAnchoring | 0.85 | 3 | 57e77a22f8832c4d, 21594d4217f1abcb, 7fa9bb49c0f0ab1e |
| 9 | InstitutionalValidationEffect | 0.80 | 3 | 5c695f3630c697d2, 06183c6949c1fb47, 1c0475ae17ce3088 |
| 10 | AIEnabledCollectorOnboarding | 0.75 | 3 | 737a90f7200802ae, 21594d4217f1abcb, fc361611ff2de97c |
| 11 | FlightToQualityInArtMarket | 0.75 | 3 | 6cbb5d378c6e1226, e23b207c6afffe59, e19c65a64f0e3161 |
| 12 | InstitutionalValidationPremium (batch 3) | 0.70 | 3 | 06d57cbc7e2f36fe, 9c0275e0716537bf, 72dc79b9cdfae8c5 |
| 13 | InstitutionalValidationPremium (batch 5) | 0.70 | 3 | 053eabe864e718a3, 195ebcd1fa784298, 8ad24cd4cf494597 |
| 14 | InstitutionalExhibitionPremium | 0.85 | 2 | 8ca3c6af96a21249, 6375b130cbd07b44 |
| 15 | FlightToQualityConcentration (batch 2) | 0.85 | 2 | 756a62abbe97f753, 097cf133a518538b |
| 16 | FreshToMarketPremium | 0.85 | 2 | 183b4f4106195067, beadd19d95147fcc |
| 17 | AuctionConcentrationDynamics | 0.80 | 2 | 21594d4217f1abcb, 57e77a22f8832c4d |
| 18 | ThirdPartyGuaranteesInAuctions | 0.80 | 2 | d59792728ba6b685, c25d5db68737d6e4 |
| 19 | MarketDemocratization | 0.70 | 2 | 0697d7917ab4b40b, e23b207c6afffe59 |
| 20 | HybridAssetMarketConvergence | 0.70 | 2 | 9da1c19b759274d9, 2a5b3d90b3668c80 |
| 21 | AccessiblePriceLiquidityEngine | 0.70 | 1 | ca576f8ef22895dc |

---

## Duplicate Analysis

### Exact Name Duplicates (2 pairs)

Two concept names were independently generated in separate batches:

**`FlightToQualityConcentration`** (batch 2 and batch 5)
Both describe the same mechanism: capital concentration in established artists during uncertainty. The batch 2 version ("collectors reallocate capital toward top-ranked established artists") and batch 5 version ("art market capital concentrates in proven blue-chip artists") are semantically identical. Different evidence IDs, no evidence overlap between the two instances.

**`InstitutionalValidationPremium`** (batch 3 and batch 5)
Both describe how institutional endorsement reduces buyer uncertainty and drives demand. The batch 3 version focuses on "price advantage and auction momentum" for endorsed artists; the batch 5 version is nearly identical but adds the reduction of "information asymmetry." Same mechanism, same name, different evidence sets, negligible definitional difference.

The fact that the model independently converged on the same names is a strong signal that these concepts are genuinely stable and detectable in the evidence.

---

### Semantic Duplicate Clusters

**Cluster 1: Flight to Quality / Prestige Anchoring (4 concepts → 1)**

All four describe the same causal mechanism: during uncertainty, demand concentrates on established, blue-chip, high-certainty works at the expense of the middle and emerging market.

| Concept | Batch | Conf | Evidence |
|---------|-------|------|----------|
| PrestigeMarketAnchoring | 0 | 0.85 | 3 |
| FlightToQualityInArtMarket | 1 | 0.75 | 3 |
| FlightToQualityConcentration | 2 | 0.85 | 2 |
| FlightToQualityConcentration | 5 | 0.85 | 4 |

Proposed canonical: **`FlightToQualityConcentration`** — already the convergent name, clear causal framing.
Combined unique evidence support after merge: 12 distinct IDs.

**Cluster 2: Institutional Validation (4 concepts → 1)**

All four describe institutional endorsement (museum, gallery, biennial, critic) as a mechanism that drives market demand and prices.

| Concept | Batch | Conf | Evidence |
|---------|-------|------|----------|
| InstitutionalValidationEffect | 1 | 0.80 | 3 |
| InstitutionalExhibitionPremium | 2 | 0.85 | 2 |
| InstitutionalValidationPremium | 3 | 0.70 | 3 |
| InstitutionalValidationPremium | 5 | 0.70 | 3 |

The distinction drawn in batch 2 ("exhibition specifically") is a subset of the broader validation mechanism, not a separate concept. The split is an artefact of the evidence in that batch being SFMOMA-heavy, not a genuine ontological distinction.

Proposed canonical: **`InstitutionalValidationPremium`** — the convergent name; covers exhibitions as one form of validation.
Combined unique evidence support after merge: 11 distinct IDs.

**Cluster 3: Concentration at the Top (2 concepts — partial overlap, may keep separate)**

| Concept | Batch | Conf | Evidence |
|---------|-------|------|----------|
| AuctionConcentrationDynamics | 0 | 0.80 | 2 |
| TrophyBuyerDemand | 3 | 0.85 | 4 |

These overlap but are distinguishable. `AuctionConcentrationDynamics` is a structural market description (a small elite captures disproportionate value). `TrophyBuyerDemand` is a demand-side driver (high-net-worth buyers specifically seeking status-signaling works). One is the outcome; the other is the cause. Keeping both is defensible, but a conservative consolidation would merge them.

If merged: proposed canonical **`TrophyBuyerDemand`** — clearer causal agent.

---

### Consolidation Summary

| Scenario | Starting count | After merge | Reduction |
|----------|---------------|-------------|-----------|
| Exact-name duplicates only | 21 | 19 | −2 |
| + Cluster 1 (flight to quality) | 19 | 16 | −3 |
| + Cluster 2 (institutional validation) | 16 | 13 | −3 |
| + Cluster 3 (optional) | 13 | 12 | −1 |

**Expected post-consolidation count: 13–14 canonical concepts.**

The consolidation will be straightforward: exact-name deduplication catches 2 pairs automatically; the semantic clusters are clearly bounded and require minimal LLM assistance to resolve.

---

## Generic / Low-Value Concepts

Four concepts warrant scrutiny before registry promotion:

### 1. `HybridAssetMarketConvergence` (conf: 0.70, 2 evidence IDs)

**Problem:** Driven by two highly specific 2026 news items: prediction markets tied to art auctions and dinosaur fossils sold in art galleries. The underlying mechanism — alternative assets entering art market infrastructure — is real, but the evidence here describes novelty items, not a durable structural factor. This concept cannot be operationalized as a stable True/False condition across time periods.

**Verdict:** Reject or defer. Too time-specific and weakly grounded.

### 2. `HistoricalControversyAsPrestigeAmplifier` (conf: 0.60, 5 evidence IDs)

**Problem:** Driven almost entirely by the SFMOMA Matisse "Femme au chapeau" exhibition — a single institution leveraging one work's historical scandal. The lowest-confidence concept in the set (0.60). While the mechanism (controversy → institutional attention → prestige) is theoretically valid, the evidence supporting it is too localized to a single exhibition to warrant a place in a general-purpose art market ontology. The definition requires the controversy to be "well-documented" and "public," making operationalization circular.

**Verdict:** Reject. Evidence is event-specific, confidence is lowest, mechanism is tautological at this scale.

### 3. `MarketDemocratization` (conf: 0.70, 2 evidence IDs)

**Problem:** The definition is vague — "structural expansion of auction participation to a larger number of artists" describes a trend, not a mechanism. It does not specify the condition under which this is True vs False. "Democratization" in the definition risks conflating distinct phenomena: more artists at auction (supply-side), more collectors entering (demand-side), and lower average prices (market structure). Difficult to use as a binary variable in a Bayesian network.

**Verdict:** Borderline. Could be retained if the definition is sharpened to specify a measurable condition. Needs rewriting before evidence scoring.

### 4. `AccessiblePriceLiquidityEngine` (conf: 0.70, 1 evidence ID)

**Problem:** Supported by only one evidence record. The single-citation rule in Phase 5 (minimum 2 supporting evidence records for promotion) will correctly filter this out. It is also semantically close to `MarketDemocratization` — both concern low-end market volume.

**Verdict:** Will be correctly suppressed by promotion rules. No action needed beyond normal lifecycle filtering.

---

## Concept Quality Assessment

### Specificity: **Good**

Most concepts have CamelCase names (the model followed the naming convention), clear 2–3 sentence definitions with explicit causal structure, and operationalizable conditions. `SpeculativeDemandCollapse`, `AuctionCatalystEffect`, `ThirdPartyGuaranteesInAuctions`, and `FreshToMarketPremium` are particularly well-specified — a reviewer could determine True/False for a given time period from evidence alone.

Exceptions: `MarketDemocratization` (too vague) and `HistoricalControversyAsPrestigeAmplifier` (tautological).

### Distinctiveness: **Fair**

8 of 21 raw concepts (38%) belong to the two major duplicate clusters. After consolidation, distinctiveness becomes Good: the 13–14 canonical concepts cover clearly separate mechanisms with minimal semantic overlap. The duplicate production is expected behavior given the independent-batch design — each batch had no knowledge of prior batches' output.

### Evidence Grounding: **Fair**

71.4% coverage is respectable for a first run. However, citation quality is uneven:

- `PostDigitalMaterialAuthenticityPremium` cites 8 evidence IDs — the widest coverage — but all come from a single batch (batch 6, SFMOMA-heavy). The citations look comprehensive within that context window but are not cross-validated.
- `AuctionCatalystEffect` cites 6 IDs from a single batch and achieves the highest confidence (0.90) — this is the strongest combination in the output.
- `AccessiblePriceLiquidityEngine` cites only 1 record. The Phase 5 minimum-evidence filter (2 records) will correctly suppress it.
- Several rich records containing relevant causal claims were not cited ("The flipping era has ended," "Lower end of market thriving"), suggesting the model did not extract everything available even in non-sparse batches.

### Confidence Calibration: **Poor**

The 0.60–0.90 range with no values above 0.90 and clustering at discrete levels (0.70, 0.85, 0.90) indicates an ordinal scale, not calibrated probability. Implications:

- The `min_confidence: 0.40` filter provides no discrimination — all concepts exceed it.
- The `promotion_confidence: 0.55` threshold will promote all 21 concepts. The threshold needs to be raised to approximately 0.75–0.80 to be meaningful at this scale.
- `HistoricalControversyAsPrestigeAmplifier` scores 0.60 (lowest) despite 5 evidence citations; `AccessiblePriceLiquidityEngine` scores 0.70 despite only 1 citation. The inverse relationship undermines confidence as a quality signal.

### Ontology Usefulness: **Good**

The majority of concepts have clear causal structure and plausible True/False interpretations as Bayesian network nodes:

- **Strong candidates for POE nodes:** SpeculativeDemandCollapse, AuctionCatalystEffect, FlightToQualityConcentration, TrophyBuyerDemand, PrestigeMarketAnchoring, InstitutionalValidationPremium, RegionalArtInfrastructureEmergence, ThirdPartyGuaranteesInAuctions, FreshToMarketPremium, PostDigitalMaterialAuthenticityPremium (with caveat).
- **Needs sharpening:** MarketDemocratization, AIEnabledCollectorOnboarding, AuctionConcentrationDynamics.
- **Reject:** HistoricalControversyAsPrestigeAmplifier, HybridAssetMarketConvergence.

---

## Registry Readiness

**1. Can a simple registry be implemented immediately?**

Yes. 21 concepts is well within the manageable range. The registry schema defined in the implementation plan (four tables: concepts, induction_runs, concept_evidence_links, concept_events) is sufficient. No schema additions are required by this output.

**2. Does consolidation appear necessary?**

Yes, but not urgently. The 4+4 duplicates are obvious and well-bounded. Without consolidation, the registry imports 21 entries representing 13–14 actual concepts. The evidence scoring layer in Phase 6 would then score 21 concepts against 70 evidence records — expensive and redundant when 8 of those 21 are duplicates.

Consolidation before evidence scoring is the right sequencing. Scoring 13–14 canonical concepts is cheaper and produces cleaner data than scoring 21 noisy ones.

**3. Should consolidation occur before evidence scoring?**

Yes. The evidence scoring step (Phase 6) maps each (evidence record, concept) pair to a True/False assignment. Running that step against duplicate clusters would produce:

- Two near-identical scoring calls per evidence record for each duplicate pair
- Redundant `concept_evidence_links` entries
- Contradictory assignments if the two versions of a concept are scored slightly differently

Consolidation first, scoring second.

**4. Is Phase 3 safe to begin?**

Yes. The output is coherent, the schema requirements are clear, and the concept count is manageable. No changes to the induction implementation are required before building the registry. The one calibration change that should be made: raise `promotion_confidence` from 0.55 to 0.75 before Phase 5 executes, given the observed confidence distribution.

---

## Recommendation

**B. Build Registry and Consolidation together**

### Justification

The induction output is solid. The concept quality is sufficient for Phase 3 to proceed. However, the evidence creates a clear architectural argument for building Phase 3 and Phase 4 as a unit:

**Reason 1: Exact duplicates are already present on first run.**
`FlightToQualityConcentration` and `InstitutionalValidationPremium` each appear twice. If Phase 3 is built alone without consolidation hooks, those duplicates will be imported and persist in the registry as separate candidates until Phase 4 is retroactively applied. Building consolidation into the import step avoids contaminating the registry from the start.

**Reason 2: The consolidation problem is simple and well-bounded.**
Two clusters with 4 concepts each, two exact-name duplicates. The consolidation logic needed here is:
1. Detect exact name matches (trivial)
2. Detect the two semantic clusters (LLM comparison of 19 pairs — small)

This is not a hard problem. Building it concurrently with the registry adds a week of work at most and prevents future cleanup debt.

**Reason 3: Confidence threshold recalibration is required.**
The `promotion_confidence: 0.55` threshold will incorrectly promote all 21 concepts. Before Phase 5 executes, this must be raised to ~0.75. That change is low-risk but should be documented as a schema/config update alongside the registry implementation.

**Against option A (Registry alone):** Importing 21 noisy concepts into a registry not yet equipped to consolidate them creates technical debt immediately. The evidence scoring step in Phase 6 would then be run against a bloated, un-deduplicated concept set.

**Against option C (More induction work first):** The induction output is good enough. Running a second induction pass before building the registry would add more concepts without resolving the duplicate problem — it would make it worse.

The correct move is to build the registry with consolidation as a first-class operation.
