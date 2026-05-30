# Roadmap Audit

_Audited: 2026-05-30_
_Source documents: SPEC.md, IMPLEMENTATION_PLAN.md, README.md_
_Note: SNAPSHOT.md and NEXT.md do not exist in the repository._

---

## 1. Documented Phase Structure

The authoritative phase list is in `IMPLEMENTATION_PLAN.md`. Phases 0–12 are the MVP critical path. Phases 13–16 are explicitly post-MVP.

| # | Name | Objective | Dependencies |
|---|------|-----------|-------------|
| 0 | Bootstrap Repository | Working Python skeleton, CLI entrypoint, pytest/ruff passing | None |
| 1 | Evidence Loader | Load art evidence records into standard POE-A schema; strip pre-annotations | Phase 0 |
| 2 | Abductive Concept Discovery MVP | Generate candidate concepts from evidence via LLM; no hand-authored vocabulary | Phase 1 |
| 3 | Concept Registry MVP | Persist induced concepts in versioned SQLite registry with lifecycle tracking | Phase 2 |
| 4 | Concept Consolidation | Merge near-duplicate concepts; preserve lineage; prevent vocabulary explosion | Phase 3 |
| 5 | Active Concept Selection | Auto-promote candidates to active status via configurable thresholds; hard cap on count | Phase 4 |
| 6 | Evidence Scoring (Assignment Bridge) | Translate each evidence record into concept-keyed boolean assignments via LLM; cache results | Phase 5 |
| 7 | Backend Interface | Define pluggable `StructureLearningBackend` protocol; implement `NullBackend` | Phase 6 |
| 8 | Concept-to-Node Translation | Export active concepts as POE-compatible node artifacts | Phase 7 |
| 9 | POE Adapter | Wire POE-A to POE structure learner via `poe_backend.py`; first end-to-end run | Phases 6, 7, 8 |
| 10 | End-to-End Pipeline Command | Single `poea pipeline` command runs all stages; produces full artifact set | Phase 9 |
| 11 | Run Reports | Auditable run report covering all pipeline stages including scorer sample | Phase 10 |
| 12 | Comparative Mode | Compare POE-A graph against POE v1 snapshot | Phase 11 |
| 13 | Latent Validation Layer | Add PCA/ICA grounding after end-to-end pipeline works | Post-MVP; Phase 10 complete |
| 14 | Pruning and Stability | Cross-run stability metrics; automatic deprecation candidates | Post-MVP; Phase 13 |
| 15 | Hypothesis and Mechanism Generation | Extend abductive generation from concepts to causal mechanisms | Post-MVP; Phase 14 |
| 16 | Autonomous Recurring Runs | Continuous ontology-growth system with trigger-based scheduling | Post-MVP; Phase 15 |

---

## 2. Current Progress

The document evidence is limited because SNAPSHOT.md and NEXT.md are absent. The table below draws on README.md (which reflects what is actually buildable/runnable) combined with the user-reported implementation status.

| Phase | Status | Evidence |
|-------|--------|----------|
| 0 – Bootstrap Repository | **Complete** | README shows installable package; `poea` CLI entrypoints exist; pytest/ruff configured |
| 1 – Evidence Loader | **Complete** | README quickstart demonstrates `poea ingest` command producing `artifacts/evidence.json` |
| 2 – Abductive Concept Discovery MVP | **Complete** | README demonstrates `poea induce --dry-run` and live induction via `poea induce`; `raw_concepts.json` produced |
| 3 – Concept Registry MVP | **Complete** | User-reported; README architecture diagram shows "Concept Registry (Phase 3+)" as a downstream stage, implying it exists |
| 4 – Concept Consolidation | **Complete** | User-reported |
| 5 – Active Concept Selection | **Unclear** | User report groups this with "registry + consolidation" but does not name Phase 5 explicitly; no direct evidence from README |
| 6 – Evidence Scoring (Assignment Bridge) | **Not Started** | README architecture marks this as "Phase 6+"; no CLI command or module referenced as present |
| 7 – Backend Interface | **Not Started** | README marks as "Phase 9+"; no evidence of interface file |
| 8 – Concept-to-Node Translation | **Not Started** | No reference in README |
| 9 – POE Adapter | **Not Started** | README marks as "Phase 9+"; no POE dependency installed |
| 10–16 | **Not Started** | Explicitly future |

---

## 3. Current Phase

**What phase is the project currently in?**

The project has completed Phase 0 through Phase 4 (bootstrap, evidence loading, concept induction, registry, and consolidation). Phase 5 (Active Concept Selection) is ambiguous — it may be complete or may be partially implemented inside the registry lifecycle module.

**What is the next documented phase?**

If Phase 5 is complete: **Phase 6 — Evidence Scoring (Assignment Bridge)**

If Phase 5 is not yet complete: **Phase 5 — Active Concept Selection**

Phase 6 is the documented blocker for all subsequent phases. The implementation plan states explicitly:

> _"This phase must complete before the POE adapter can be built."_

---

## 4. Alignment Check

| User-Reported Item | Documented Phase | Match? |
|-------------------|-----------------|--------|
| Phase 0 bootstrap | Phase 0: Bootstrap Repository | Exact match |
| Phase 1 evidence ingestion | Phase 1: Evidence Loader | Exact match |
| Phase 2 concept induction | Phase 2: Abductive Concept Discovery MVP | Exact match |
| Registry implementation | Phase 3: Concept Registry MVP | Exact match |
| Consolidation implementation | Phase 4: Concept Consolidation | Exact match |

The user-reported progress is fully consistent with the documented phase numbering and names. No renaming or reordering discrepancy exists between what the user reports and what the implementation plan defines.

The only ambiguity is whether "registry + consolidation implementation" includes Phase 5 (Active Concept Selection), which is tightly coupled to the registry lifecycle module (`src/poea/registry/lifecycle.py`) that consolidation also touches.

---

## 5. Evidence Scoring Assessment

**Does the documented roadmap place Evidence Scoring before POE integration?**

**Yes, unambiguously.**

Relevant sections:

1. **IMPLEMENTATION_PLAN.md — Phase 6 header:**
   > _"This phase was absent from earlier versions of the implementation plan and identified as a critical missing step in the architecture review."_
   > _"This phase must complete before the POE adapter can be built."_

2. **IMPLEMENTATION_PLAN.md — Phase 9 dependency:**
   The POE Adapter (Phase 9) explicitly lists scored evidence as its input. The adapter translates `scored_evidence` assignments into POE `EvidenceRecord` objects. Without scorer output there is nothing for the adapter to pass to POE.

3. **IMPLEMENTATION_PLAN.md — Backend Interface (Phase 7):**
   The protocol signature is `learn_graph(..., scored_evidence, ...)` — not raw evidence. The contract assumes scoring has already occurred.

4. **SPEC.md — Architecture diagram:**
   The ordered stack is:
   ```
   Node Registry → Evidence Scoring → Backend Interface → Structure Learning
   ```
   Evidence Scoring is positioned between the registry and the backend in the canonical architecture.

5. **IMPLEMENTATION_PLAN.md — MVP-0 Acceptance Criteria:**
   The required pipeline sequence is:
   ```
   Evidence → Concept Discovery → Concept Registry → Evidence Scoring → Nodes → POE Graph
   ```
   Evidence Scoring is a required stage of MVP-0, not an optional enrichment.

**Role of Evidence Scoring:**

Evidence Scoring is the translation layer. It bridges the semantic world (concepts in the registry) and the statistical world (assignments that POE can train on). Without it, POE receives no evidence — the graph would reflect nothing real. The implementation plan calls it "the critical link between the concept registry and structure learning."

---

## 6. Discrepancies

### 6.1 Missing planning documents

SNAPSHOT.md and NEXT.md do not exist. The user's instructions treat them as present. Their absence removes the primary source of current-state truth. Progress assessment in this audit relies on README.md and user-reported status rather than authoritative snapshots.

### 6.2 LLM provider divergence

IMPLEMENTATION_PLAN.md specifies:

> _"The `anthropic` SDK is the default provider for all LLM calls."_
> _"Do not add LLM provider dependencies beyond `anthropic` until needed."_

README.md documents:

> _"Default provider: **Fireworks AI**"_
> _"Default model: `accounts/fireworks/models/deepseek-v3`"_
> _"Required env var: `FIREWORKS_API_KEY`"_

The implementation deviated from the planned provider. This is not a phase-sequence issue, but it represents a documented-vs-implemented mismatch that will matter when POE integration begins, since IMPLEMENTATION_PLAN.md was written with Anthropic SDK cost assumptions (e.g., batch scoring to reduce API cost) and model-specific behavior expectations.

### 6.3 Phase 5 status unclear

The user reports "registry + consolidation implementation" as complete but does not explicitly name Phase 5 (Active Concept Selection). Phase 5 implements `lifecycle.py` auto-promotion — the same module that Phase 3 creates. It is possible Phase 5 is fully implemented, partially implemented, or not yet started. This ambiguity should be resolved before Phase 6 begins, because Evidence Scoring requires an active concept set as its input.

### 6.4 No discrepancy in phase ordering

The documented phase sequence and the user's reported implementation sequence are consistent. There is no evidence that any phases were built out of order.

---

## 7. Recommendation

**A. Proceed to Evidence Scoring (Phase 6)**

**Justification:**

The documented roadmap is internally consistent and correctly places Evidence Scoring before POE integration. The phase sequence — consolidation, active concept selection, evidence scoring, backend interface, POE adapter — is well-motivated and should not be reordered.

Before beginning Phase 6, confirm one prerequisite:

- Verify Phase 5 (Active Concept Selection) is complete and that `poea registry promote --auto` produces a non-empty active concept set. Evidence Scoring takes active concepts as its primary input; if no concepts are active, the scorer produces no output.

Once Phase 5 is confirmed, Evidence Scoring is the correct next step. It is the blocking dependency for all remaining MVP phases (7, 8, 9, 10) and is explicitly identified in the implementation plan as the step that was historically missing and caused an architecture gap. Completing it unblocks the first end-to-end POE-A run.

No documentation update is required before proceeding. The plan is accurate and current.
