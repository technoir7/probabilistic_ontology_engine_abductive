# POE-A Snapshot

_Last updated: 2026-05-30_

---

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Bootstrap Repository | Complete |
| 1 | Evidence Loader | Complete |
| 2 | Abductive Concept Discovery MVP | Complete |
| 3 | Concept Registry MVP | Complete |
| 4 | Concept Consolidation | Complete |
| 5 | Active Concept Selection | Complete |
| 6 | Evidence Scoring (Assignment Bridge) | Complete |
| 7 | Backend Interface | Complete |
| 8 | Concept-to-Node Translation | Complete |
| 9 | POE Adapter | Complete |
| 10 | End-to-End Pipeline Command | **Complete** |
| 11 | Run Reports | **Complete** |
| 12 | Comparative Mode | Not Started |
| 13+ | Post-MVP phases | Not Started |

---

## Assignment Layer

POE-A now routes evidence through a deterministic assignment layer before using
semantic LLM scoring.

Implemented backends:

| Backend | Use case | LLM calls |
|---------|----------|----------:|
| `DirectStructuredAssignmentBackend` | evidence metadata already contains concept assignments | 0 |
| `DeterministicMapperBackend` | structured numeric/API/tabular evidence with a registered mapper, old POE mapper, or rule assignments | 0 |
| `SemanticLLMScorerBackend` | explicitly prose-heavy evidence requiring interpretation | yes |
| `HybridPrefilterScorerBackend` | mixed evidence; direct where possible, semantic fallback otherwise | conditional |

`AssignmentRouter` is deterministic. It routes from explicit
`assignment_mode`, `evidence_type`, and structured metadata. It does not use an
LLM to decide whether to call an LLM.

Default route is deterministic/direct assignment. Semantic LLM scoring is
opt-in via prose/unstructured evidence type. Art-market ingestion with
`--domain art` marks all article evidence as `prose_text`, routing to semantic
scoring. Evidence ingested with `--domain unknown` only gets `prose_text` when
body text is present; title-only records fall through to deterministic (which
errors if no mapper is found).

Old POE deterministic mapper reuse is implemented through
`OldPOEDomainMapperAdapter`, which lazily calls the sibling POE domain
`*Pipeline.build_evidence_record` methods and translates old POE
`EvidenceRecord` outputs into POE-A scored artifacts. Discovered old POE domains:
`macro-regime-v1`, `natural-gas-v1`, `ai-regime-v1`, `sovereign-debt-v1`,
`credit-cycle-v1`, `energy-regime-v1`, `labor-market-v1`, `crypto-regime-v1`,
`geopolitics-v1`, and `sf-urban-v1`.

If structured evidence lacks direct assignments and no deterministic mapper can
be found, POE-A emits an explicit routing/error record instead of calling the
LLM scorer.

---

## Semantic LLM Scoring Optimizations (2026-05-30)

### Prompt Compaction

Scoring prompt compacted by removing the redundant per-call response schema block.

| Metric | Before | After | Savings |
|--------|-------:|------:|--------:|
| System prompt | 1280 chars | 771 chars | 509 chars |
| Avg user message | 5442 chars | 4226 chars | 1216 chars |
| Tokens per call | ~1680 | ~1250 | ~430 |
| Tokens for 70 calls | ~117,626 | ~87,526 | ~30,100 |
| Input cost (70 calls) | ~$0.205 | ~$0.152 | ~$0.052 |

Output schema and JSON parsing are unchanged. Live-validated with compact prompt:
3 records scored correctly, all 11 assignments per record parsed without errors.

### Shadow Prefilter

`ShadowPrefilter` in `poea.assignments.prefilter` runs in read-only mode
alongside semantic scoring. Lexical keyword overlap between evidence text and
concept name/definition identifies pairs the LLM would likely score neutral.

Live validation (3-5 prose records):
- Would skip: 58-64% of semantic pairs
- False negatives: 0-1 (pairs it would skip that had actual true/false verdicts)
- Skipping is NOT yet enabled — prefilter is advisory only in shadow mode

Shadow analysis is exposed in `assignment_router.shadow_prefilter` in scored
evidence metadata and in run reports under "Routing And Cost Summary".

### Cost Reporting

`AssignmentRouter.score_all` now records in routing metadata:
- `fireworks_calls_made`: actual LLM calls made
- `fireworks_calls_avoided_by_deterministic`: records that skipped LLM via routing
- `fireworks_calls_avoided_by_cache`: records served from existing cache
- `shadow_prefilter`: full shadow analysis (pairs, skip rate, false negatives, savings)

Run reports include a "Routing And Cost Summary" section.

### Live Validation Results (2026-05-30)

| Metric | Value |
|--------|------:|
| Prose records scored (real Fireworks API) | 5 |
| Fireworks calls made | 5 |
| Structured records (no Fireworks) | 1 |
| Fireworks calls for structured | 0 |
| Compact prompt parse errors | 0 |
| Cache hits on immediate rerun | 6 |
| LLM calls on cache rerun | 0 |
| Shadow prefilter would-skip rate | 58–64% |
| Shadow prefilter false negatives | 0–1 |

---

## Posterior Inference (Old POE) — 2026-05-30

Old POE's `engine.query()` → `InferenceService` → pgmpy `VariableElimination` is
now called immediately after `engine.learn()` in `poe_backend.py`.

POE-A does not compute posterior probabilities. It passes target variable names
to `engine.query(InferenceQuery(aggregation=WEIGHTED_AVERAGE))` and embeds the
result in the graph artifact under `posterior_inference`.

The run report includes a "Posterior Inference (Old POE)" section that reads from
this artifact key and displays per-concept P(True)/P(False) alongside the dominant
direction (active/absent/uncertain).

Architecture boundary remains intact:
- POE-A: builds `InferenceQuery`, calls `engine.query()`, reads result
- Old POE: runs pgmpy VariableElimination over learned CPTs

No probabilistic computation exists in POE-A.

---

## Current Art Domain Registry

Induction run on art-market-domain evidence.

| Status | Count |
|--------|-------|
| active | 11 |
| suppressed | 2 |
| rejected | 2 |
| merged_into | 4 |

Active concepts (canonical):
- RegionalArtInfrastructureEmergence (conf 0.90, 3 evidence)
- SpeculativeDemandCollapse (conf 0.90, 4 evidence)
- AuctionCatalystEffect (conf 0.90, 6 evidence)
- FlightToQualityConcentration (conf 0.85, 12 evidence)
- TrophyBuyerDemand (conf 0.85, 4 evidence)
- InstitutionalValidationPremium (conf 0.85, 11 evidence)
- FreshToMarketPremium (conf 0.85, 2 evidence)
- AuctionConcentrationDynamics (conf 0.80, 2 evidence)
- ThirdPartyGuaranteesInAuctions (conf 0.80, 2 evidence)
- AIEnabledCollectorOnboarding (conf 0.75, 3 evidence)
- PostDigitalMaterialAuthenticityPremium (conf 0.75, 8 evidence)

Promotion thresholds: conf ≥ 0.75, evidence ≥ 2, cap 30.

---

## Artifacts

| File | Description |
|------|-------------|
| `artifacts/evidence.json` | 70 normalized evidence records (pre-annotations stripped) |
| `artifacts/raw_concepts.json` | 21 LLM-induced concept proposals (7 batches) |
| `artifacts/concept_registry.json` | Full registry with all statuses and promotion_events |
| `artifacts/canonical_concepts.json` | Active concepts only |
| `artifacts/nodes.json` | POE-compatible node objects (Phase 8 output; gitignored) |
| `artifacts/scored_evidence.json` | Concept assignments per evidence record (requires live API; gitignored) |
| `artifacts/poea_graph.json` | Graph artifact from last `poea pipeline --backend poe` run (gitignored) |
| `artifacts/run_report.md` | Phase 11 regenerated run report with scoring diagnostics, warnings, samples, backend summary, and artifact timestamps (gitignored) |

Latest Phase 10 POE pipeline run:

| Metric | Value |
|--------|------:|
| evidence records | 70 |
| raw concepts | 21 |
| active concepts | 11 |
| scored concept/evidence pairs | 770 |
| scoring errors | 0 |
| graph nodes | 11 |
| graph edges | 1 |
| records included in POE learning | 30 |
| records omitted from POE learning | 40 |
| neutral assignment rate | 95.1% |
| all-neutral scored records | 40 |

---

## Available CLI Commands

```
poea ingest                Load and normalize evidence records
poea induce                Induce candidate concepts (requires FIREWORKS_API_KEY)
poea consolidate           Build registry and select active concepts
poea registry promote      Re-apply promotion rules (threshold tuning)
poea score-evidence        Assign evidence against active concepts (deterministic/direct/semantic routing)
poea export-nodes          Export active concepts as POE-compatible node objects
poea run-backend           Run a structure-learning backend (--backend null|poe)
poea pipeline              Run the full evidence-to-graph pipeline
poea report                Regenerate run_report.md from existing artifacts
```

---

## Documented Architectural Divergences

### 1. JSON files instead of SQLite

**What the spec says:** Phases 3–5 use a SQLite registry with specific tables.

**What was implemented:** JSON file artifacts. Evidence scoring cached as `scored_evidence.json`.

**Why:** Consistent architecture — SQLite only for Phase 6 would create a dual-store system. JSON satisfies all documented exit criteria.

### 2. Fireworks AI instead of Anthropic SDK

**What the spec says:** `anthropic` SDK is the default LLM provider.

**What was implemented:** Fireworks AI (OpenAI-compatible endpoint), model `deepseek-v4-pro`.

**Why:** Provider decision made during Phase 2. LLM client is provider-agnostic via `LLMClient` protocol.

### 3. CLI command structure differs from spec

The spec uses SQLite-oriented `--db` flags. The implementation uses JSON-oriented `--concepts` and `--scored-evidence` flags. `registry init/import/list/diff` are not implemented (superseded by JSON workflow).

### 4. Phase 9 import path differs from plan

**What the plan documents:** `engine.engine`, `engine.schemas`, `engine.variable_identity`

**What the actual path is:** `src.engine.engine`, `src.engine.schemas`, `src.engine.variable_identity`

**Why:** The POE editable install (`pip install -e ../probabilistic_ontology_engine`) adds the repo root to sys.path rather than `src/`. The API is otherwise identical. The adapter uses lazy imports to surface missing-dependency errors clearly.

### 5. Phase 8 node format includes concept_id

Node format adds `concept_id` beyond the spec's documented fields for POE-A internal traceability. Harmless for POE (it derives its own UUIDs via `stable_variable_id`).

### 6. Assignment router added before comparative mode

The roadmap's next documented phase remains Phase 12, but the cost audit and
POE architecture review identified a missing assignment abstraction: LLM scoring
should not be the default for structured evidence. This change is an
architecture correction to Phase 6 rather than a new roadmap phase. It preserves
current art-market behavior through explicit prose metadata while reusing old
POE deterministic mappers for structured-domain runs.

---

## POE Dependency

Phase 9 requires:

```bash
pip install -e ../probabilistic_ontology_engine
```

POE version: 0.1.0
POE location: `../probabilistic_ontology_engine` (sibling repo)
POE imports used: `src.engine.engine`, `src.engine.schemas`, `src.engine.variable_identity`
Domain ID used: `poea-induced-v1` (configurable via `configs/induction_config.yaml`)

---

## Test Suite

```
329 passed, 1 skipped
```

Tests added:
- `tests/test_semantic_optimization.py` — 25 tests for prompt compaction, shadow prefilter, cache, routing metrics (added earlier)
- `tests/test_prefilter_eval.py` — 30 tests for shadow prefilter evaluator
- `tests/test_poe_adapter.py` — extended with 9 new posterior inference tests:
  - `test_graph_artifact_contains_posterior_inference_key`
  - `test_posterior_inference_present_with_evidence`
  - `test_posterior_inference_delegates_to_old_poe_engine`
  - `test_posterior_probabilities_sum_to_one`
  - `test_posterior_inference_variable_names_match_concepts`
  - `test_run_posterior_query_returns_empty_for_no_variables`
  - `test_build_graph_artifact_embeds_posterior_inference`
  - `test_poe_backend_score_hypotheses_includes_posterior_inference`
- `tests/test_reports.py` — extended with 10 new posterior inference report tests

25 new tests added in `tests/test_semantic_optimization.py` covering:
- Compact prompt output schema preservation
- Shadow prefilter shadow-mode behavior (no outputs changed)
- Cache preventing repeated LLM calls
- Routing/cost metrics determinism
- Structured evidence → deterministic (no LLM)
- Old POE mapper adapter used for structured domains
- Unknown structured → explicit error without LLM
- Art prose evidence → semantic routing

Latest verification also passed:

```bash
.venv/bin/python -m ruff check .
```

Result: all checks passed.
