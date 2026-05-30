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
| 8 | Concept-to-Node Translation | **Complete** |
| 9 | POE Adapter | Not Started |
| 10 | End-to-End Pipeline Command | Not Started |
| 11 | Run Reports | Not Started |
| 12 | Comparative Mode | Not Started |
| 13+ | Post-MVP phases | Not Started |

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
| `artifacts/scored_evidence.json` | Concept assignments per evidence record (requires live API run; gitignored) |
| `artifacts/poea_graph.json` | Graph artifact from last `poea run-backend` call (gitignored) |

---

## Available CLI Commands

```
poea ingest                Load and normalize evidence records
poea induce                Induce candidate concepts (requires FIREWORKS_API_KEY)
poea consolidate           Build registry and select active concepts
poea registry promote      Re-apply promotion rules (threshold tuning)
poea score-evidence        Score evidence against active concepts (requires FIREWORKS_API_KEY)
poea export-nodes          Export active concepts as POE-compatible node objects
poea run-backend           Run a structure-learning backend
```

Available backends: `null` (trivial graph, Phase 7). The `poe` backend is Phase 9.

---

## Documented Architectural Divergences

### 1. JSON files instead of SQLite

**What the spec says:** Phases 3–5 use a SQLite registry (`poea_registry.sqlite`) with tables `concepts`, `induction_runs`, `concept_evidence_links`, `concept_events`.

**What was implemented:** JSON file artifacts (`concept_registry.json`, `canonical_concepts.json`). The registry is rebuilt on each `consolidate` run from `raw_concepts.json`.

**Phase 6 decision:** Evidence scoring results are cached as `scored_evidence.json`. This satisfies the Phase 6 caching requirement without introducing SQLite.

**Why chosen over SQLite:** Introducing SQLite only for Phase 6 would create an inconsistent dual-store architecture. A full migration would require re-implementing Phases 3–5. The JSON approach satisfies all documented exit criteria.

**Future note:** Phase 9 (POE Adapter) requires careful integration — the adapter must call POE's `stable_variable_id(domain_id, concept_name)` for deterministic UUIDs and translate scored evidence assignments into POE `EvidenceRecord` objects.

### 2. Fireworks AI instead of Anthropic SDK

**What the spec says:** `anthropic` SDK is the default LLM provider.

**What was implemented:** Fireworks AI (OpenAI-compatible endpoint), model `deepseek-v4-pro`.

**Why:** Provider decision made during Phase 2. The LLM client is provider-agnostic via the `LLMClient` protocol.

### 3. CLI command structure differs from spec

**What the spec says:**
```
poea registry init --db ...
poea registry import --db ...
poea registry list --db ...
poea registry diff --db ...
poea registry promote --db ... --auto
poea score-evidence --db ... --evidence ...
poea export-nodes --db ... --output ...
poea run-backend --backend poe --db ... --evidence ...
```

**What was implemented:**
```
poea consolidate               (consolidation + promotion in one step)
poea registry promote          (standalone re-promotion, JSON-based)
poea score-evidence            (uses --concepts instead of --db)
poea export-nodes              (uses --concepts instead of --db)
poea run-backend               (uses --concepts and --scored-evidence instead of --db and --evidence)
```

`registry init`, `registry import`, `registry list`, and `registry diff` are not implemented. These are SQLite-oriented commands superseded by the JSON-file workflow.

### 4. Phase 8 node format includes concept_id

**What the spec says:** Node format: `name`, `definition`, `prior_probability`, `boolean_state`, `source`.

**What was implemented:** Node format adds `concept_id` for POE-A internal traceability.

**Why:** Phase 9's POE adapter derives its own UUIDs via `stable_variable_id(domain_id, concept_name)`, so the extra field does not conflict. It enables correlation between nodes and registry entries without re-parsing concept names.

---

## Test Suite

```
204 passed, 1 failed (pre-existing: openai module not installed), 1 skipped
```

Pre-existing failure: `test_inducer_retries_on_rate_limit` imports `openai` which is not in the active venv. Not a regression.
