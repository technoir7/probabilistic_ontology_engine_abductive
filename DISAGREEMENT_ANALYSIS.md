# Disagreement Analysis

_Domain: Art Market_
_Date: 2026-05-30_

---

## Framework

A "disagreement" is any record where the two ontologies reach substantially different
conclusions — different variable counts, different concepts activated, or genuinely
opposed framings of the same evidence.

Three types of disagreement are analyzed:
1. **Coverage disagreement** — old ontology assigns; induced assigns nothing
2. **Framing disagreement** — both assign but emphasize different mechanisms
3. **Directional disagreement** — both engage the same phenomenon but frame it inversely

---

## Type 1: Coverage Disagreement — Evidence the Induced Ontology Cannot Read

40 of 70 records produce zero induced assignments. These are orphan records for the
induced ontology. The old ontology reads all 40 of them.

### Category A: Hiscox Artist Rankings (14 records)

**Example records:**
- "Hiscox Artist Top 100 2025 Introduction"
- "More women in this year's HAT 100"
- "Number of artists at auction reaches a record high"
- "Female Artists: Analysis of New Records"
- "Non-Western art market presence"

**Old ontology reads:** `BlueChipConcentration=True`, `CollectorFlightToSafety=True`,
`PrestigeFragmentation=True` (2-3 assignments per record, low confidence).

**Induced ontology reads:** Nothing. These records discuss artist ranking statistics
and demographic composition without using the vocabulary of mechanisms (auctions,
trophy buying, infrastructure, speculation) that would trigger induced concepts.

**Why the divergence:** The old ontology has structural state variables (`BlueChipConcentration`,
`PrestigeFragmentation`) that the analyst assigns when any ranking evidence is present —
as background conditions of the current art market. The induced concepts require
specific causal mechanisms to be described; a list of top-ranked artists does not
describe a mechanism.

**Which reading is more defensible:** Both are defensible. The old reading imposes
structural assumptions (rankings imply concentration); the induced reading correctly
notes that no mechanism is described. Whether the background-condition reading adds
epistemic value or noise is the core disagreement.

---

### Category B: SFMOMA Press Releases (6 records)

**Example records:**
- "SFMOMA to Unveil Complete Transformation of the Renowned Doris and Donald Fisher Collection"
- "Global Debut of RM x SFMOMA Exhibition Opens to the Public"
- "SFMOMA to Open Graciela Iturbide: Between Two Worlds, a Major Retrospective"

**Old ontology reads:** `BlueChipConcentration`, `MarketUncertainty` (2-3 assignments).

**Induced ontology reads:** Nothing except for "SFMOMA Announces Landmark Jacob
Hashimoto Installation" (InstitutionalValidationPremium=True) and "Three Artists Win
SFMOMA's 2026 SECA Art Award" (InstitutionalValidationPremium=True).

**Why the divergence:** The old analyst assigned market structural variables
(`BlueChipConcentration`, `MarketUncertainty`) to museum announcements, presumably
reading them as part of the broader museum acquisition ecosystem. The induced
ontology only fires `InstitutionalValidationPremium` when the institutional event
is framed as directly elevating an artist's market position. Generic SFMOMA programming
announcements do not trigger this.

**Driver:** Difference in evidence theory. Old ontology uses holistic background-condition
reading; induced ontology uses specific mechanism-trigger reading.

---

### Category C: Auction Market Data Summaries (12 records)

**Example records:**
- "Christie's Posts 'Rock Solid' Contemporary Sale, Led by Marian Goodman's Gerhard Richters"
- "Who Won New York's $2.5 Billion Auction Week?"
- "Sotheby's Buoyant $303.4 Million Modern Art Evening Sale: By the Numbers"
- "The New York Fairs Are Done. What Remains?"

**Old ontology reads:** `BlueChipConcentration=True`, `CollectorFlightToSafety=True`,
`PrestigeFragmentation=True`, `RegionalSceneMomentum=True` (3-4 assignments each).

**Induced ontology reads:** Nothing.

**Why the divergence:** These records describe overall auction week results with dollar
totals and headline lots. The old ontology reads them as confirming structural conditions
(high dollar amounts → blue chip concentration). The induced ontology does not fire
because these records describe outcomes without narrating the mechanisms that the
induced concepts require.

**Concrete example — "Who Won New York's $2.5 Billion Auction Week?":**
Old: BlueChipConcentration=True (large dollar totals → top-of-market), CollectorFlightToSafety=True
(established names dominating), PrestigeFragmentation=True (multiple winners across categories).
Induced: Nothing. The headline asks "who won" but the induced concepts require "what mechanism."

**Driver:** Evidence theory. The old ontology asks "what state does this evidence
reflect?" The induced ontology asks "what mechanism does this evidence describe?"

---

## Type 2: Framing Disagreement — Same Evidence, Different Questions

### Example 1: "Is A Random Unknown Artist More Valuable Than Picasso? AI Thinks So."

**Old ontology reads:**
- `AIImageSaturation=True`
- `BlueChipConcentration=True`
- `PrestigeFragmentation=True`
- `AuthenticityPremium=True`

**Induced ontology reads:** Nothing.

**Analysis:** The old ontology reads this speculative article as confirming structural
conditions (AI is prevalent; blue-chip names remain dominant; prestige hierarchy is under
question; authenticity matters). The induced ontology finds no specific mechanism — the
article is arguing a counterfactual about AI valuation, not describing an observed auction
mechanism.

**Driver:** The old ontology is willing to read speculative/editorial content as
confirming structural conditions. The induced ontology requires mechanism descriptions.

---

### Example 2: "Lalanne's Playful Frog Fountains Surface at Auction"

**Old ontology reads:**
- `CollectorFlightToSafety=True` (established estate lot)
- `BlueChipConcentration=True` (Lalanne = high-prestige established artist)
- `AuthenticityPremium=True` (sculptural craft work)
- `RitualAuraPremium=True` (unique physical work)

**Induced ontology reads:** Nothing.

**Analysis:** Lalanne is an established decorative arts artist. The old ontology
assigns high-prestige structural conditions. The induced ontology finds no mechanism
signal — the article announces an auction lot without describing the demand dynamics
or market mechanisms that would trigger induced concepts.

**Driver:** The induced ontology has no concept for "established prestige artist
selling well" as a mechanism. `TrophyBuyerDemand` is the closest but did not fire,
suggesting the LLM scorer did not detect trophy-seeking in this specific context.

---

## Type 3: Directional Disagreement — Inverse Framings of the Same Phenomenon

### Example: "How Did Phillips Pull Off a $115.2 Million 'White Glove' Sale?"

This is the clearest directional disagreement in the corpus.

**Old ontology reads:**
- `PrestigeFragmentation=True` (Phillips, not Sotheby's/Christie's, achieving the sale)
- `RegionalSceneMomentum=True` (Phillips = institutional decentralization)
- `CollectorFlightToSafety=True` (guaranteed, all-sold event = safety)

**Induced ontology reads:**
- `TrophyBuyerDemand=True` (large auction → trophy-seeking demand)
- `ThirdPartyGuaranteesInAuctions=True` ("white glove" = guarantee mechanism)
- `SpeculativeDemandCollapse=False` (white glove success = evidence against speculation collapse)

**The directional disagreement:** The old ontology reads the success of a Phillips
sale as evidence of prestige fragmentation (the Big Three are no longer the only
venue for record-setting results). The induced ontology reads it as evidence of
trophy-buyer demand concentration (large sale = concentrated demand from wealthy buyers).

These framings are not just different — they imply opposite structural conclusions:
- Old reading: prestige is decentralizing (fragmentation hypothesis H4)
- Induced reading: prestige demand is concentrating among trophy buyers

**What caused this divergence:** Both readings are logically defensible from the
same evidence. The divergence reflects different hypotheses about what the success
of a Phillips record sale means for the art market structure.

---

### Example: "Auction sales value down 27%"

**Old ontology reads:**
- `MarketUncertainty=True`
- `CollectorFlightToSafety=True`
- `PrestigeFragmentation=True`

**Induced ontology reads:**
- `SpeculativeDemandCollapse=True`

**The directional disagreement:** The old ontology frames a 27% decline as uncertainty
driving collectors toward safety (H3 narrative). The induced ontology frames it as
speculative demand collapsing (the speculative buyers have exited). Both describe
a declining market but attribute it to different mechanisms.

**Implication for structure learning:**
- H3 narrative predicts: decline → market normalizes around blue-chip assets
- SpeculativeDemandCollapse narrative predicts: decline → quality concentration follows (market sorting itself)

These are empirically distinguishable if the follow-on data were available.

---

## Evidence Categories Producing Largest Disagreements

### 1. Specific mechanism records (old: sparse; induced: triggered)

Records describing auction mechanics, price guarantees, and specific market structures
trigger induced concepts but produce sparse old ontology assignments:
- "How Did Phillips Pull Off...White Glove Sale?" — 3 induced, 3 old (but divergent)
- "Rediscovered Old Master Painting Eclipses Estimate" — 2 induced, 3 old (partially convergent)

### 2. Cultural/discourse records (old: rich; induced: sparse or absent)

Records discussing art theory, cultural discourse, and institutional criticism trigger
old ontology variables but not induced concepts:
- "Post-Digital Scarcity and the Neo-Academic Signal" — 14 old, 1 induced (largest gap)
- "EmbodimentDiscourseRising" and "NeoAcademicResurgence" have no induced equivalents

### 3. Statistical/ranking records (old: background conditions; induced: silent)

Records presenting aggregate statistics, rankings, and demographic data:
- Both Hiscox and Artprice aggregate records receive old ontology background assignments
- Induced ontology reads all of them as neutral

---

## Summary: What Causes Ontology Divergence?

| Cause | Records affected | Direction |
|-------|:----------------:|-----------|
| Evidence theory difference (state vs. mechanism) | ~30 | Old reads all; induced silent |
| Cultural vocabulary gap (old has theory concepts; induced doesn't) | ~10 | Old rich; induced sparse |
| Causal compression (induced merges multiple old variables) | ~20 | Fewer induced assignments for same evidence |
| Novel mechanism detection (induced finds what old misses) | ~5 | Induced fires; old silent |
| Directional framing (same phenomenon, opposite interpretation) | ~3 | Genuine interpretive disagreement |

The dominant driver of disagreement is the **evidence theory difference**: the old
ontology assigns background structural conditions to most records regardless of
specific mechanism content; the induced ontology requires explicit mechanism signal
before assigning any concept. This explains the 57% orphan rate for the induced
ontology and the 0% orphan rate for the old ontology.
