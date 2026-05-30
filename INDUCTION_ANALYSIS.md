# Induction Analysis

## Execution Summary

Phase 2 robustness changes were applied only:

- Default induction batch size reduced from 20 to 10.
- Prompt now strongly requires compact valid JSON only, with no markdown, prose, code fences, trailing commentary, or incomplete objects.
- Prompt now exposes `evidence_id` directly and requires exact raw evidence IDs.
- Parser now accepts both raw IDs and `EVIDENCE-<id>` citation strings, normalizing both to raw IDs.
- Invalid or truncated JSON now becomes an explicit batch parse error instead of a silent zero-concept success.
- Debug responses are preserved on successful batches and on final parse failure.

No registry, consolidation, scoring, POE adapter, or latent validation was implemented.

## Test Results

Command:

```bash
.venv/bin/python -m pytest
```

Result:

- 66 passed
- 1 skipped

## Live Run

Commands:

```bash
poea ingest --input ../art-market-domain/data/manual_ingest_split --output artifacts/evidence.json
poea induce --evidence artifacts/evidence.json --output artifacts/raw_concepts.json --verbose --debug-responses
```

Run facts:

- Evidence records: 70
- Title-only evidence records: 21
- Model: `accounts/fireworks/models/deepseek-v4-pro`
- Batch size: 10
- Final batch count: 7
- Final parsed concept count: 21
- Final batch errors: 0

Saved artifacts:

- `artifacts/raw_concepts.json`
- `artifacts/raw_debug_responses.json`
- `artifacts/raw_debug_responses/batch_0.txt` through `batch_6.txt`

## Parse Success Rate

Final batch parse success rate: 7/7 batches, 100%.

Observed provider-response parse behavior during the run:

- 10 HTTP 200 responses were observed.
- 7 responses became final parsed batch outputs.
- 3 intermediate responses failed JSON parsing and were retried.
- Batch 4 required two retries before success.
- Batch 5 required one retry before success.

The final artifact has no batch-level errors, but the model still occasionally emits incomplete JSON. The retry behavior now catches and recovers from that failure mode instead of hiding it.

## Total Concepts

21 concepts were parsed.

## Concepts Per Batch

| Batch | Evidence Records | Parsed Concepts | Final Status |
| --- | ---: | ---: | --- |
| 0 | 10 | 5 | Parsed |
| 1 | 10 | 4 | Parsed |
| 2 | 10 | 2 | Parsed |
| 3 | 10 | 3 | Parsed |
| 4 | 10 | 3 | Parsed after retries |
| 5 | 10 | 2 | Parsed after retry |
| 6 | 10 | 2 | Parsed |

## Missing Citation Rate

Missing citation rate: 0/21 concepts, 0%.

All retained citations are valid evidence IDs from `artifacts/evidence.json`. No parsed concept has an empty `supporting_evidence_ids` list.

The previous `EVIDENCE-<id>` citation-loss issue was corrected by normalization. The final saved raw responses used raw IDs, but the parser now accepts either form.

## Confidence Distribution

| Confidence Range | Count |
| --- | ---: |
| 0.00-0.25 | 0 |
| 0.26-0.50 | 0 |
| 0.51-0.75 | 9 |
| 0.76-1.00 | 12 |

Exact confidence counts:

- 0.90: 3
- 0.85: 6
- 0.80: 3
- 0.75: 3
- 0.70: 5
- 0.60: 1

Confidence remains compressed toward the high end, but the run now includes one lower-confidence concept at 0.60.

## Duplicate Patterns

Exact duplicate names:

- `FlightToQualityConcentration`: 2 occurrences
- `InstitutionalValidationPremium`: 2 occurrences

Near-duplicate or overlapping families:

- Flight-to-quality family:
  - `FlightToQualityInArtMarket`
  - `FlightToQualityConcentration`
  - `FlightToQualityConcentration`
- Institutional-validation family:
  - `InstitutionalValidationEffect`
  - `InstitutionalExhibitionPremium`
  - `InstitutionalValidationPremium`
  - `InstitutionalValidationPremium`
- Market/prestige anchoring family:
  - `PrestigeMarketAnchoring`
  - `AuctionConcentrationDynamics`
  - `AuctionCatalystEffect`

These duplicate patterns are expected at raw induction time because cross-batch consolidation is intentionally not implemented in Phase 2.

## Output Quality Assessment

The run is materially better than the previous 20-record batch run:

- Final parse success improved from partial success to 100%.
- Missing citation rate improved from 50% to 0%.
- Parsed concept count increased from 8 to 21.
- Raw debug responses are available for every final batch.
- Invalid JSON is now treated as an error and retried.

Remaining Phase 2 limitations:

- The model still produced invalid JSON on 3 intermediate attempts.
- Intermediate failed responses are visible in terminal logs but are not saved when a later retry succeeds.
- Cross-batch duplicates remain present in raw output.
- Confidence values are still high-skewed.

## Phase 3 Readiness

Phase 3 is now safe to begin if it treats `artifacts/raw_concepts.json` as noisy raw induction output that requires consolidation and review.

It is not safe to treat the raw concepts as a final ontology. Exact duplicates and near-duplicates remain, and confidence values should not yet be interpreted as calibrated scores.

The Phase 2 induction path is now robust enough for Phase 3 work to start on downstream consolidation, registry decisions, scoring, adapter integration, and validation in their proper phase.
