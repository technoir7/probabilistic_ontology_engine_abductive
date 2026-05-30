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
opt-in via prose/unstructured evidence type. Current art-market ingestion marks
article evidence as `prose_text`, preserving Phase 6 behavior and existing
`scored_evidence.json` compatibility.

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
256 passed, 1 skipped
```

Latest verification also passed:

```bash
.venv/bin/python -m ruff check .
```

Result: all checks passed.
