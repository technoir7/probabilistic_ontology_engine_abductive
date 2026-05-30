# POE-A Implementation Sequence

**Version:** 1.0
**Date:** 2026-05-30

This document converts IMPLEMENTATION_PLAN.md into a sequenced build plan ordered by risk reduction, not architectural elegance.

The ordering differs from the original plan's phase numbering in two ways:
1. Evidence scoring is added as an explicit phase in the critical path (between active concept selection and the POE adapter).
2. Latent validation and stability phases are clearly post-MVP and not mixed into the critical path.

---

## Milestones

| Milestone | Description | Phases Required |
|-----------|-------------|-----------------|
| **M0: Skeleton** | Repo runs, tests pass, CLI exists | Phase 0 |
| **M1: Evidence Loaded** | Art text evidence normalized to EvidenceUnit format | Phase 1 |
| **M2: First Concepts** | LLM induces concepts from evidence (with null backend) | Phase 2 |
| **M3: Registry** | Concepts persist, lifecycle tracked | Phase 3 |
| **M4: Clean Concepts** | Deduplication works, concept count manageable | Phase 4 |
| **M5: Active Set** | System selects active concepts without human input | Phase 5 |
| **M6: Evidence Scored** | Each evidence record scored against active concepts | Phase 6 (new) |
| **M7: Null Pipeline** | Full pipeline runs end-to-end with null backend | Phase 7 |
| **MVP-0** | Full pipeline runs end-to-end with POE backend, zero hand-authored variables | Phase 8 |
| **M8: Reports** | Every run produces an auditable report | Phase 9 |
| **M9: Comparison** | POE-A graph compared against POE v1 | Phase 10 |
| **M10: Latent Validation** | Statistical grounding for concepts | Phase 11 |
| **M11: Stability** | Cross-run stability, autonomous operation | Phase 12 |

---

## Critical Path

```
Phase 0: Bootstrap
    ↓
Phase 1: Evidence Loader
    ↓
Phase 2: Concept Induction (null backend)
    ↓
Phase 3: Concept Registry
    ↓
Phase 4: Consolidation
    ↓
Phase 5: Active Selection
    ↓
Phase 6: Evidence Scoring   ← CRITICAL PATH ADDITION (not in original plan)
    ↓
Phase 7: Null Backend Pipeline (M7 smoke test)
    ↓
Phase 8: POE Adapter
    ↓
MVP-0: End-to-End Command
```

Everything after MVP-0 is post-MVP work and should not block the initial milestone.

---

## Phase 0: Bootstrap Repository

**Milestone:** M0
**Risk reduced:** None — establishes the build environment

**Tasks:**
1. `git init` in `probabilistic_ontology_engine_abductive/`
2. `uv init`, configure `pyproject.toml` with name `poea`
3. Add dependencies: `pydantic`, `typer`, `rich`, `sqlite-utils`, `anthropic`
4. Add dev dependencies: `pytest`, `ruff`, `mypy`
5. Create `src/poea/__init__.py` and `src/poea/cli.py` with a stub `poea` command
6. Configure pytest, ruff in `pyproject.toml`
7. Create `configs/induction_config.yaml` with MVP-minimal config

**Do not add yet:** LLM provider-specific dependencies beyond `anthropic`, `numpy`, `scikit-learn` (needed later for latent validation, not now), `openai`, `sentence-transformers`

**Exit criteria:**
```bash
pytest          # passes (no tests yet, but test discovery works)
ruff check .    # passes
poea --help     # shows CLI
```

**Notes:**
- Use `anthropic` as the default LLM provider, not `openai`. Fireworks API paths in the config should be treated as optional overrides. Update `configs/induction_config.yaml` to use `claude-sonnet-4-6` as the default model.
- No POE dependency yet.

---

## Phase 1: Evidence Loader

**Milestone:** M1
**Risk reduced:** Confirms the evidence format and normalizer work before investing in LLM calls

**Tasks:**
1. Implement `src/poea/evidence/schemas.py` — `EvidenceUnit` Pydantic model:
   ```
   evidence_id: str   (stable hash of source + title)
   source: str
   title: str
   published_at: str | None
   domain_tag: str
   text: str          (concatenated from title + notes + text content)
   metadata: dict
   ```
2. Implement `src/poea/evidence/loaders.py` — load from JSON file, JSON array, or directory
3. Implement `src/poea/evidence/normalizer.py`:
   - Extract `title`, `notes`, and text content
   - **Explicitly discard** `assignments` and `causal_claims` fields
   - Compute stable `evidence_id` from hash of (source, title)
4. CLI: `poea ingest --input <path> --domain art --output artifacts/evidence.json`
5. Tests: `test_evidence_loader.py`, `test_evidence_normalizer.py`
   - Test that `assignments` fields are stripped
   - Test stable ID generation
   - Test loading from directory and from single file

**Exit criteria:**
- At least 50 art evidence records load successfully from `manual_ingest_split/`
- Each record has a stable `evidence_id`
- No concept induction yet
- `assignments` fields absent from normalized output (verifiable in test)

**Known issue to address:** The art evidence files have a non-uniform structure. Some files are JSON arrays, some are single objects. The loader must handle both.

---

## Phase 2: Concept Induction

**Milestone:** M2
**Risk reduced:** Proves the central hypothesis — that LLM induction produces plausible concepts without a hand-authored vocabulary. This is the highest research risk and should be tested as early as possible.

**Tasks:**
1. Implement `src/poea/concepts/schemas.py` — MVP `Concept` Pydantic model:
   ```
   concept_id: str    (UUID)
   name: str
   definition: str
   confidence: float
   supporting_evidence_ids: list[str]
   ```
   Do not include `epistemic_role`, `direction`, `frequency` yet.

2. Implement `src/poea/concepts/prompts.py`:
   - `INDUCTION_PROMPT_TEMPLATE`: structured prompt for concept proposal
   - Prompt must instruct LLM to identify recurring, explanatory, causally relevant mechanisms
   - Prompt must explicitly prohibit returning pre-existing ontology variables
   - Prompt must produce JSON output matching the Concept schema
   - Include negative examples: "Do not propose 'ArtMarket' or 'GallerySales' — these are domain labels, not mechanisms"

3. Implement `src/poea/concepts/inducer.py`:
   - `induce_batch(evidence_batch, config) → list[Concept]`
   - Handle LLM response parsing and validation
   - Handle API errors with retry logic
   - Log token usage for cost tracking

4. CLI: `poea induce --evidence artifacts/evidence.json --output artifacts/raw_concepts.json`

5. Tests: `test_concept_inducer.py` (mocked LLM), `test_concept_schema.py`
   - Test schema validation
   - Test JSON parsing from mock LLM responses
   - Test error handling for malformed LLM output

**Exit criteria:**
- System produces plausible concepts from art evidence without receiving a prewritten vocabulary
- Run the live test manually: `pytest -m live -k test_induce_art_sample`
- Qualitative review: at least 5 of the top-confidence concepts are recognizable as art market mechanisms, not topic labels

---

## Phase 3: Concept Registry

**Milestone:** M3
**Risk reduced:** Establishes the durable artifact that makes the system auditable and incremental

**Tasks:**
1. Create `migrations/001_registry.sql`:
   ```sql
   CREATE TABLE concepts (
     concept_id TEXT PRIMARY KEY, name TEXT NOT NULL,
     definition TEXT NOT NULL, llm_confidence REAL,
     grounded INTEGER DEFAULT 0, status TEXT DEFAULT 'candidate',
     merged_into TEXT, induction_run_id TEXT,
     domain_tag TEXT, schema_version INTEGER DEFAULT 1,
     created_at TEXT DEFAULT CURRENT_TIMESTAMP, deprecated_at TEXT
   );
   CREATE TABLE concept_events (
     event_id TEXT PRIMARY KEY, concept_id TEXT,
     event_type TEXT, event_payload_json TEXT,
     created_at TEXT DEFAULT CURRENT_TIMESTAMP
   );
   ```
2. Create `migrations/002_induction_runs.sql`:
   ```sql
   CREATE TABLE induction_runs (
     induction_run_id TEXT PRIMARY KEY, domain_tag TEXT,
     input_artifact TEXT, model TEXT, config_json TEXT,
     created_at TEXT DEFAULT CURRENT_TIMESTAMP
   );
   ```
3. Create `migrations/003_evidence_links.sql`:
   ```sql
   CREATE TABLE concept_evidence_links (
     concept_id TEXT, evidence_id TEXT, support_strength REAL,
     PRIMARY KEY (concept_id, evidence_id)
   );
   ```
4. Implement `src/poea/registry/store.py`:
   - `init_db(db_path)` — runs migrations
   - `insert_concept(concept, induction_run_id, domain_tag)`
   - `get_concept(concept_id)`
   - `list_concepts(status=None, domain_tag=None)`
   - `update_status(concept_id, new_status, payload=None)` — records a `concept_event`
   - `link_evidence(concept_id, evidence_id, support_strength)`

5. Implement `src/poea/registry/diff.py`:
   - `diff_runs(db_path, run_id_1, run_id_2) → dict` — new, merged, deprecated concepts between two runs

6. CLI:
   ```bash
   poea registry init --db artifacts/poea_registry.sqlite
   poea registry import --db ... --concepts artifacts/raw_concepts.json
   poea registry list --db ...
   poea registry diff --db ...
   ```

7. Tests: `test_registry.py`

**Exit criteria:**
- Raw concepts import into registry
- Concepts persist across process restarts
- `registry list` shows concept count and statuses
- No concept is deleted by any operation

---

## Phase 4: Concept Consolidation

**Milestone:** M4
**Risk reduced:** Addresses risk T1 (concept explosion) and T3 (unstable names). If consolidation doesn't work, the registry grows without bound.

**Tasks:**
1. Implement `src/poea/concepts/consolidation.py`:
   - Pass 1: `exact_match(concepts) → list[MergeCandidate]` — normalize names (lowercase, strip punctuation, common suffixes), find exact matches
   - Pass 2: `llm_merge_pass(concepts, config) → list[MergeCandidate]` — for concepts not resolved by Pass 1, use LLM to compare definitions pairwise for semantic equivalence
   - `apply_merges(merge_candidates, registry)` — performs merges in registry, records `merged_into` events
   
2. Merge policy:
   - Winner: the concept with higher confidence or longer definition (more specific is better)
   - Loser: marked `merged_into = winner.concept_id`, status = `merged_into`
   - Evidence links: transferred to winner
   - Definition synthesis: for LLM-detected merges, synthesize a unified definition

3. CLI: `poea consolidate --db artifacts/poea_registry.sqlite`

4. Tests: `test_consolidation.py`
   - Test exact matching
   - Test merge recording in concept_events
   - Test evidence link transfer
   - Test that no concepts are deleted

**Exit criteria:**
- Obvious duplicates merge
- Merge history preserved in `concept_events`
- Concept count after consolidation is materially lower than before
- No silent deletion

**Performance note:** For 50-100 concepts, LLM comparison is feasible. For 500+ concepts, pairwise LLM comparison is O(N²) and too expensive. Limit LLM merge pass to concept pairs with normalized name Levenshtein distance below a threshold.

---

## Phase 5: Active Concept Selection

**Milestone:** M5
**Risk reduced:** Proves the system can select a working vocabulary without human input

**Tasks:**
1. Implement `src/poea/registry/lifecycle.py`:
   - `auto_promote(db_path, config) → list[promoted_concept_ids]`
   - Promotion criteria (from config):
     - `confidence >= min_confidence` (default 0.55)
     - `len(supporting_evidence_ids) >= min_supporting_evidence` (default 2)
     - `status == 'candidate'`
     - `merged_into IS NULL`
   - Every promotion writes a `concept_event` with the criteria that triggered it
   - Hard cap: if promotion would produce more than `max_active_concepts` (default 30) active concepts, only promote the top-ranked candidates

2. CLI: `poea registry promote --db ... --auto`

3. Tests: `test_lifecycle.py`

**Exit criteria:**
- Active concept set is produced without human input
- Promotion events are recorded
- Active concept count is bounded

---

## Phase 6: Evidence Scoring (New Phase — Critical Path)

**Milestone:** M6
**Risk reduced:** This is the critical missing step. Without it, Phase 8 (POE adapter) cannot produce valid evidence records.

**Tasks:**
1. Implement `src/poea/concepts/scorer.py`:
   - `score_evidence_record(evidence_unit, active_concepts, config) → list[ConceptAssignment]`
   - For each active concept, call LLM: "Given this concept's definition and this evidence text, does the evidence support this concept being True, False, or is it neutral? Answer in JSON."
   - Output per (evidence, concept) pair:
     ```json
     {
       "concept_id": "...",
       "evidence_id": "...",
       "assigned_value": true | false | null,
       "confidence": 0.0,
       "missingness": "OBSERVED | SOFT_OBSERVED | MISSING"
     }
     ```
   - Batch the scoring: score all concepts for one evidence record in a single LLM call to reduce API costs
   - Cache results: store in registry `concept_evidence_links` to avoid re-scoring on reruns

2. `build_poe_evidence_records(assignments) → list[dict]`:
   - Group assignments by evidence_id
   - For each evidence record, produce the POE `EvidenceRecord`-compatible structure:
     ```json
     {
       "evidence_id": "...",
       "assignments": [
         {"concept_id": "...", "variable_name": "...", "value": true, "confidence": 0.8}
       ]
     }
     ```

3. Tests: `test_scorer.py` (mocked LLM)
   - Test JSON parsing from mock responses
   - Test handling of neutral assignments
   - Test batching behavior
   - Test cache hit/miss behavior

**Exit criteria:**
- Every active concept receives an assignment for every evidence record
- Neutral assignments map to `MISSING` missingness type
- Scores are cached in the registry and not recomputed on re-run

**Cost concern:** For 50 evidence records and 20 active concepts, this phase may require 50-100 LLM calls (batching helps). Use the smallest capable model for scoring.

---

## Phase 7: Null Backend End-to-End

**Milestone:** M7
**Risk reduced:** Validates the full pipeline integration without the complexity of the POE adapter

**Tasks:**
1. Implement `src/poea/backends/interface.py` — `StructureLearningBackend` protocol
2. Implement `src/poea/backends/null_backend.py`:
   - Accepts concept list and scored evidence list
   - Returns: `{"nodes": [...], "edges": [], "source": "null_backend"}`
3. Implement `src/poea/artifacts/exporters.py`:
   - `export_nodes(active_concepts) → nodes.json`
   - `generate_report(run_summary) → run_report.md`
4. Implement `src/poea/cli.py` — full `poea pipeline` command wiring all phases together
5. Integration test: `test_pipeline_null_backend.py` — full pipeline with null backend, no LLM calls

**Exit criteria:**
- `poea pipeline --backend null ...` produces all six artifacts
- `pytest test_pipeline_null_backend.py` passes without LLM calls
- Run report is human-readable and contains all required sections

---

## Phase 8: POE Adapter

**Milestone:** MVP-0
**Risk reduced:** The core deliverable — zero hand-authored variables, real ontology graph

**Tasks:**
1. Install POE as local dependency: `pip install -e ../probabilistic_ontology_engine`

2. Implement `src/poea/backends/poe_backend.py`:

   a. `build_poe_variables(active_concepts) → dict[str, Variable]`
   - For each concept: `Variable(variable_id=stable_variable_id(domain_id, name), name=name, domain_type=DomainType.BOOLEAN, support=[True, False])`
   - Use POE's existing `stable_variable_id()` function from `engine.variable_identity`

   b. `build_seed_candidate(poe_variables, domain_id) → OntologyCandidate`
   - Build `DependencyEdge` objects for all directed pairs where both concepts co-occurred in evidence (sparse seeding, not all-pairs)
   - Assign moderate existence priors (0.5)

   c. `build_dynamic_domain_module(active_concepts, poe_variables, seed_candidate, config) → DomainModule`
   - Construct a class implementing the POE domain module interface
   - `module_id()` → `f"poea-{domain_tag}-v{run_id[:8]}"`
   - `initial_candidates()` → `[seed_candidate]`
   - `existence_thresholds()` → default `EdgeExistenceThresholdConfig()`

   d. `build_poe_evidence_records(scored_assignments, poe_variables) → list[EvidenceRecord]`
   - For each evidence record's assignments, build `ObservedAssignment(variable_id=..., observed_value=True/False, confidence=..., missingness=...)`
   - Group into `EvidenceRecord` objects

   e. `learn_graph(concepts, scored_evidence, config) → dict`
   - Wire steps a–d together
   - Call `engine.register_domain()`, `engine.activate_domain()`, `engine.ingest_batch()`, `engine.learn()`
   - Return `{"nodes": [...], "dominant_candidate": {...}, "snapshot": {...}}`

3. CLI update: `poea run-backend --backend poe ...`

4. Tests: `test_poe_backend.py` (mocked POE)

**Exit criteria:**
```bash
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```
produces all six artifacts with zero manually supplied art ontology variables.

---

## Post-MVP Phases

The following phases are correctly ordered in IMPLEMENTATION_PLAN.md and are not modified here. They begin only after MVP-0 is accepted.

| Phase | Description | Dependency |
|-------|-------------|------------|
| 9 | Run reports (enhanced) | MVP-0 |
| 10 | Comparison mode (POE v1 vs POE-A) | MVP-0 |
| 11 | Latent validation (PCA/ICA over embeddings) | MVP-0 |
| 12 | Cross-run stability and pruning | Phase 11 |
| 13 | Hypothesis and mechanism generation | Phase 12 |
| 14 | Autonomous recurring runs | Phase 13 |

---

## Dependencies Between Phases

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
               ↑                   ↑                               ↑
       (evidence format)    (registry schema)              (scoring bridge)
```

Phase 6 cannot begin until Phase 5 completes (needs active concept set).
Phase 8 cannot begin until Phase 6 completes (needs scored evidence records).
Phase 7 can run in parallel with Phase 6 (null backend does not need scores).

---

## Anti-Patterns to Avoid

**Do not start Phase 8 without Phase 6.** The architecture review identified the missing evidence scoring bridge as a critical blocker. The temptation to wire the POE adapter before scoring is implemented will produce a POE integration that receives empty or random evidence records. This will appear to "work" (POE will learn something) but the resulting graph will be meaningless.

**Do not add latent validation to the critical path.** Phases 11-12 are explicitly post-MVP. If latent validation is added before MVP-0, the risk of blocking the primary milestone on a secondary feature is high.

**Do not pre-create empty modules for deferred phases.** The repository layout should reflect what is built, not what is planned. Empty `validation/` directories create the illusion of completeness.

**Do not use a fixed domain variable list as a "quick test."** It is tempting to seed the Phase 2 induction with known art variables to verify the pipeline works. This defeats the project's purpose and makes it impossible to validate that the system actually works without them. Use the null backend for pipeline testing; test concept quality qualitatively on the actual induced output.
