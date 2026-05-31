# Cost Review

_Date: 2026-05-30_
_Scope: Identify duplicate scoring, unnecessary calls, cache misses, redundant LLM calls_

---

## Current Cost Baseline

From COST_AUDIT.md (post-prompt-compaction, post-deterministic-routing):

| Stage | Fireworks calls | Approx input tokens | Approx output tokens | Estimated cost |
|-------|----------------:|--------------------:|---------------------:|---------------:|
| Concept induction | 7 | 8,910 | 2,911 | $0.0256 |
| Evidence scoring (art prose) | 70 | ~87,526 | ~13,396 | ~$0.199 |
| Structure learning (old POE) | 0 | 0 | 0 | $0.000 |
| Posterior inference (engine.query) | 0 | 0 | 0 | $0.000 |
| Structure diagnostics (pure fn) | 0 | 0 | 0 | $0.000 |
| Entropy diagnostics (pure fn) | 0 | 0 | 0 | $0.000 |
| **Total per full run** | **77** | **~96,436** | **~16,307** | **~$0.225** |

New diagnostic calls (`build_structure_diagnostics`, `build_entropy_diagnostics`,
`engine.query`) are all local CPU computation. They add no Fireworks cost.

---

## Finding 1: No Duplicate Scoring Identified

**Expected concern:** POE-A might score evidence twice — once for assignment and once
for the backend.

**Finding:** Not the case. Evidence is scored exactly once:
1. `score-evidence` runs LLM scoring (70 calls for art prose, 0 for structured)
2. The resulting `scored_evidence.json` is passed to `poe_backend.learn_graph()`
3. `learn_graph()` translates `ScoredRecord` → `EvidenceRecord` and passes them to
   `engine.learn()` with no additional LLM call

The scoring artifact is a cache — if it exists, the pipeline skips the 70-call scoring
stage on rerun.

---

## Finding 2: Cache Is Working Correctly

**Current behavior:**
- `scored_evidence.json` serves as a record-level cache
- If ALL active concepts are covered by an existing record, it is reused without LLM call
- `poea pipeline` skips intermediate artifacts unless `--force` is passed
- Structure diagnostics and entropy diagnostics are CPU-only, not cached (fast enough)

**Cache miss scenario:** Adding a new concept triggers full re-scoring of all records
(record-level cache invalidation). Pair-level cache would prevent this. Documented in
COST_AUDIT.md as medium-priority optimization but not blocking.

---

## Finding 3: Concept Induction Could Be Cheaper With Reuse

**Current behavior:** Every `poea pipeline` call re-induces concepts from scratch
(7 Fireworks calls, ~$0.026) unless `raw_concepts.json` already exists.

**Finding:** Induction is already protected by artifact reuse. If `raw_concepts.json`
exists, it is skipped. The $0.026 is only paid on first run or after `--force`.

**Remaining issue:** Induction has no per-batch content-addressed cache. If the
evidence corpus changes partially, all 7 batches run again. For large corpora this
could be improved, but at 70 records it is not the dominant cost.

---

## Finding 4: Structured Domain Scoring Correctly Avoids Fireworks

**Verified:** All 10 old POE structured domains route to `DeterministicMapperBackend`
with 0 Fireworks calls. Art prose routes to `SemanticLLMScorerBackend`.

No unnecessary LLM calls for structured evidence.

---

## Finding 5: Shadow Prefilter Is Observation-Only (No Cost Impact)

The `ShadowPrefilter` runs in shadow mode. It performs lexical keyword overlap
computation (CPU-only) and records what it would skip. It does not reduce actual
Fireworks calls.

As documented in SHADOW_PREFILTER_EVALUATION.md, enabling skipping is not safe
until the prefilter is redesigned. No cost reduction here yet.

**Potential if redesigned:** Shadow prefilter analysis suggests 58-64% of semantic
pairs could be skipped. With a redesigned prefilter achieving ≥95% recall, this
could save ~$0.10-0.14 per 70-record run. That redesign is not in scope here.

---

## Finding 6: All-Neutral Records Still Consume Fireworks Budget

40 of 70 art evidence records produce all-neutral assignments (no true/false values).
These records are scored but contribute nothing to POE learning (skipped by
`_translate_scored_evidence` which drops MISSING records).

**Current cost impact:** 40/70 = 57.1% of scoring calls produce no POE-usable output.

**This is documented but not actionable now:** The shadow prefilter evaluation
established that no safe pair-level skipping is currently possible. Record-level
skipping at any non-trivial threshold creates unacceptable false negatives (>13%
FN rate at threshold=0.01).

**Not a new finding.** COST_AUDIT.md identified this as the top optimization
opportunity. No change recommended here.

---

## Finding 7: Posterior Inference Adds No Cost

`engine.query(InferenceQuery(...))` runs `InferenceService.query()` →
pgmpy `VariableElimination`. This is:
- Purely local CPU computation
- No network calls
- No Fireworks API calls
- Typically < 100ms for 11 variables

The new structure diagnostics (`build_structure_diagnostics`) and entropy diagnostics
(`build_entropy_diagnostics`) are similarly zero-cost pure functions.

---

## Summary: No Action Items

| Finding | Status | Cost impact | Action |
|---------|--------|------------|--------|
| Duplicate scoring | None found | - | None |
| Cache miss on concept addition | Documented | Medium (future) | No change now |
| Induction reuse | Working | Protects $0.026 | None |
| Structured domain routing | Correct | Saves all structured costs | None |
| Shadow prefilter | Shadow only | No savings yet | No change (unsafe) |
| All-neutral records | Known, blocked | 57% of scoring cost | Blocked by prefilter safety |
| New diagnostic calls | CPU-only | Zero | None needed |

**Net cost change from this session:** $0.000 per run.

All new capabilities (structure diagnostics, entropy diagnostics, posterior inference)
are CPU-local computations. No new Fireworks calls were added.

---

## Cost Optimization Roadmap (Not Implemented Here)

In priority order for future sessions:

1. **Redesign shadow prefilter** (~$0.10-0.14/run savings)
   — Record-level neutral-rate accumulator over prior runs is the safest approach
   — Requires scoring history artifact
   
2. **Pair-level cache** (~$0 on first run, saves on concept-set changes)
   — Cache by (evidence_id, concept_id) pairs
   — Reuse previous score when concept unchanged, re-score only new concepts
   
3. **Induction cadence control** (~$0.026/run savings)
   — Hash-based evidence change detection: skip induction if corpus unchanged
   — Already partially protected by artifact reuse

4. **Cheaper scoring model** (needs calibration, not recommended yet)
   — Could save 40-80% of scoring cost
   — Would require recall validation against existing scored baseline
