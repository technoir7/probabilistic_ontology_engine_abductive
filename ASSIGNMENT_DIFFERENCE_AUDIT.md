# Assignment Difference Audit

_Domain: Art Market_
_Date: 2026-05-30_
_Methodology: Per-record comparison of old vs. induced assignments on the same 70 evidence records_

---

## Data Sources

**Old ontology assignments:** `art-market-domain/data/manual_ingest_split/*.json` (field: `assignments`)
These assignments were made by human analysts reading the same 70 evidence records
and assigning old ontology variables. They include confidence scores and rationales.

**Induced ontology assignments:** `artifacts/scored_evidence.json`
These assignments were made by an LLM semantic scorer evaluating the same 70 records
against the 11 induced concepts. No human review; automated semantic judgment.

**Note on methodology differences:** The old assignments are human-authored with
confidence-weighted rationales; the induced assignments are LLM-scored against
concept definitions. These are different epistemological processes operating on the
same evidence. Differences in assignment may reflect genuine ontological disagreement
OR differences in the scoring method.

---

## Overall Statistics

| Metric | Old Ontology | Induced Ontology |
|--------|-------------|-----------------|
| Total pairs | 70 × 25 = 1,750 | 70 × 11 = 770 |
| Observed true | 218 | 35 |
| Observed false | 6 | 3 |
| Neutral/missing | 1,526 | 732 |
| Assignment density | 12.8% | 4.9% |
| Records with ≥1 observation | 70 / 70 (100%) | 30 / 70 (43%) |
| Records with all-neutral | 0 / 70 (0%) | 40 / 70 (57%) |

---

## Records with Both Ontologies Producing Observations (30 records)

These are the only records where a cross-ontology comparison is possible.

### Records with Highest Total Observations

| Record | Old obs | Induced obs | Overlap quality |
|--------|:-------:|:-----------:|----------------|
| Post-Digital Scarcity and the Neo-Academic Signal | 14 | 1 | Partial |
| The Art Market in 2025 | 7 | 4 | Strong |
| How Did Phillips Pull Off a $115.2M White Glove Sale? | 3 | 3 | Divergent |
| Rediscovered Old Master Painting Eclipses Estimate | 3 | 2 | Convergent |
| Foreword by Wan Jie | 4 | 1 | Partial |
| Long-term Value Consolidation | 3 | 2 | Partial |
| Auction sales value down 27% | 4 | 1 | Partial |
| Yayoi Kusama tops the ranking for the second year | 3 | 2 | Partial |

---

## Same Interpretation Examples

Records where both ontologies reach compatible conclusions.

### Example A: "The Art Market in 2025"

**Old assignments (7 observed):**
- `MarketUncertainty=True` (conf 0.94) — first-half contraction
- `CollectorFlightToSafety=True` (conf 0.92)
- `BlueChipConcentration=True` (conf 0.95)
- `PrestigeFragmentation=True` (conf 0.71)
- `RegionalSceneMomentum=True` (conf 0.90)
- `AIArtInstitutionalAcceptance=True` (conf 0.86)
- `AuthenticityPremium=True` (conf 0.83)

**Induced assignments (4 observed):**
- `FlightToQualityConcentration=True`
- `RegionalArtInfrastructureEmergence=True`
- `TrophyBuyerDemand=True`
- `AuctionConcentrationDynamics=True`

**Assessment: Compatible.** Both ontologies agree this record shows market concentration,
regional growth, and quality-seeking. The old ontology is more granular (7 specific
mechanisms). The induced ontology compresses several old variables into fewer concepts.
`FlightToQualityConcentration` maps to `CollectorFlightToSafety + BlueChipConcentration`;
`RegionalArtInfrastructureEmergence` maps to `RegionalSceneMomentum`.

---

### Example B: "Yayoi Kusama tops the ranking for the second year"

**Old assignments:**
- `BlueChipConcentration=True`
- `CollectorFlightToSafety=True`
- `PrestigeFragmentation=True` (conf 0.62)

**Induced assignments:**
- `FlightToQualityConcentration=True`
- `AuctionConcentrationDynamics=True`

**Assessment: Compatible.** Both ontologies agree this record shows market concentration
at the top. The induced `FlightToQualityConcentration` maps directly to the old
`CollectorFlightToSafety + BlueChipConcentration`. The old `PrestigeFragmentation`
assignment is lower confidence and disputed — a single artist topping rankings could
be read as either concentrated prestige (not fragmented) or as part of a fragmented
market where no collective narrative exists.

---

## Partially Different Interpretation Examples

Records where both ontologies engage but emphasize different dimensions.

### Example C: "Rediscovered Old Master Painting Eclipses Estimate at Auction"

**Old assignments:**
- `AuthenticityPremium=True` — rediscovered original work
- `CollectorFlightToSafety=True` — established prestige collecting
- `BlueChipConcentration=True` — Old Masters as blue-chip

**Induced assignments:**
- `TrophyBuyerDemand=True`
- `FreshToMarketPremium=True`

**Assessment: Partially different emphasis.** Both ontologies agree this record
involves high-prestige collecting. The old ontology frames it through authenticity
and safety-seeking; the induced ontology identifies the buyer motivation (trophy)
and the specific mechanism that created the premium (freshness/rediscovery).
`FreshToMarketPremium` has no old equivalent — it captures what made this lot
exceptional in a way the old ontology cannot express.

---

### Example D: "Auction sales value down 27%"

**Old assignments:**
- `MarketUncertainty=True`
- `CollectorFlightToSafety=True`
- `PrestigeFragmentation=True`
- `BlueChipConcentration=True` (implied)

**Induced assignments:**
- `SpeculativeDemandCollapse=True`

**Assessment: Partially different.** Both agree the market is contracting, but frame
it differently. The old ontology reads the decline through uncertainty and safety-seeking
(macro economic framing). The induced ontology reads it through the collapse of
speculative demand (market-microstructure framing). Both are defensible readings
of a record showing 27% auction value decline.

---

## Fundamentally Different Interpretation Examples

Records where the two ontologies produce incompatible readings.

### Example E: "How Did Phillips Pull Off a $115.2M White Glove Sale?"

**Old assignments:**
- `PrestigeFragmentation=True` (conf 0.67) — prestige authority still distributed
- `RegionalSceneMomentum=True` (conf 0.70) — Phillips operating outside traditional Big 3
- `CollectorFlightToSafety=True` — white-glove sale implies guaranteed quality

**Induced assignments:**
- `TrophyBuyerDemand=True` — $115M sale implies trophy-seeking
- `ThirdPartyGuaranteesInAuctions=True` — "white glove" implies guarantee mechanism
- `SpeculativeDemandCollapse=False` — white-glove success argues against speculation collapse

**Assessment: Significantly different.** The old ontology frames this record as evidence
of prestige fragmentation (Phillips, not Christie's/Sotheby's, achieving the sale) and
market safety-seeking. The induced ontology frames it mechanistically: trophy buying,
guarantee structures, and evidence against speculative collapse. The `SpeculativeDemandCollapse=False`
assignment has no analog in the old ontology, which lacks an inverse speculation variable.

This record is the clearest example of genuine interpretive divergence: both ontologies
are engaging with the same evidence but asking fundamentally different questions about it.

---

### Example F: "Post-Digital Scarcity and the Neo-Academic Signal"

**Old assignments (14 observed — richest record in old ontology):**
- `AuthenticityPremium=True`, `RitualAuraPremium=True`, `CraftPrestigeRising=True`
- `AntiDigitalSentiment=True`, `AIImageSaturation=True`
- `EmbodimentDiscourseRising=True`, `NeoAcademicResurgence=True`
- `CuratorialMaterialityShift=True`
- `BlueChipConcentration=True`, `PrestigeFragmentation=True`
- `CollectorFlightToSafety=True`, `MarketUncertainty=True`
- `AIArtInstitutionalAcceptance=True`
- `MuseumFigurativeAcceptance=True`

**Induced assignments (1 observed):**
- `PostDigitalMaterialAuthenticityPremium=True`

**Assessment: Drastically different.** This record is explicitly about art theory and
cultural criticism (the "post-digital" discourse), making it extremely relevant to the
old ontology's cultural and institutional variables. The old ontology assigns 14 of 25
variables, many at high confidence. The induced ontology assigns only 1 concept — and
that concept partially overlaps with several old variables.

The induced ontology has no analog for `RitualAuraPremium`, `NeoAcademicResurgence`,
`EmbodimentDiscourseRising`, `CraftPrestigeRising`, or `AntiDigitalSentiment` as
distinct concepts. This entire cluster of cultural/discourse variables gets compressed
into the single `PostDigitalMaterialAuthenticityPremium` concept.

This represents the most significant interpretive gap: the old ontology has 7 distinct
cultural theory variables; the induced ontology has one.

---

## Summary Statistics

| Category | Records | Percentage |
|---------|:-------:|:----------:|
| Both ontologies assign at least one concept | 30 | 43% |
| Old assigns, induced does not | 40 | 57% |
| Induced assigns, old does not | 0 | 0% (all induced records also have old assignments) |
| Compatible assignment direction | ~22 | ~73% of overlap records |
| Partially different emphasis | ~6 | ~20% of overlap records |
| Substantially divergent | ~2 | ~7% of overlap records |

**Assignment density gap:** The old ontology is 2.6× denser than the induced ontology
(12.8% vs. 4.9% assignment rate). This reflects both the larger variable set AND
the human analyst's ability to engage with subtler cultural and institutional signals.

**Coverage gap:** 40 of 70 records produce zero induced assignments. The old ontology
produces at least 1-2 assignments for every record. This gap is the most significant
practical difference between the two ontologies.
