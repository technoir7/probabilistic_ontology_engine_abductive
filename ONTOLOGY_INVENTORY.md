# Ontology Inventory

_Domain: Art Market / Art Prestige Regime_
_Date: 2026-05-30_

---

## Old Ontology: art-prestige-regime-v1

**Source:** `art-market-domain/src/art_prestige_regime_v1/domain.py`

**Design approach:** Human-authored. Variables selected by a domain expert to represent
the causal mechanisms hypothesized to govern art market prestige dynamics.

### Variable Count

25 variables (all BOOLEAN).

### Variable Groups

**Institutional (11 variables)**

| Variable | Description |
|----------|-------------|
| `InstitutionalRiskAversion` | Museums and institutions avoiding experimental acquisitions |
| `MuseumFigurativeAcceptance` | Museum programming expanding to include figurative/craft work |
| `ConceptualDominance` | Conceptual frameworks dominating institutional discourse |
| `AIArtInstitutionalAcceptance` | AI-tagged art accepted into institutional acquisitions |
| `CuratorialMaterialityShift` | Curators emphasizing material, physical medium in programming |
| `CraftPrestigeRising` | Craft-based practices gaining prestige in market and institutions |
| `PrestigeFragmentation` | Prestige hierarchy fragmenting; no single dominant narrative |
| `RegionalSceneMomentum` | Non-center (non-NYC/LA/London) scenes gaining market visibility |
| `BlueChipInstitutionalCapture` | Blue-chip artists dominating museum programming |
| `BiennialFatigue` | Art fairs and biennials seen as expensive and diminishing returns |
| `MuseumAcquisitionMomentum` | Museums actively acquiring at elevated rate |

**Market (7 variables)**

| Variable | Description |
|----------|-------------|
| `BlueChipConcentration` | Top-decile artists capturing disproportionate auction share |
| `AuctionSpeculationElevated` | High-risk speculative buying elevated in auction markets |
| `CollectorFlightToSafety` | Collectors retreating to established, lower-risk names |
| `FigurativeAuctionMomentum` | Figurative/representational lots achieving strong auction results |
| `EmergingMarketLiquidity` | Emerging artist lots selling freely; younger market is liquid |
| `MarketPolarization` | Market growth concentrated at extremes; middle squeezed |
| `MarketUncertainty` | Broad market-level uncertainty from economic or geopolitical stress |

**Cultural (7 variables)**

| Variable | Description |
|----------|-------------|
| `RitualAuraPremium` | Premium on ritual presence, singularity, and aura (Benjaminian) |
| `EmbodimentDiscourseRising` | Theoretical discourse emphasizing embodied, physical experience |
| `AntiDigitalSentiment` | Market or cultural backlash against digital/AI work |
| `AIImageSaturation` | AI-generated images flooding visual culture |
| `AuthenticityPremium` | Valuation premium for hand-made, singular, provenance-rich works |
| `NeoAcademicResurgence` | Figurative/academic painting gaining institutional/market momentum |
| `AttentionFragmentation` | Audience attention dispersed across competing scenes and channels |

### Seed Hypotheses (5 OntologyCandidates)

| Hypothesis | Description | Key edges |
|-----------|-------------|-----------|
| H1 CraftAuraBacklash | AI saturation → aura premium → craft/figurative institutionalisation | AIImageSaturation→RitualAuraPremium→CraftPrestigeRising→MuseumFigurativeAcceptance |
| H2 AINormalization | AI saturation absorbed into institutional legitimacy | AIImageSaturation→AIArtInstitutionalAcceptance→MuseumAcquisitionMomentum |
| H3 DefensiveBlueChipConsolidation | Market uncertainty → blue-chip flight → institutional conservatism | MarketUncertainty→CollectorFlightToSafety→BlueChipConcentration→InstitutionalRiskAversion |
| H4 PrestigeFragmentation | Attention dispersal fractures prestige hierarchy → regional momentum | AttentionFragmentation→PrestigeFragmentation→RegionalSceneMomentum |
| H5 NeoAcademicResurgence | Aura + authenticity premium → neo-academic figurative revival | RitualAuraPremium+AuthenticityPremium→NeoAcademicResurgence→MuseumFigurativeAcceptance |

### Evidence Corpus Results

After running old POE on 70 evidence records (art_prestige_regime.db):

- Evidence records: 70
- Domain: art_prestige_regime_v1
- Generation reached: 6
- Active candidates: 10 (5 seed + 5 variants)
- Dominant candidate: H4 PrestigeFragmentation (log_score −38.13, tie with H3 variants)
- Paradigm shift count: 1 (H1 CraftAuraBacklash → H4 PrestigeFragmentation)
- Variables observed (true): 218 assignments across 20 of 25 variables
- Variables observed (false): 6 assignments
- Variables never observed: 5 (InstitutionalRiskAversion, FigurativeAuctionMomentum, EmergingMarketLiquidity, BlueChipInstitutionalCapture, AttentionFragmentation)

---

## Induced Ontology: poea-induced-v1

**Source:** `artifacts/canonical_concepts.json`

**Design approach:** Abductively induced by LLM from raw evidence text (no pre-specified
variable vocabulary). Concepts induced bottom-up from the same 70 evidence records.
Pre-existing variable annotations (`assignments`, `causal_claims`) stripped before
induction to prevent vocabulary leakage.

### Concept Count

11 active concepts (promoted from 21 raw proposals after consolidation).

### Active Concepts

| Concept | Confidence | Supporting evidence | Definition summary |
|---------|:----------:|:-------------------:|-------------------|
| `RegionalArtInfrastructureEmergence` | 0.90 | 3 | Growth of local gallery/museum/auction ecosystems in new geographic areas |
| `SpeculativeDemandCollapse` | 0.90 | 4 | Withdrawal of high-risk short-term buying aimed at flipping artworks |
| `AuctionCatalystEffect` | 0.90 | 6 | Single high-profile auction event that revalues an artist's market |
| `FlightToQualityConcentration` | 0.85 | 12 | Capital reallocation toward top-ranked artists during uncertainty |
| `TrophyBuyerDemand` | 0.85 | 4 | Demand from high-net-worth collectors for iconic status-signaling artworks |
| `InstitutionalValidationPremium` | 0.85 | 11 | Museum shows and biennials elevating artists' market value |
| `FreshToMarketPremium` | 0.85 | 2 | Valuation uplift for recently rediscovered or previously absent artworks |
| `AuctionConcentrationDynamics` | 0.80 | 2 | Small elite of artists and houses capturing disproportionate share |
| `ThirdPartyGuaranteesInAuctions` | 0.80 | 2 | Third party committing minimum price before auction to secure consignment |
| `AIEnabledCollectorOnboarding` | 0.75 | 3 | AI tools reducing barriers to art market entry for new collectors |
| `PostDigitalMaterialAuthenticityPremium` | 0.75 | 8 | AI saturation elevating value of physical, handmade, unique artworks |

### Evidence Corpus Results

After running induced ontology through old POE backend on 70 evidence records:

- Evidence records fed to POE: 30 of 70 (40 all-neutral, dropped)
- Domain: poea-induced-v1
- Candidates: 10 (1 seed + 9 variants)
- Dominant candidate: seed (log_score −21.01, evidence_count 30)
- Paradigm shift count: 0 (single batch, no shift)
- Observed true: 35 across 11 concepts
- Observed false: 3 across 11 concepts
- All-neutral records: 40/70

### Raw Proposal Summary

21 total proposals → 11 active after consolidation:
- Exact duplicates merged: 4
- Semantic merges: 6
- Rejected (low confidence): 2
- Suppressed (low evidence): 2

---

## Summary Comparison

| Dimension | Old Ontology | Induced Ontology |
|-----------|-------------|-----------------|
| Variable count | 25 | 11 |
| Designed by | Human expert | LLM from evidence |
| Hypotheses | 5 named seed candidates | 1 seed (co-occurrence based) |
| Evidence coverage | 100% (70/70 records assigned) | 43% (30/70 records with observations) |
| Total observed assignments | 224 (218 true + 6 false) | 38 (35 true + 3 false) |
| Variables never observed | 5 of 25 (20%) | 0 of 11 (0%) |
| Mean observations per active record | ~3.2 | ~1.3 |
| Dominant hypothesis after learning | H3/H4 (PrestigeFragmentation/BlueChip) | Seed (co-occurrence) |
| POE generation reached | 6 | 1 |
| Paradigm shifts | 1 | 0 |
