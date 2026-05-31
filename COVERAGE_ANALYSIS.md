# Coverage Analysis

_Domain: Art Market_
_Date: 2026-05-30_

---

## Old Ontology Coverage

### Assignment Density

| Metric | Value |
|--------|------:|
| Total possible pairs | 1,750 (70 records × 25 variables) |
| Observed true | 218 (12.5%) |
| Observed false | 6 (0.3%) |
| Missing/neutral | 1,526 (87.2%) |
| Overall assignment density | 12.8% |
| Mean assignments per record | 3.2 (218+6 / 70) |
| Records with ≥1 observation | 70 / 70 (100%) |
| Records with ≥5 observations | 14 / 70 (20%) |
| Records with ≥10 observations | 4 / 70 (6%) |

### Unused Variables (Never Observed)

5 of 25 variables were never assigned in this 70-record corpus:

| Variable | Group | Likely reason |
|---------|-------|--------------|
| `InstitutionalRiskAversion` | Institutional | Outcome variable; requires sustained pattern not visible in articles |
| `FigurativeAuctionMomentum` | Market | No figurative-specific auction data in article corpus |
| `EmergingMarketLiquidity` | Market | Emerging lot ratios require auction aggregate data not present in articles |
| `BlueChipInstitutionalCapture` | Institutional | Requires counting museum show ratios; articles lack this granularity |
| `AttentionFragmentation` | Cultural | Difficult to observe directly from single articles |

**Observation:** 4 of 5 unused variables require quantitative aggregate inputs
(ratios, counts) that the art-prestige-regime-v1 `evidence_mapper.py` was designed
to compute from Artsy API and auction data — but this corpus uses text-based manual
ingest, not API ingest. The unused variables represent a mismatch between the variable
design (API-derived) and the evidence format (prose articles).

### Overloaded Variables

Variables with very high observation rates across the corpus:

| Variable | True count | Rate | Notes |
|---------|:----------:|:----:|-------|
| `BlueChipConcentration` | 32 | 46% | Present in almost half of all records |
| `MarketUncertainty` | 31 | 44% | Present in nearly half of records |
| `PrestigeFragmentation` | 30 | 43% | Present in nearly half of records |
| `CollectorFlightToSafety` | 28 | 40% | Present in 40% of records |
| `AuthenticityPremium` | 25 | 36% | Present in over a third |
| `RegionalSceneMomentum` | 21 | 30% | Present in 30% |

These 6 variables are observed in 30-46% of records. If they were truly binary states,
we would not expect them in nearly every record. High base rates suggest these variables
may be structural conditions of the current art market rather than distinguishing
episodic signals. They carry limited discriminative power for structure learning.

### Orphan Evidence (Records with Few Observations)

Records where the old ontology found few or no meaningful assignments:

- 0 records with zero old observations
- 12 records with only 1-2 old observations (typically short news items: "New on View", Hiscox ranking snippets)
- The minimum observed in any record was 1 assignment (e.g., "New on View: SFMOMA Graciela Iturbide")

The old ontology had no true orphan evidence; every record received some assignment.

---

## Induced Ontology Coverage

### Assignment Density

| Metric | Value |
|--------|------:|
| Total possible pairs | 770 (70 records × 11 concepts) |
| Observed true | 35 (4.5%) |
| Observed false | 3 (0.4%) |
| Neutral/missing | 732 (95.1%) |
| Overall assignment density | 4.9% |
| Mean assignments per non-neutral record | 1.3 (38 / 30) |
| Records with ≥1 observation | 30 / 70 (43%) |
| Records with ≥3 observations | 10 / 70 (14%) |
| Records with ≥4 observations | 3 / 70 (4%) |

### Unused Concepts

All 11 induced concepts were observed at least once. No unused concepts.

However, some concepts have very low observation rates:

| Concept | True | False | Rate |
|---------|:----:|:-----:|:----:|
| `InstitutionalValidationPremium` | 9 | 0 | 12.9% |
| `TrophyBuyerDemand` | 5 | 0 | 7.1% |
| `SpeculativeDemandCollapse` | 5 | 2 | 10.0% |
| `FlightToQualityConcentration` | 4 | 0 | 5.7% |
| `RegionalArtInfrastructureEmergence` | 3 | 0 | 4.3% |
| `AuctionConcentrationDynamics` | 3 | 1 | 5.7% |
| `AuctionCatalystEffect` | 2 | 0 | 2.9% |
| `ThirdPartyGuaranteesInAuctions` | 1 | 0 | 1.4% |
| `AIEnabledCollectorOnboarding` | 1 | 0 | 1.4% |
| `FreshToMarketPremium` | 1 | 0 | 1.4% |
| `PostDigitalMaterialAuthenticityPremium` | 1 | 0 | 1.4% |

**The bottom four concepts** (ThirdPartyGuarantees, AIEnabled, FreshToMarket,
PostDigitalMaterial) each appear in only 1 of 70 records. With only 1 observation,
these concepts carry almost no information for structure learning.

### Orphan Evidence

40 of 70 records (57.1%) produce zero induced assignments. These are records that the
LLM scorer evaluated as neutral against all 11 active concepts.

**Orphan record categories:**
- Hiscox artist ranking snippets (14 records) — artist statistics without market mechanism content
- SFMOMA press releases (6 records) — institutional announcements without market mechanism framing
- Artprice/auction data summaries (12 records) — structural market data without named mechanism triggers
- General market commentary (8 records) — broad market observations that fall below scoring thresholds

The Hiscox and SFMOMA records are particularly interesting: the old ontology assigns
2-3 variables to each of them (`BlueChipConcentration`, `CollectorFlightToSafety`,
`MuseumAcquisitionMomentum`) because these are structural conditions assumed to be
observable in any art market record. The induced ontology makes no such assumption.

---

## Coverage Comparison

| Dimension | Old Ontology | Induced Ontology |
|-----------|-------------|-----------------|
| Assignment density | 12.8% | 4.9% |
| Records with ≥1 assignment | 100% | 43% |
| Unused variables/concepts | 5 (20%) | 0 (0%) |
| High base-rate variables (>30%) | 6 (24%) | 0 (0%) |
| Mean assignments per active record | 3.2 | 1.3 |
| Orphan records (0 assignments) | 0 | 40 (57%) |

### Interpretation of Differences

**1. Density gap (12.8% vs 4.9%)**

The old ontology is 2.6× denser. This reflects two distinct factors:
- More variables (25 vs 11), some of which are designed to be near-always-present conditions
- Human analyst assignment, which can engage with implied and contextual signals
  that the LLM semantic scorer may not detect

**2. Coverage gap (100% vs 43%)**

The old ontology leaves no record unaddressed because it contains structural variables
(`MarketUncertainty`, `BlueChipConcentration`, `PrestigeFragmentation`) that are almost
always present as background conditions. The induced ontology only fires when an evidence
record specifically triggers a named mechanism concept.

**3. Unused variables (20% vs 0%)**

The old ontology has 5 unused variables that were designed for API-derived quantitative
inputs. The induced ontology has zero unused concepts because concepts were induced
from the prose text evidence — they emerge from what the evidence actually contains.

**4. High-base-rate variables (24% vs 0%)**

The old ontology has 6 structural condition variables that fire in 30-46% of records.
The induced ontology has no such near-omnipresent concepts. This reflects a difference
in design philosophy: the old ontology includes background structural conditions;
the induced ontology generates episodic mechanism concepts grounded in specific evidence.

**5. Orphan evidence (0% vs 57%)**

The 40 orphan records represent a genuine coverage gap in the induced ontology. These
records receive no epistemic annotation from the induced system, whereas the old system
has at least some interpretation for every record. Whether this gap reflects a flaw in
the induced vocabulary or a genuine judgment that these records contain no mechanism
signal is an open question.
