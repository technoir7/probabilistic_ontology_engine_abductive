# POE-A Cost Optimization Audit

_Updated: 2026-05-30 — reflects deterministic routing correction and prompt compaction_

## Scope

This audit tracks POE-A LLM costs across two states:
- **Baseline**: before deterministic routing correction (all 70 art records scored by LLM)
- **Current**: after routing correction + prompt compaction (only explicit prose scores LLM, prompt is 26% smaller)

---

## Current State After Optimizations

### Routing Correction Impact

After the deterministic routing correction and re-ingestion of art evidence with
`--domain art`:

| Evidence type | Records | LLM calls | Cost |
|---------------|--------:|----------:|-----:|
| Art prose (prose_text) | 70 | 70 | ~$0.199 (after compaction) |
| Old POE structured domains (deterministic) | any | 0 | $0.000 |
| Direct structured assignments | any | 0 | $0.000 |
| Unknown structured (no mapper) | any | 0 | $0.000 (errors loudly) |

Key finding: the stored `artifacts/evidence.json` was previously ingested with
`--domain unknown` (no `evidence_type` metadata). With the deterministic router,
this caused all 70 art records to route to deterministic, which errored on all 70
(no mapper for domain `unknown`). **This was a stale artifact bug, not a code
bug.** Re-ingesting with `--domain art` correctly marks all art evidence as
`prose_text` and routes it to semantic scoring.

### Prompt Compaction Impact

| Metric | Before | After | Savings |
|--------|-------:|------:|--------:|
| System prompt chars | 1,280 | 771 | 509 |
| Avg user message chars | 5,442 | 4,226 | 1,216 |
| Tokens per scoring call | ~1,680 | ~1,250 | ~430 |
| Input tokens for 70 calls | ~117,626 | ~87,526 | ~30,100 |
| Input cost for 70 calls | ~$0.205 | ~$0.152 | ~$0.052 |

The compaction removed the per-call response schema block (~297 tokens) and
shortened the system prompt (~133 tokens) while preserving all output schema
compatibility.

### Shadow Prefilter Potential

Shadow prefilter analysis (live validation, 3-5 prose records):
- Would skip 58-64% of semantic pairs by lexical prefiltering
- False negative rate: 0-1 per 3-5 records (requires broader validation)
- Estimated savings if enabled for 70 records: ~$0.10-0.14
- Status: shadow mode only (advisory) — actual skipping not yet enabled

---

Baseline (before deterministic routing correction and prompt compaction):

| Metric | Value |
| --- | ---: |
| evidence records | 70 |
| raw concepts | 21 |
| active concepts | 11 |
| concept/evidence score pairs | 770 |
| scoring errors | 0 |
| graph nodes | 11 |
| graph edges | 1 |
| scored records included in POE learning | 30 |
| scored records omitted from POE learning | 40 |
| neutral assignment rate | 95.1% |

Pricing assumption: Fireworks model page for
`accounts/fireworks/models/deepseek-v4-pro` lists input at `$1.74 / 1M tokens`,
cached input at `$0.14 / 1M tokens`, and output at `$3.48 / 1M tokens`.
Token counts below are approximate, estimated from actual current prompts and
artifacts using the common `characters / 4` rule. Source:
https://fireworks.ai/models/deepseek-ai/deepseek-v4-pro

## 1. Estimated Fireworks/API Cost By Phase

| Phase | Fireworks calls | Approx input tokens | Approx output tokens | Estimated API cost | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| evidence ingestion | 0 | 0 billed | 0 billed | `$0.0000` | Local JSON load/normalization only. |
| concept induction | 7 | 8,910 | 2,911 | `$0.0256` | 70 evidence records batched 10 per call. |
| concept consolidation | 0 | 0 billed | 0 billed | `$0.0000` | Local JSON consolidation and YAML map. |
| active concept selection | 0 | 0 billed | 0 billed | `$0.0000` | Local threshold/promotion logic. |
| evidence scoring | 70 | 117,626 | 13,396 | `$0.2512` | One LLM call per evidence record, all 11 active concepts per call. |
| POE adapter | 0 | 0 billed | 0 billed | `$0.0000` | Local POE structure learning, no Fireworks calls. |
| pipeline orchestration | 0 direct | 0 direct | 0 direct | `$0.0000` direct | Orchestrates the above stages. |
| **Total latest uncached LLM work** | **77** | **126,536** | **16,307** | **`$0.2768`** | Scoring is about 90.7% of direct API cost. |

The absolute dollar amount is small for this run, but the cost structure is
important because scoring scales as:

```text
O(evidence_records * active_concepts * concept_definition_prompt_size)
```

The scoring prompt repeats all active concept names and definitions for every
evidence record.

## 2. Approximate Token Consumption Per Phase

| Phase | Approx billed tokens | Approx local artifact volume | Cost driver |
| --- | ---: | ---: | --- |
| evidence ingestion | 0 | `artifacts/evidence.json` is 36,241 bytes, roughly 9k local tokens | No API cost; affects downstream prompt size. |
| concept induction | 11,821 | `artifacts/raw_concepts.json` is 26,961 bytes, roughly 6.7k local tokens | Evidence text included once across 7 batches. |
| concept consolidation | 0 billed | registry artifact is 20,943 bytes, roughly 5.2k local tokens | No LLM call. |
| active concept selection | 0 billed | canonical concepts artifact is 8,752 bytes, roughly 2.2k local tokens | No LLM call. |
| evidence scoring | 131,022 | scored evidence artifact is 179,433 bytes, roughly 44.9k local tokens | Dominated by repeated concept block plus 70 records. |
| POE adapter | 0 billed | graph artifact is 4,860 bytes, roughly 1.2k local tokens | No LLM call. |
| pipeline orchestration | 0 billed | report artifact is 7,937 bytes, roughly 2.0k local tokens | No LLM call. |

Detailed LLM token estimates:

| Stage | Requests | Input tokens | Output tokens | Total tokens |
| --- | ---: | ---: | ---: | ---: |
| induction | 7 | 8,910 | 2,911 | 11,821 |
| scoring | 70 | 117,626 | 13,396 | 131,022 |

Scoring consumes about 11.1x the tokens of induction in the current run.

## 3. Current Cache Effectiveness

| Cache / Reuse Layer | Current status | Observed effectiveness |
| --- | --- | --- |
| induction cache hits | No per-batch induction cache metric exists. Pipeline reuses `artifacts/raw_concepts.json` when present and `--force` is not used. | Latest regenerated report did not run induction. A normal rerun with artifacts present avoids 100% of induction API calls, but there is no granular cache-hit accounting. |
| scoring cache hits | `artifacts/scored_evidence.json` summary reports `cache_hits: 0`, `scored: 70`. | The latest scoring artifact was produced from live scoring rather than record-level cache hits. Pipeline-level artifact reuse can skip the whole scoring stage on rerun. |
| reusable artifacts | `evidence.json`, `raw_concepts.json`, `concept_registry.json`, `canonical_concepts.json`, `scored_evidence.json`, `nodes.json`, `poea_graph.json`, `run_report.md`. | High pipeline-level reuse. Low incremental granularity for induction; scoring cache is record-level but not pair-level. |

Important cache behavior:

- `poea pipeline` reuses intermediate artifacts unless `--force` is passed.
- `score-evidence` can reuse a scored record only when that record already has
  a superset of the current active concept IDs.
- If active concepts change partially, the current scoring cache re-scores the
  whole evidence record rather than only missing `(evidence_id, concept_id)`
  pairs.
- Induction has artifact reuse but no content-addressed per-batch cache.

## 4. Neutral-Rate Analysis

### Overall Neutral Rate

| Assignment type | Count | Rate |
| --- | ---: | ---: |
| true | 35 | 4.5% |
| false | 3 | 0.4% |
| neutral / missing | 732 | 95.1% |
| total pairs | 770 | 100.0% |

`SOFT_OBSERVED` count is 0. All non-neutral assignments are hard `OBSERVED`.

### Concepts Causing Most Neutral Outcomes

| Concept | True | False | Neutral | Neutral rate |
| --- | ---: | ---: | ---: | ---: |
| FreshToMarketPremium | 1 | 0 | 69 | 98.6% |
| ThirdPartyGuaranteesInAuctions | 1 | 0 | 69 | 98.6% |
| AIEnabledCollectorOnboarding | 1 | 0 | 69 | 98.6% |
| PostDigitalMaterialAuthenticityPremium | 1 | 0 | 69 | 98.6% |
| AuctionCatalystEffect | 2 | 0 | 68 | 97.1% |
| RegionalArtInfrastructureEmergence | 3 | 0 | 67 | 95.7% |
| FlightToQualityConcentration | 4 | 0 | 66 | 94.3% |
| AuctionConcentrationDynamics | 3 | 1 | 66 | 94.3% |
| TrophyBuyerDemand | 5 | 0 | 65 | 92.9% |
| SpeculativeDemandCollapse | 5 | 2 | 63 | 90.0% |
| InstitutionalValidationPremium | 9 | 0 | 61 | 87.1% |

The concepts with the weakest observed support are:

- `FreshToMarketPremium`
- `ThirdPartyGuaranteesInAuctions`
- `AIEnabledCollectorOnboarding`
- `PostDigitalMaterialAuthenticityPremium`

Each has only one true/false observed assignment out of 70 evidence records.

### Evidence Records With All-Neutral Assignments

40 of 70 scored records are all-neutral. These records produced zero scoreable
assignments for POE learning:

| Evidence ID | Title |
| --- | --- |
| `dd355ccee678f0b5` | The Art Basel and UBS Art Market Report 2026 |
| `2ccdad8b8306e11c` | Foreword by Thierry Ehrmann |
| `57e77a22f8832c4d` | A Breath of Fresh Air from the Major Collections |
| `fc361611ff2de97c` | The Discreet Market for NFTs and Generative Art |
| `ca576f8ef22895dc` | Prints Stimulating the Art Market |
| `23e560a35f25504d` | France: A Champion of Sales Moving Upmarket |
| `06183c6949c1fb47` | Vietnamese Artists: A Dazzling Year in France |
| `1c0475ae17ce3088` | Female Artists: Analysis of New Records |
| `e19c65a64f0e3161` | Hiscox Artist Top 100 2025 Introduction |
| `0697d7917ab4b40b` | Number of artists at auction reaches a record high |
| `e23b207c6afffe59` | Highest market share as record volume of lots coming to auction |
| `6cbb5d378c6e1226` | New York and London increase their market share |
| `3d5a505dccadd4f8` | Confidence may be returning - but for how long? |
| `5ef674cc7f1bb886` | Asian demand takes a hit |
| `429a0115d8a2b5e3` | More women in this year’s HAT 100 |
| `d88799c640f6c6cc` | Non-Western art market presence |
| `6898a9ac6a3f2bb4` | Artist profile: François-Xavier and Claude Lalanne |
| `4549f654fcce3636` | Hiscox Artist Top 100 Rankings |
| `9b8731a06c066716` | Top 25 prices paid at auction for artworks made after 2000 (2019-2024) |
| `127489693e8d9ca4` | Top 25 prices paid at auction for artworks made after 2000 (2024) |
| `9c0275e0716537bf` | Christie’s Posts ‘Rock Solid’ Contemporary Sale, Led by Marian Goodman’s Gerhard Richters |
| `034c8bed965532a8` | Gala Season! Shaggy and Jewel Hit the Whitney, Henry Taylor and Pharrell Toast Gordon Parks, and More Juicy Art-World Gossip |
| `beadd19d95147fcc` | Lalanne’s Playful Frog Fountains Surface at Auction |
| `05ec6cd8def1f72a` | Robert Mnuchin’s Storied Art Gallery Townhouse Lists for $35 Million |
| `6461c5b9005711bc` | The New York Fairs Are Done. What Remains? |
| `7d86bea9dcbad88d` | U.K. Arts Center Lands Seismic $122.4M Gift-and More Art Industry News |
| `c25d5db68737d6e4` | Sotheby’s Buoyant $303.4 Million Modern Art Evening Sale: By the Numbers |
| `2a5b3d90b3668c80` | Three Dinosaur Fossils Are Up for Grabs at This New York Art Gallery |
| `050415c995aeaede` | Tracey Emin, Katharina Grosse, and More Rally to Raise $2.7 Million for South London Gallery |
| `c04f9d2830a56c47` | Who Won New York’s $2.5 Billion Auction Week? |
| `52990e25e59d2886` | The Art Basel & UBS Art Market Report 2026 By Arts Economics |
| `063e695beef6a9a5` | Is A Random Unknown Artist More Valuable Than Picasso? AI Thinks So. |
| `f8fdc50bde7d2121` | Five Questions for Five Art Advisors on the May 2026 Marquee Sales |
| `195ebcd1fa784298` | New on View |
| `94c095369ef873ad` | SFMOMA Announces 2026 Exhibitions, Including Transformed Fisher Collection Galleries, Matisse’s Femme au chapeau, and RM x SFMOMA |
| `e43eac72d27663e7` | Exclusive SFMOMA Presentation of Matisse's Femme au chapeau: A Modern Scandal Explores the Spectacular Debut and Enduring Impact of Matisse's Iconic Painting |
| `2aeb34951e43644f` | SFMOMA to Unveil Complete Transformation of the Renowned Doris and Donald Fisher Collection in April 2026 |
| `7a43425e43220e0c` | Last Call to Join SFMOMA’s Museumwide Art Bash Party on April 29 |
| `35a0294d8ffbf218` | Global Debut of RM x SFMOMA Exhibition Opens to the Public on October 3, 2026 |
| `1e197f01c0cac25e` | SFMOMA to Open Graciela Iturbide: Between Two Worlds, a Major Retrospective |

### Estimate Of Unnecessary Scoring Work

If a pre-scoring filter had perfectly identified the 40 all-neutral records:

| Avoidable component | Estimate |
| --- | ---: |
| avoidable scorer calls | 40 / 70 = 57.1% |
| avoidable concept/evidence pairs | 440 / 770 = 57.1% |
| avoidable input tokens | about 67,162 |
| avoidable output tokens | about 7,620 |
| avoidable scoring cost | about `$0.1434` |
| avoidable total latest-run LLM cost | about 51.8% |

This is an upper bound for all-neutral record filtering. Additional savings are
possible by filtering sparse concept/evidence pairs within the remaining 30
non-neutral records, but that has higher quality risk.

## 5. Optimization Opportunities Ranked By Expected Savings

| Rank | Opportunity | Expected cost reduction | Implementation complexity | Risk to quality | Rationale |
| ---: | --- | ---: | --- | --- | --- |
| 1 | Sparse concept filtering before scoring | 40-70% of scoring cost; 36-63% of total LLM cost | Medium | Medium | Current scoring evaluates every active concept against every record. A local prefilter could skip obviously irrelevant evidence/concept pairs or all-neutral records before invoking the scorer. |
| 2 | Cheaper scoring model | 40-80% of scoring cost depending on model | Low-Medium | Medium-High | Scoring is classification-like and may tolerate a cheaper model, but false negatives/false positives directly alter POE learning evidence. Needs calibration. |
| 3 | Pair-level scoring cache | 10-60% on iterative runs with concept-set changes | Medium | Low | Current cache is record-level. If active concepts change, partial cache misses can cause full-record rescoring. Pair-level cache preserves prior assignments. |
| 4 | Concept coverage triggers | 20-50% of scoring cost | Medium | Medium | Suppress or defer scoring for concepts with weak observed support after an initial coverage pass. This targets concepts with 98.6% neutral rates. Risk: rare but important concepts may be underlearned. |
| 5 | Induction cadence changes | 5-15% of total current cost; larger on repeated corpus updates | Low | Medium | Induction is only about 9.3% of current API cost. Running induction less often helps less than scoring optimization unless the corpus changes frequently. |
| 6 | Batch sizing changes for induction | 1-5% of total current cost | Low | Low-Medium | Induction has only 7 calls. Larger batches may reduce repeated system/schema overhead but may reduce concept quality or increase truncation risk. |
| 7 | Prompt compaction for scoring | 10-25% of scoring input cost | Low-Medium | Low-Medium | Concept definitions are repeated 70 times. Shorter concept summaries or IDs could reduce input tokens while keeping the same model and scoring behavior. |
| 8 | Fireworks cached-input / prompt-prefix exploitation | 5-20% of scoring cost if provider caching applies reliably | Medium | Low | The concept block is highly repetitive. Reordering prompts to maximize stable prefix reuse may qualify for cached-input pricing, but provider-side behavior needs verification. |
| 9 | Pipeline artifact reuse guardrails | Near 100% for accidental reruns | Low | Low | Existing artifact reuse already helps. Add clearer dry-run/cost preview and stricter warnings before `--force` live reruns. Does not reduce first-run cost. |

## 6. Completed Optimizations And Remaining Recommendations

### Completed (2026-05-30)

**Prompt compaction** — implemented:
- System prompt: 1280 → 771 chars (−509)
- User message schema block removed: saved ~297 tokens/call
- Total: ~430 tokens saved/call → ~30,100 tokens / 70 calls → ~$0.052 savings
- Live validated: compact prompt parses correctly, no schema errors

**Shadow prefilter** — implemented in shadow mode:
- `ShadowPrefilter` in `poea.assignments.prefilter`
- Reports would-be-skipped pairs without actually skipping
- Live validation: 58-64% skip rate, 0-1 false negatives per 3-5 records
- Shadow analysis in routing metadata and run reports

**Cost reporting** — implemented:
- `fireworks_calls_made`, `fireworks_calls_avoided_by_deterministic`,
  `fireworks_calls_avoided_by_cache` in routing metadata
- "Routing And Cost Summary" section in run reports

### Remaining: Enable Shadow Prefilter Skipping

After broader validation confirms low false-negative rate:

1. Run shadow prefilter on all 70 records with actual scored outputs to measure
   overall false-negative rate against the 38 observed true/false assignments.
2. If false-negative rate < 5%, enable actual pair skipping in the router.
3. Expected additional savings: ~58-64% of scoring pairs → ~$0.10-0.14 per run.

Do not implement a cheaper scoring model without quality validation against
existing scored evidence baselines. Model switching changes epistemic behavior
of the assignment bridge.
