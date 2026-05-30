# Induction Readiness Review

**Date:** 2026-05-30 (updated after provider migration)
**Scope:** Static analysis of Phases 0–2 implementation prior to first live API run
**Provider:** Fireworks AI (`accounts/fireworks/models/deepseek-v3`)
**Status:** No live API call has been made. All findings are based on code analysis and corpus inspection.

---

## Evidence ID Fix Summary

### Problem

Two SFMOMA records with identical titles produced the same `evidence_id` because the hash was computed from `source + title` only.

### Fix

`stable_evidence_id` now hashes `source + title + text` (all normalized: stripped, lowercased). The two colliding SFMOMA records have different `notes` fields and now produce different IDs.

### Verification

Seven new tests including `test_real_art_evidence_no_id_collisions`, which loads the actual corpus and asserts zero duplicate IDs. All pass.

---

## Provider Migration Summary

### What Changed

Anthropic was removed as the live induction provider. The project now uses Fireworks AI via an OpenAI-compatible REST endpoint.

| Item | Before | After |
|------|--------|-------|
| Required env var | `ANTHROPIC_API_KEY` | `FIREWORKS_API_KEY` |
| Default model | `claude-sonnet-4-6` | `accounts/fireworks/models/deepseek-v3` |
| SDK | `anthropic` | `openai` (pointed at Fireworks base URL) |
| Python dependency | `anthropic>=0.30` | `openai>=1.0` |

### Architecture

A `LLMClient` protocol was added in `src/poea/llm.py`:

```python
class LLMClient(Protocol):
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str: ...
```

`FireworksClient` implements this protocol using the OpenAI SDK's `chat.completions.create` against `https://api.fireworks.ai/inference/v1`. Any OpenAI-compatible endpoint can be swapped in by changing `base_url` and `api_key`.

The `ConceptInducer` accepts any `LLMClient` implementation, making it fully provider-agnostic in tests.

### Tests

All Anthropic-specific imports and fixtures removed. The mock now satisfies the `LLMClient` protocol directly:
```python
client.complete.return_value = json.dumps(sample_response)
```

Rate-limit retry behavior is tested using `openai.RateLimitError`. A live smoke test exists in `test_live_induction_smoke`, marked `@pytest.mark.live` and skipped unless `FIREWORKS_API_KEY` is present.

**Test results: 62 passed, 1 skipped (live test), 0 failed.**

---

## Is the Implementation Ready for a Live Run?

**Overall assessment: Mechanically ready. Epistemically uncertain.**

The pipeline will execute without errors once `FIREWORKS_API_KEY` is set. Whether the output is useful depends on model behavior that cannot be verified without running it.

What is confirmed working:
- Evidence loading, normalization, annotation stripping: tested on real corpus
- JSON extraction from LLM responses (plain, fenced, with preamble): tested with mocks
- Evidence ID restriction (filtering out hallucinated IDs): tested with mocks
- Schema validation of concept output: tested with mocks
- Rate-limit retry behavior: tested with mocks
- Provider abstraction: any `LLMClient` implementation accepted

What has NOT been tested against a real model:
- Whether `deepseek-v3` follows the "no domain labels" constraint
- Whether `deepseek-v3` returns valid JSON without preamble
- Whether it correctly references evidence IDs from the `[EVIDENCE-xxx]` tags
- Whether the output schema matches what was defined (model may add or omit fields)
- Confidence score distribution for this model
- Response latency and token usage

---

## Evidence Corpus Characterization

### Volume

| Metric | Value |
|--------|-------|
| Total records | 70 |
| With substantive text (title + notes) | 49 |
| Title-only (sparse) | 21 |
| Mean text length | 114 characters |
| Median text length | 104 characters |
| Max text length | 334 characters |

### Text Sparsity

The evidence is significantly thinner than the spec implies. Most `notes` fields are 1–2 sentence summaries. A representative example:

```
"Auction sales value decreased by 27% from 2022 peak, reaching $2.0 billion
across 5,400 auction sales in the first half of 2023."
```

This is an observation, not a mechanism. The LLM must infer causal structure from single-sentence market statistics.

### Batch Composition (default batch size: 20)

With `max_records: 20` the corpus splits into **4 batches**:

| Batch | Records | Sparse | Sources |
|-------|---------|--------|---------|
| 1 | 20 | 0 | art-basel (1), art_market_2025 (11), hiscox (8) |
| 2 | 20 | 3 | hiscox (17), huge_evidence (3) |
| 3 | 20 | 18 | huge_evidence (18), museum (2) |
| 4 | 10 | 0 | post_digital (1), sfmoma (9) |

Note: Batch 3 is 90% sparse (news headlines from `huge_evidence_27may26.json`). It will produce weaker concepts than the others.

The previous batch size of 40 was reduced to 20 in the config, producing 4 batches. More batches means the "recurring across batches" criterion is more meaningful — a concept must appear in at least 2 of 4 batches rather than both of 2.

---

## Model Assumptions

The implementation makes the following assumptions about `deepseek-v3` behavior, none of which have been empirically verified:

### 1. JSON Output Compliance

The prompt ends with `Return ONLY a JSON object with no preamble or explanation.` DeepSeek-V3 may still wrap output in prose or fences. The three-strategy `_extract_json` function handles this, but if the model returns a non-standard structure (e.g., `"result"` instead of `"concepts"`), the parse silently returns an empty list.

**Risk level:** Low. The extraction is robust.

### 2. Evidence ID Citation

The model must reference 16-char hex IDs from `[EVIDENCE-xxx]` tags. In practice:
- May ignore IDs and return empty `supporting_evidence_ids`
- May hallucinate IDs not present in the batch (filtered out by the implementation)
- May cite partially — only some concepts get IDs

The implementation handles all three cases safely. The practical consequence is that many concepts arrive with `supporting_evidence_ids: []`, which reduces the grounding signal for Phase 6 (evidence scoring).

**Risk level:** Medium. Will need to assess citation rate from first live run.

### 3. Confidence Calibration

LLMs typically cluster confidence scores in the 0.65–0.90 range regardless of evidence strength. The `min_confidence: 0.4` filter will likely pass virtually all concepts. The `promotion_confidence: 0.55` threshold may not discriminate meaningfully between better and worse concepts.

**Risk level:** Medium. Thresholds may need recalibration after first run.

### 4. Concept Count Per Batch

The prompt does not specify how many concepts to produce. Observed range for similar prompts: 5–20 per call. With a 4,096 token output limit and ~80 tokens per concept, the limit allows ~50 concepts. Unlikely to be hit.

### 5. Naming Convention

The prompt requests CamelCase names of 2–4 words. Models frequently violate this with:
- `snake_case` or `Title Case` or quoted `"phrase names"`
- Multi-word names over 4 words
- Abbreviations and domain-specific jargon

The schema does not enforce naming convention. Consolidation (Phase 4) must handle format normalization.

---

## Batching Strategy Analysis

### Current Configuration

```yaml
batching:
  max_records: 20
```

With 70 records → 4 batches of approximately 20 records each.

### Input Token Estimates

| Batch | Records | Input tokens (est.) |
|-------|---------|---------------------|
| 1 | 20 | ~1,600 |
| 2 | 20 | ~1,400 |
| 3 | 20 | ~800 (mostly sparse) |
| 4 | 10 | ~1,200 |
| System prompt | — | ~480 |

All batches are well within `deepseek-v3`'s context window. No concerns.

### Limitation: No Cross-Batch Context

Each batch is processed independently. The LLM in batch 2 does not see what concepts were proposed in batch 1. This means:
- The same underlying concept will likely appear in multiple batches under different names
- The "recurring across evidence" criterion must be assessed post-hoc during consolidation, not during induction

This is by design. The consolidation layer (Phase 4) is responsible for cross-batch deduplication.

---

## Expected Output Volume

Based on evidence density and typical LLM behavior:

| Scenario | Concepts per batch | Total raw concepts |
|----------|-------------------|-------------------|
| Conservative | 4–7 | 16–28 |
| Expected | 7–12 | 28–48 |
| Generous | 10–18 | 40–72 |

The art market domain has a well-defined conceptual space. Expect output toward the generous end, with significant cross-batch naming variation on the same underlying concepts.

---

## Expected Duplication Patterns

The art market evidence cluster around ~8–10 recurring themes. Expected naming variants:

| Underlying concept | Expected name variants |
|-------------------|----------------------|
| Price concentration in high-end tiers | PriceConcentration, BluechipConcentration, TierBifurcation, MarketPolarization |
| Auction guarantee mechanisms | AuctionGuarantee, IrrevocableBidEffect, GuaranteeMechanism, FloorPriceMechanism |
| Authenticity as a value driver | AuthenticityPremium, HumanOriginPremium, AIDiscount, ProvenancePremium |
| Institutional validation signal | MuseumValidation, InstitutionalPrestige, CriticalEndorsement, ExhibitionPremium |
| Macro uncertainty / collector caution | MarketUncertainty, CollectorCaution, RiskAversion, MacroHeadwinds |
| Fair and dealer cost pressure | DealerMarginCompression, FairFatigue, OperationalCostPressure |

Each cluster produces 2–4 naming variants across batches. Without consolidation, the registry for one run will contain 25–50 distinct names representing ~8–12 actual concepts.

---

## Ontology Explosion Risk

**Single run: LOW–MEDIUM. Multiple runs without consolidation: HIGH.**

### Single Run (70 records, 4 batches)

Expected raw output: 28–50 concepts. Expected underlying distinct concepts: 8–12. Name proliferation ratio: ~3–4×. The registry for a single run is manageable — consolidation reduces it to ~8–12 canonical concepts.

### Multiple Runs

Without cross-run consolidation, each run adds 28–50 new candidates. After 5 runs: 140–250 candidates with massive overlap. The consolidation pass must compare against the full existing registry, not only the current batch.

The implementation plan correctly specifies this requirement: "At the start of each induction pass, load existing registry concepts for cross-run deduplication." This must be enforced in Phase 4.

---

## Parts of the Implementation Untested by Live Run

| Component | What's Untested | Risk |
|-----------|----------------|------|
| `FireworksClient.complete()` | Real API round-trip, latency, token usage | None (infra) |
| `_parse_concepts()` | Real deepseek-v3 response format | Medium |
| Evidence ID citation rate | Whether model actually cites batch IDs | Medium |
| Confidence score distribution | Whether 0.4–0.55 thresholds are meaningful | High |
| Naming convention compliance | Whether CamelCase instruction is followed | Medium |
| Retry behavior | Whether 429s occur at this scale | Low |
| Batch 3 output | 90% sparse records — may produce few/no concepts | High |

---

## Recommended Next Steps

### To Enable Live Run

```bash
export FIREWORKS_API_KEY=your-key-here
poea ingest --input ../art-market-domain/data/manual_ingest_split --domain art --output artifacts/evidence.json
poea induce --evidence artifacts/evidence.json --output artifacts/raw_concepts.json --verbose
```

The live smoke test can also be run independently:
```bash
pytest -m live tests/test_concept_inducer.py::test_live_induction_smoke -v
```

### Before Phase 3 (Registry)

**Highest priority: run live induction first.** The registry schema and consolidation strategy depend on what the LLM actually produces — concept count, naming patterns, and confidence distribution. Designing Phase 3 without this data risks building a registry that doesn't fit the actual induction output.

Specific decisions that require live data:
1. **Confidence threshold calibration** — is 0.55 meaningful or do all concepts score above 0.7?
2. **Naming format** — does the model use CamelCase, or does consolidation need to normalize names first?
3. **Evidence ID citation rate** — if consistently empty, the `concept_evidence_links` table has less value
4. **Concept count** — does batch size 20 produce 5 or 20 concepts? This affects the registry's expected scale

### Other Recommendations

- Add `--debug-responses` flag to save raw LLM responses before parsing (essential for diagnosing JSON variation)
- Consider interleaving evidence across sources before batching to improve cross-batch recurrence signal
- Batch 3 (18/20 sparse records) may warrant a smaller or separate batch strategy for news headlines

---

## Current Test State

```
62 passed, 1 skipped (FIREWORKS_API_KEY not set), 0 failed
ruff: all checks passed
```
