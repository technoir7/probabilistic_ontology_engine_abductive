# Concept Correspondence Audit

_Domain: Art Market_
_Date: 2026-05-30_
_Methodology: Semantic comparison of concept definitions, evidence patterns, and causal roles_

---

## Approach

Each induced concept is compared against old ontology variables using:
1. Semantic similarity of definitions
2. Evidence record overlap (which records triggered each)
3. Causal role (driver/outcome/structural)

Neither ontology is treated as correct. Correspondences are descriptive.

---

## Partial Correspondences

Concepts that substantially overlap but differ in scope or framing.

### 1. `FlightToQualityConcentration` (induced) ↔ `CollectorFlightToSafety` + `BlueChipConcentration` (old)

**Classification:** Many-to-one (two old variables → one induced concept)

**Induced definition:** "During periods of geopolitical or economic uncertainty, collectors reallocate capital toward top-ranked artists and auction houses, producing a measurable concentration of value at the top of the market."

**Old definitions:**
- `CollectorFlightToSafety`: Collectors retreating to established, lower-risk names
- `BlueChipConcentration`: Top-decile artists capturing disproportionate share

**Rationale:** The induced concept merges the behavioral mechanism (collector flight)
with its structural outcome (market concentration) into a single observable. The old
ontology separates cause (flight) from effect (concentration), which enables the causal
edge `CollectorFlightToSafety → BlueChipConcentration` in H3. The induced concept
collapses this into one observable, losing the intermediate causal step but gaining
a more directly measurable unit.

**Evidence overlap:** Both concepts were scored on "The Art Market in 2025" — the record
with the most complete assignments in both ontologies.

---

### 2. `RegionalArtInfrastructureEmergence` (induced) ↔ `RegionalSceneMomentum` (old)

**Classification:** Partial correspondence

**Induced definition:** "The growth of local gallery, museum, and auction ecosystems in new geographic areas re-routes demand away from traditional centers."

**Old definition:** `RegionalSceneMomentum` — Non-center scenes gaining market visibility.

**Rationale:** Both concepts point to the same phenomenon: geographic decentralization
of the art market. The induced version emphasizes institutional infrastructure growth
(galleries, museums, auction houses as a system). The old version emphasizes visibility
and market momentum without requiring institutional depth.

**Key difference:** The induced concept is structural (infrastructure as precondition);
the old concept is market-behavioral (momentum and attention). Evidence like
"Art Basel Qatar Names Wassan Al-Khudhairi Artistic Director for 2027" triggered
the induced concept (institutional appointment) but would map more ambiguously to the
old `RegionalSceneMomentum` (which focuses on market results, not appointments).

---

### 3. `PostDigitalMaterialAuthenticityPremium` (induced) ↔ `AuthenticityPremium` + `AntiDigitalSentiment` (old)

**Classification:** Many-to-one (with causal compression)

**Induced definition:** "The saturation of AI-generated digital art elevates the cultural and market value of physical, handmade, and unique artworks."

**Old definitions:**
- `AuthenticityPremium`: Valuation premium for handmade, singular, provenance-rich works
- `AntiDigitalSentiment`: Market or cultural backlash against digital/AI work

**Rationale:** The induced concept embeds a causal claim (AI saturation → materiality premium)
that the old ontology represents as two separate variables linked by an inferred edge
(`AntiDigitalSentiment → AuthenticityPremium` appears in the causal claims data).
The induced concept is economically framed (valuation, market value); the old variables
include a cultural/sentiment variable (`AntiDigitalSentiment`) without requiring it to be
market-facing.

**The old ontology also has:** `RitualAuraPremium` and `CraftPrestigeRising`, which
the induced ontology does not distinguish from general authenticity premiums. The old
ontology has more granular resolution of the materiality/authenticity cluster.

---

### 4. `InstitutionalValidationPremium` (induced) ↔ `MuseumAcquisitionMomentum` + `AIArtInstitutionalAcceptance` (old, partial)

**Classification:** Partial correspondence (broader than any single old variable)

**Induced definition:** "Institutional exhibitions such as museum shows and biennials elevate artists' visibility and market value."

**Old definitions:**
- `MuseumAcquisitionMomentum`: Museums actively acquiring at elevated rate
- `AIArtInstitutionalAcceptance`: AI-tagged art accepted into institutional acquisitions
- (`BlueChipInstitutionalCapture`: Blue-chip artists dominating museum programming — never observed)

**Rationale:** The induced concept captures the general mechanism of institutional
validation translating to market premium, regardless of whether the work is
AI, figurative, or established. The old ontology splits institutional engagement
by type: acquisition activity (`MuseumAcquisitionMomentum`) is distinct from
specific acceptance of AI art (`AIArtInstitutionalAcceptance`). The induced
concept loses this specificity but gains generality.

**Evidence triggering `InstitutionalValidationPremium`:** SFMOMA SECA Award,
Venice Biennale, museum acquisitions — these are all validation events. The old
`MuseumAcquisitionMomentum` variable specifically requires acquisition activity,
so the Venice Biennale article would score differently.

---

### 5. `AuctionConcentrationDynamics` (induced) ↔ `BlueChipConcentration` (old, partial)

**Classification:** Partial correspondence

**Induced definition:** "A structural mechanism by which a small elite of artists and auction houses captures a disproportionate share of total auction value."

**Old definition:** `BlueChipConcentration` — Top-decile artists capturing disproportionate auction share.

**Rationale:** Both describe market concentration at the top of the auction hierarchy.
The induced concept explicitly names the mechanism (structural) and includes auction
houses as agents, not just artists. The old variable is purely artist-focused.
The induced concept is also framed around a dynamic (ongoing process) rather than
a state (concentration exists).

**Key difference:** The old `BlueChipConcentration` is a state variable; the induced
`AuctionConcentrationDynamics` is a mechanism variable. The distinction matters for
causal inference: old POE can learn `MarketUncertainty → CollectorFlightToSafety → BlueChipConcentration`.
The induced concept is harder to place as a downstream outcome of uncertainty because
it describes the process rather than the result.

---

## Novel Induced Concepts (No Clear Old Counterpart)

Induced concepts that do not map to any old ontology variable.

### 6. `AuctionCatalystEffect`

**Induced definition:** "A single high-profile auction event that revalues an artist's market by generating widespread attention, setting a new price benchmark, and increasing demand."

**Old ontology gap:** The old ontology has no event-level variable. All old variables
describe structural states or persistent conditions. The `AuctionCatalystEffect` captures
the episodic, event-driven nature of auction price-discovery — a concept the old
ontology cannot represent because its variables are designed for monthly cadence
with rolling-window aggregate signals (Artsy ratios, FRED series).

**Evidence:** "Top movers: Maurizio Cattelan" and "Top movers: Lucian Freud" both
triggered this concept — records describing specific auction events that reset price
benchmarks. The old ontology would not have flagged these records at all.

---

### 7. `FreshToMarketPremium`

**Induced definition:** "The valuation uplift assigned to artworks that have been long hidden, recently rediscovered, or absent from the auction circuit."

**Old ontology gap:** No equivalent. The old ontology's `AuthenticityPremium` covers
provenance but does not distinguish between widely-traded authenticated works and
newly-surfaced works. The `FreshToMarketPremium` captures market scarcity created by
temporal absence — a concept absent from the monthly-aggregate old ontology because
it requires tracking individual lot provenance.

**Evidence:** "Rediscovered Old Master Painting Eclipses Estimate at Auction" is the
single record that triggered this concept. The old ontology assigned `AuthenticityPremium`
and `CollectorFlightToSafety` to the same record — different interpretation.

---

### 8. `ThirdPartyGuaranteesInAuctions`

**Induced definition:** "A mechanism where a third party commits to a minimum sale price before the auction, reducing consignor risk and enabling premium lots to come to market."

**Old ontology gap:** No equivalent. The old ontology has no mechanism variable for
auction risk-transfer. This is a market microstructure concept absent from the
art prestige regime framing (which focuses on prestige, culture, and institutional
dynamics rather than auction mechanics).

**Evidence:** "How Did Phillips Pull Off a $115.2 Million 'White Glove' Sale?" triggered
this concept. A white-glove sale (100% sold rate) is enabled partly by guarantees.
The old ontology assigned `MarketUncertainty=False` (implied), `CollectorFlightToSafety`,
`AuctionSpeculationElevated` to this record — interpreting the same event through
different lenses.

---

### 9. `AIEnabledCollectorOnboarding`

**Induced definition:** "AI tools and digital platforms reduce barriers to art market entry by offering education, discovery, and transaction support, injecting new collector demand."

**Old ontology gap:** No equivalent. The old ontology has `AIArtInstitutionalAcceptance`
(AI as a subject of art) and `AIImageSaturation` (AI as a cultural pollutant/stimulus),
but no variable for AI as an infrastructure tool that facilitates collector participation.
The induced concept captures a demand-side market development that the old ontology
does not contemplate.

---

### 10. `SpeculativeDemandCollapse`

**Induced definition:** "The rapid withdrawal of high-risk, short-term buying aimed at flipping artworks for quick profit."

**Old ontology note:** The old ontology has `AuctionSpeculationElevated` — the *presence*
of speculation. The induced concept captures the *collapse* — when speculation ends.
This is a near-inverse relationship: both ontologies identify speculation as a market
force, but the induced concept orients around its withdrawal while the old concept
orients around its presence.

**Causal implication:** In the old ontology, `AuctionSpeculationElevated` is a state
variable in the market group. In the induced ontology, `SpeculativeDemandCollapse`
is framed as a mechanism that concentrates quality-seeking behavior (linked to
`FlightToQualityConcentration`). The induced framing implies a different causal story:
not "speculation is high" but "speculation ended and quality-seeking replaced it."

---

### 11. `TrophyBuyerDemand`

**Induced definition:** "Demand from high-net-worth collectors seeking iconic, unique, or status-signaling artworks that concentrate value at a small number of works."

**Old ontology partial match:** `CollectorFlightToSafety` captures the behavioral
retreat to established names, but not the trophy-seeking motivation. `BlueChipConcentration`
captures the structural outcome. Neither captures the buyer psychology of trophy-seeking
specifically.

**Classification:** Partial, close to novel. The induced concept identifies a specific
buyer archetype and motivation (trophy/status-seeking) absent from the old ontology's
variable vocabulary, which is more concerned with market structure than buyer intent.

---

## Old Variables with No Induced Counterpart (Missing Concepts)

Old variables that the induced ontology does not represent.

| Old variable | Observation count | Assessment |
|-------------|:-------------------:|-----------|
| `MarketUncertainty` | 31 | Most frequently observed old variable; absent from induced ontology |
| `PrestigeFragmentation` | 30 | Second most observed; induced has `RegionalArtInfrastructureEmergence` as partial proxy |
| `CollectorFlightToSafety` | 28 | Partially absorbed into `FlightToQualityConcentration` |
| `BlueChipConcentration` | 32 | Partially absorbed into `FlightToQualityConcentration` + `AuctionConcentrationDynamics` |
| `AuthenticityPremium` | 25 | Partially captured by `PostDigitalMaterialAuthenticityPremium` (narrower) |
| `RitualAuraPremium` | 19 | Partially captured by `PostDigitalMaterialAuthenticityPremium` (cultural dimension) |
| `MuseumAcquisitionMomentum` | 14 | Partially captured by `InstitutionalValidationPremium` |
| `RegionalSceneMomentum` | 21 | Partially captured by `RegionalArtInfrastructureEmergence` |
| `AIArtInstitutionalAcceptance` | 5 | Partially captured by `InstitutionalValidationPremium` |
| `NeoAcademicResurgence` | 3 | Not captured |
| `EmbodimentDiscourseRising` | 1 | Not captured |
| `MarketPolarization` | 1 | Not captured |
| `BiennialFatigue` | 1 | Not captured |
| `AIImageSaturation` | 1 | Partially captured by `PostDigitalMaterialAuthenticityPremium` (as cause) |
| `CuratorialMaterialityShift` | 1 | Not captured |
| `CraftPrestigeRising` | 1 | Not captured |
| `AntiDigitalSentiment` | 1 | Partially captured by `PostDigitalMaterialAuthenticityPremium` |
| `AuctionSpeculationElevated` | 1 | Inversely captured by `SpeculativeDemandCollapse` |
| `ConceptualDominance` | 1 | Not captured |
| `MuseumFigurativeAcceptance` | 1 | Not captured |

**Five old variables never observed in this corpus:**
`InstitutionalRiskAversion`, `FigurativeAuctionMomentum`, `EmergingMarketLiquidity`,
`BlueChipInstitutionalCapture`, `AttentionFragmentation`

---

## Summary Classification

| Category | Count | Examples |
|---------|:-----:|---------|
| Partial correspondence | 5 | FlightToQuality↔CollectorFlight+BlueChip; RegionalInfrastructure↔RegionalMomentum |
| Many-to-one (old→induced) | 2 | BlueChip+CollectorFlight→FlightToQuality; AuthenticityPremium+AntiDigital→PostDigital |
| Novel induced (no old equivalent) | 6 | AuctionCatalystEffect, FreshToMarketPremium, ThirdPartyGuarantees, AIEnabledOnboarding, TrophyBuyerDemand, SpeculativeDemandCollapse (inverse) |
| Missing in induced (old→nothing) | 8+ | MarketUncertainty, NeoAcademicResurgence, CraftPrestigeRising, EmbodimentDiscourseRising, MarketPolarization, BiennialFatigue, ConceptualDominance, MuseumFigurativeAcceptance |
