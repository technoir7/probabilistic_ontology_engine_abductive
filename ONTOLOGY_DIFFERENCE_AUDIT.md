# Ontology Difference Audit

_Domain: Art Market (art-prestige-regime-v1 vs. poea-induced-v1)_
_Date: 2026-05-30_
_Methodology: Descriptive comparison. Neither ontology is treated as correct._

---

## How Do These Ontologies Differ in Practice?

This report synthesizes findings from six individual audits. It describes differences
without judging which ontology is superior.

---

## 1. Variable Vocabulary

**Old ontology:** 25 human-authored variables organized into three groups: Institutional
(11), Market (7), Cultural (7). Variables were designed by a domain expert to represent
causal mechanisms hypothesized to govern art market prestige dynamics. Vocabulary
was specified before evidence was ingested.

**Induced ontology:** 11 LLM-induced concepts, promoted from 21 raw proposals after
consolidation. Vocabulary was derived from the same 70 evidence records without
access to the old variable list. No concepts were specified in advance.

**Overlap:** No exact matches. Five concepts have partial or many-to-one correspondence.
Six induced concepts have no clear old equivalent. Eight-plus old variables have no
induced equivalent.

---

## 2. Conceptual Coverage

### What both ontologies agree on

Both ontologies identify art market concentration, regional growth, and institutional
validation as present in the evidence corpus:

| Shared phenomenon | Old concept | Induced concept |
|------------------|------------|----------------|
| Market concentration at top | `BlueChipConcentration` + `CollectorFlightToSafety` | `FlightToQualityConcentration` |
| Regional decentralization | `RegionalSceneMomentum` | `RegionalArtInfrastructureEmergence` |
| Institutional market effect | `MuseumAcquisitionMomentum` | `InstitutionalValidationPremium` |
| Authenticity/physical premium | `AuthenticityPremium` + `RitualAuraPremium` | `PostDigitalMaterialAuthenticityPremium` |
| Prestige hierarchy competition | `PrestigeFragmentation` | `AuctionConcentrationDynamics` (partial) |

### What only the old ontology captures

The old ontology has seven cultural and institutional theory variables with no induced
equivalents: `RitualAuraPremium`, `EmbodimentDiscourseRising`, `NeoAcademicResurgence`,
`CraftPrestigeRising`, `AntiDigitalSentiment`, `ConceptualDominance`, `BiennialFatigue`.

These variables engage art market discourse — theory texts, curatorial statements,
prestige hierarchy criticism. The induced ontology did not generate equivalents, likely
because the evidence corpus contains relatively few discourse-heavy records (the theoretical
essay "Post-Digital Scarcity and the Neo-Academic Signal" being the main exception).

The old ontology also has macro-condition variables that are near-omnipresent in the
evidence: `MarketUncertainty` (31/70 records), `PrestigeFragmentation` (30/70). The
induced ontology has no equivalent structural background-condition variables.

### What only the induced ontology captures

The induced ontology identified six concepts with no old equivalent:
- `AuctionCatalystEffect` — event-driven artist revaluation
- `FreshToMarketPremium` — scarcity premium from long-absent works
- `ThirdPartyGuaranteesInAuctions` — auction risk-transfer mechanism
- `AIEnabledCollectorOnboarding` — AI as collector access tool (demand-side infrastructure)
- `TrophyBuyerDemand` — high-net-worth buyer psychology (status-seeking)
- `SpeculativeDemandCollapse` — speculative market exit (inverse of old `AuctionSpeculationElevated`)

These are mechanism-level concepts arising from specific events in the evidence: a white
glove sale, a rediscovered Old Master, AI discovery tools, trophy auctions. The old
ontology could not have captured them because it was designed for monthly API-derived
aggregate signals, not article-level event descriptions.

---

## 3. Assignment Patterns

**Old ontology assigns 2.6× more densely** (12.8% vs. 4.9% of all pairs).

**Old ontology achieves 100% record coverage** (all 70 records receive ≥1 assignment).
The induced ontology assigns 0 concepts to 40 of 70 records (57%).

**The core reason for the coverage gap:**

The old ontology uses two epistemological strategies:
1. **Structural background conditions:** Variables like `MarketUncertainty` and
   `BlueChipConcentration` are assigned whenever the evidence implies a market state,
   even without explicit mechanism description.
2. **Specific mechanism signals:** Cultural and institutional variables require explicit
   content matching.

The induced ontology uses only one strategy:
1. **Explicit mechanism description required:** A concept is assigned only when the evidence
   text describes the mechanism named by the concept.

This difference explains most of the coverage gap. The 40 orphan records (ranking
statistics, auction week summaries, press releases) all receive old ontology assignments
from strategy (1) but no induced assignments because strategy (1) does not exist
in the induced system.

---

## 4. Evidence Theory Differences

The two ontologies operate under different implicit theories of what evidence means.

**Old ontology:** Evidence is a window onto structural states of the art market.
A list of top-selling auction artists implies blue-chip concentration is present.
A museum press release implies acquisition momentum exists. Evidence confirms or
disconfirms background conditions.

**Induced ontology:** Evidence is a description of a specific event or mechanism.
A press release describes an event. An auction summary describes an outcome. Only
records that describe an identifiable causal mechanism trigger concept assignment.

Neither evidence theory is uniquely correct. The old approach ensures comprehensive
coverage at the cost of imputed assumptions. The induced approach ensures precision
at the cost of leaving many records unaddressed.

---

## 5. Causal Structure Differences

**Old ontology structure (after 6 learning generations, 70 records):**

The dominant hypothesis (H3 DefensiveBlueChipConsolidation, marginally) proposes:
```
MarketUncertainty → CollectorFlightToSafety → BlueChipConcentration → InstitutionalRiskAversion
```

This is a macro-economic chain: uncertainty → behavioral response → market structure → institutional response.

The most evidence-supported edge (4 explicit causal claims):
```
MarketUncertainty → CollectorFlightToSafety
```

H4 PrestigeFragmentation (competing hypothesis) proposes:
```
AttentionFragmentation → PrestigeFragmentation → RegionalSceneMomentum
```

The population remains contested between H3 and H4 — the evidence equally supports
both narratives (log_score difference: 0.19, within BIC noise).

**Induced ontology structure (after 1 learning generation, 30 records):**

The only emerging edge: `TrophyBuyerDemand → FreshToMarketPremium` (p=0.156, unconfirmed)

This proposes: wealthy buyers seeking trophy works drive up premiums on newly
surfaced historical works. It is a market microstructure relationship not present
in the old ontology at all.

The induced population has no differentiation yet (all 10 candidates tied at −21.01).
No structural story has emerged.

**What the structural difference tells us:**

The old ontology found structure because its variables are designed to be sensitive to
the corpus, its evidence coverage is complete (70/70 records), and it has run through
6 learning generations. The induced ontology has not found structure yet because 40/70
records provide no signal, and one learning cycle is insufficient.

**The structural story that has emerged** from the old ontology (defensive blue-chip
consolidation under market uncertainty) is consistent with the induced ontology's
strongest signals (FlightToQualityConcentration, TrophyBuyerDemand, AuctionConcentrationDynamics)
— both point toward capital concentration at the top of the market. They are telling
related stories with different vocabularies.

---

## 6. Where the Disagreements Are Deepest

**Deepest coverage disagreement:** Art discourse records ("Post-Digital Scarcity and
the Neo-Academic Signal" — 14 old assignments, 1 induced). The old ontology has a
rich cultural theory vocabulary; the induced ontology generates market-mechanism
concepts.

**Deepest framing disagreement:** The Phillips white-glove sale — old ontology reads
this as prestige fragmentation (non-dominant auction house succeeds); induced reads
it as trophy demand concentration (large sale = wealthy buyers). Both are defensible
from the same evidence.

**Deepest directional disagreement:** Declining auction market records — old reads
as uncertainty → flight to safety; induced reads as speculative demand collapse.
Different causes, same observable (price decline).

---

## 7. How Do These Ontologies Differ? — Direct Answer

| Dimension | How they differ |
|-----------|----------------|
| **Vocabulary size** | Old: 25 variables; Induced: 11 concepts — induced is more compact |
| **Vocabulary origin** | Old: human expert a priori; Induced: LLM from evidence |
| **Coverage** | Old: 100% of records assigned; Induced: 43% — massive gap |
| **Assignment density** | Old: 12.8%; Induced: 4.9% — old is 2.6× denser |
| **Causal resolution** | Old: separates cause from effect (flight → concentration); Induced: merges (FlightToQualityConcentration) |
| **Event granularity** | Old: monthly structural states; Induced: episode-level mechanisms |
| **Cultural dimension** | Old: has 7 cultural/discourse variables; Induced: has none equivalent |
| **Market mechanics** | Old: lacks auction microstructure; Induced: has ThirdPartyGuarantees, FreshToMarketPremium |
| **AI framing** | Old: AI as culture/backlash force; Induced: AI as collector onboarding infrastructure |
| **Structure learned** | Old: H3/H4 competition after 6 cycles; Induced: no structure after 1 cycle |
| **Dominant narrative** | Old: market uncertainty → blue-chip flight; Induced: no narrative yet |

---

## Limitations of This Comparison

1. **Different evidence volumes fed to old POE:** Old POE used 70 records; induced POE
   used only 30 (40 orphaned). This is a confound in the structural comparison.

2. **Different generation counts:** Old POE ran 6 generations; induced ran 1. The
   induced ontology's structural results are immature by design.

3. **Different assignment methods:** Old assignments are human-authored (manual LLM
   annotation with confidence and rationale); induced assignments are automated LLM
   scoring against concept definitions. These are not equivalent epistemological processes.

4. **Evidence selection:** Both ontologies use the same 70 records. The induced ontology
   was designed for prose articles; the old ontology was designed for API-derived signals.
   The current evidence corpus (prose articles) may favor the induced ontology's
   mechanism-detection approach.

5. **The old ontology has not been run on this corpus with pgmpy posteriors available.**
   The structural comparison uses causal claims and log_score rankings, not marginal
   posterior distributions.

---

## Conclusion

These two ontologies are not competing answers to the same question. They are asking
somewhat different questions of the same evidence:

- **Old ontology asks:** What structural states of the art market does this evidence
  reflect?

- **Induced ontology asks:** What causal mechanisms does this evidence describe?

The old ontology has broader evidence coverage and a richer cultural vocabulary.
The induced ontology has better mechanism specificity and identifies episode-level
phenomena the old ontology cannot represent.

The most surprising finding is that the two ontologies share a common core story —
capital concentration at the top of the market under conditions of uncertainty — but
express it through different conceptual lenses and with different granularity. The
old ontology has a complete causal chain (uncertainty → flight → concentration → institutional
conservatism). The induced ontology has the concept but not yet the chain (FlightToQualityConcentration
as a single merged concept, plus TrophyBuyerDemand as a separate but related observation).

The induced ontology found genuinely novel concepts (AuctionCatalystEffect, FreshToMarketPremium,
ThirdPartyGuaranteesInAuctions) that the old ontology cannot express. Whether these
are important causal mechanisms or incidental observations from a small evidence corpus
remains an open question.
