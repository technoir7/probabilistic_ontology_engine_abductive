# POE-A Architecture Review

**Reviewer:** Lead Architect
**Date:** 2026-05-30
**Documents reviewed:** SPEC.md, IMPLEMENTATION_PLAN.md
**POE codebase inspected:** src/engine/engine.py, src/engine/schemas.py, src/domains/ai_regime_v1/domain.py
**Evidence format inspected:** art-market-domain/data/manual_ingest_split/

---

## Executive Summary

The design direction is correct. The epistemic goal — removing the fixed vocabulary assumption — is clear, the dependency architecture is sound, and the phased build plan is appropriately pragmatic. This is a buildable system.

However, there are seven findings that require attention before implementation begins. Two are critical blockers that would cause the Phase 8 POE adapter to silently fail. The rest are significant but non-blocking if addressed in the design phase.

---

## Naming Inconsistency: VIE vs POE-A

**Severity: Medium. Must be resolved before any code is written.**

SPEC.md calls the system "Variable Induction Engine (VIE)" and declares `Repository: variable-induction-engine`. IMPLEMENTATION_PLAN.md calls the system "Probabilistic Ontology Engine Abductive (POE-A)" and declares `Repository: probabilistic_ontology_engine_abductive`. The actual directory on disk is `probabilistic_ontology_engine_abductive`.

SPEC.md was written for a differently-named project and was not updated when the name changed. All references to VIE in the spec should be treated as POE-A for implementation purposes.

The architecture review throughout this document uses POE-A exclusively.

---

## Finding 1 (Critical): The Evidence-to-Assignment Bridge Is Missing

**This is the single most significant omission in both documents.**

POE does not accept text documents. POE accepts `EvidenceRecord` objects. Each `EvidenceRecord` contains a list of `ObservedAssignment` objects. Each `ObservedAssignment` maps a `variable_id` (UUID) to a concrete observed value (True/False for BOOLEAN variables).

To feed POE, POE-A must translate each text evidence document into an `EvidenceRecord` where every active concept has been evaluated to True or False (with confidence) for that document. This is a distinct processing step: **evidence scoring**.

Neither SPEC.md nor IMPLEMENTATION_PLAN.md names this step, defines its inputs/outputs, or assigns it to a phase. It is implied but never made explicit. Phase 7 (Concept-to-Node Translation) and Phase 8 (POE Adapter) assume this problem is solved, but the mechanism is absent.

Without an evidence scoring step, Phase 8 cannot produce a working POE integration. The export format in Phase 7 produces `nodes.json`, but producing `EvidenceRecord` objects requires scoring each (evidence_document, concept) pair.

**What is needed:** A dedicated `evidence_scorer.py` module that, given a list of active concepts and a list of text evidence records, produces POE-compatible `EvidenceRecord` objects. For MVP, the simplest viable approach is an LLM call per evidence batch: given the concept definition and a text record, does this evidence record support, contradict, or not bear on this concept?

This must be added to the implementation plan as an explicit phase, and it belongs in the critical path before the POE adapter.

---

## Finding 2 (Critical): The Art Evidence Is Pre-Annotated

Inspecting the actual evidence in `art-market-domain/data/manual_ingest_split/`, the files contain structured `assignments` fields that map named variables (`MarketUncertainty`, `CollectorFlightToSafety`, etc.) directly to boolean values with confidence scores. These are already-annotated evidence records, not raw text.

If POE-A ingests these files and reads the `assignments` fields, it will have access to the manually-designed vocabulary it is supposed to be discovering. That is precisely what POE-A must not do. The epistemic cleanliness criterion requires that POE-A treat the underlying text as the evidence, not the pre-existing annotations.

The evidence loader must be written to ingest only the raw text fields (`title`, `notes`, the text content of each article) and ignore `assignments` and `causal_claims` fields. The annotations in those files represent a POE v1 vocabulary that POE-A should treat as a comparison baseline, not an input.

The Phase 1 spec says to support "existing art evidence format" without specifying which fields to read. This must be made explicit: the evidence normalizer must extract text content only and discard pre-existing variable annotations.

---

## Finding 3 (High): The Backend Interface Design Does Not Match POE's Actual Interface

The proposed `StructureLearningBackend` protocol is:

```python
class StructureLearningBackend(Protocol):
    def learn_graph(
        self, concepts, evidence, config
    ) -> Mapping[str, Any]: ...

    def score_hypotheses(
        self, graph, evidence, config
    ) -> Mapping[str, Any]: ...
```

POE's actual interface is substantially more complex. POE requires:

1. **A domain module object** implementing `module_id()`, `initial_candidates()`, and `existence_thresholds()`. The `initial_candidates()` method must return a list of `OntologyCandidate` objects, each containing `Variable` objects (with UUIDs, domain_type, support lists) and `DependencyEdge` objects.

2. **`EvidenceRecord` objects** (not generic dicts). Each `EvidenceRecord` contains `ObservedAssignment` objects keyed to `variable_id` UUIDs — not names.

3. **Registration and activation**: `engine.register_domain(domain_module)` and `engine.activate_domain(module_id)` must be called before evidence can be ingested or learning can begin.

4. **Variable UUID stability**: POE uses stable UUIDs derived from the domain/variable name combination. If POE-A restarts and regenerates variable UUIDs, historical evidence records will fail to match new UUIDs.

The proposed `learn_graph(concepts, evidence)` abstraction hides all of this complexity inside the adapter. That is appropriate. But the adapter itself will need to:
- Construct `Variable` objects from concept definitions (choosing BOOLEAN as the domain type for MVP)
- Generate stable UUIDs for each concept (deterministic, not random, so they survive restarts)
- Build initial candidate `OntologyCandidate` objects (with all-pairs edges as the seed population)
- Build `EvidenceRecord` objects from scored evidence
- Register the dynamically constructed domain module with POE

The `poe_backend.py` adapter is the most complex piece of POE-A. The plan should not underestimate it.

---

## Finding 4 (High): SPEC and Plan Contradict on Auto-Promotion

SPEC.md, under "Human Oversight," states:

> Automatic promotion is prohibited.
> The system may not autonomously modify active ontology state.

IMPLEMENTATION_PLAN.md Phase 5 states:

> Since POE-A is meant to operate without human-authored variables, the system must be able to select active concepts automatically.

And the config includes `allow_auto_promotion: true`.

These are in direct contradiction. The resolution is architectural, not cosmetic: for MVP-0 to meet its acceptance criterion (one command produces a graph without human intervention), auto-promotion must be permitted. The spec's prohibition on automatic promotion is incompatible with a fully autonomous pipeline.

**Resolution:** The spec's human oversight clause should be understood as applying to permanent ontology state changes — specifically, the transition from `candidate` to `active` in a production registry. For MVP-0, auto-promotion with explicit configurable thresholds is permitted. The spec should be amended to distinguish between (a) MVP auto-promotion with audit trail and (b) production governance requiring human approval. Both can coexist.

---

## Finding 5 (Medium): The Latent Validation Stage Has a Scope Mismatch

SPEC.md Stage 2 describes PCA and ICA over "numeric signals" with "rolling-window z-scores." But the primary art domain evidence is text, not numeric time series.

PCA/ICA over text requires embedding text first (using a sentence transformer or similar), then running dimensionality reduction over the embedding matrix. This is fundamentally different from PCA over market price time series. The spec conflates these two cases without acknowledging the difference.

Concretely: the art evidence contains text articles, reports, and press releases — not FRED series or yfinance time series. Applying PCA/ICA to text evidence requires either:
- Embedding each evidence document to a fixed-size vector, then running PCA on the matrix of embeddings
- Using topic models (LDA, NMF) over TF-IDF representations

Both are valid but the spec implies the former while providing retention rules that only make sense for continuous numeric signals ("explain at least 2% variance").

Since latent validation is correctly deferred to Phase 12 in the implementation plan, this is not a blocker. But the latent validation module must be designed with text-native extraction methods, not assumed to be a trivial application of sklearn's PCA to a pre-existing numeric matrix.

---

## Finding 6 (Medium): Consolidation Is the Hidden Complexity of MVP

The consolidation stage (Phase 4) is described as "similarity detection → merge candidates → canonical concepts." The SPEC sets a threshold of 0.85 definition similarity but does not define how similarity is measured.

In practice, naive string similarity (Levenshtein, Jaccard) will fail on semantic paraphrases. Embedding cosine similarity requires an embedding model. LLM-assisted merging is effective but expensive at scale.

Concept explosion is listed as a top risk — and it is real. With 50 evidence records, batched into groups of 20-60, a single induction run may produce 50-200 candidate concepts. Without effective consolidation, each subsequent run adds another 50-200 near-duplicates. The registry can become unmanageable within three runs.

The plan's consolidation implementation (`consolidation.py`, `dedupe.py`) is correct in existence but underspecified in method. For MVP, the recommendation is a two-pass approach:
- Pass 1: exact normalized name matching (fast, cheap, handles the obvious cases)
- Pass 2: LLM-assisted merge pass with a structured comparison prompt

Embedding similarity should be optional and configured off by default until it proves necessary.

---

## Finding 7 (Low): The Repository Layout Pre-Creates Deferred Modules

The proposed initial layout includes:

```text
src/poea/validation/
    latent.py
    alignment.py
    pruning.py
```

These modules are for Phase 12 and Phase 13 — deferred post-MVP features. Creating empty directories and stub files upfront for features that are explicitly "What Not To Build First" adds noise without value.

The initial repository layout should only include what will be populated during MVP-0. Deferred modules can be created when their phases begin.

---

## Finding 8 (Low): Concept Schema Adds Complexity to MVP Prompts

The concept schema for Phase 2 includes:

```json
{
  "epistemic_role": "driver | outcome | mediator | context | unknown",
  "direction": "positive_signal | negative_signal | bidirectional | unknown",
  "frequency": "persistent | episodic | shock | unknown"
}
```

These fields are analytically interesting but require the LLM induction prompt to reason about epistemic roles and signal directions — which adds prompt complexity and increases the probability of hallucinated or internally inconsistent outputs.

For MVP-0, none of these fields affect the core pipeline. The POE adapter does not use them. The registry stores them but does not act on them. Including them in the MVP concept schema increases the chance of poor induction quality without adding capability that MVP-0 needs.

**Recommendation:** Move `epistemic_role`, `direction`, and `frequency` to a separate enrichment pass (post-consolidation, optional). The MVP concept schema needs only: `name`, `definition`, `confidence`, `supporting_evidence_ids`.

---

## Finding 9 (Low): Model Routing Is Underspecified

The configuration specifies:

```yaml
models:
  induction: accounts/fireworks/models/deepseek-v3
  prototype: accounts/fireworks/models/apriel-1-6-15b-thinker
  prefilter: accounts/fireworks/models/llama-v3p2-3b-instruct
```

These are Fireworks AI model identifiers. The implementation plan adds `openai` as an optional dependency. These are not the same API. Using Fireworks requires the Fireworks client, not the OpenAI client (though Fireworks has an OpenAI-compatible endpoint).

The plan does not specify which client library to use or how model routing should be abstracted. For MVP, a single LLM provider and model is sufficient. The multi-model tiered approach (induction/prototype/prefilter) is an optimization that belongs post-MVP.

**Recommendation:** For MVP, use a single configurable LLM client with a single model. Add the `anthropic` SDK as the default — it is the most capable and most naturally suited to the structured output tasks POE-A requires. Defer the multi-tier model routing.

---

## Strengths

The design has genuine strengths that should be preserved:

**The dependency direction is correct and strictly enforced.** POE-A upstream of POE, never the reverse. This is architecturally sound and must be maintained.

**The registry as a scientific record (never delete, preserve lineage) is the right design.** The concept event log (`concept_events` table) gives future operators the ability to audit every change. This should not be simplified away.

**The null backend is a good idea.** It lets the entire pipeline run without POE, which is essential for testing and for evaluating whether POE-A's concept generation is working before committing to the more complex POE integration.

**The build-order decision to defer latent validation is correct.** Getting an end-to-end working system first, then adding statistical grounding, is the right risk management strategy.

**The philosophical acceptance test is useful:** "The system receives evidence before it receives concepts." This single sentence disambiguates the system's purpose and can serve as a quick sanity check on any implementation decision.

---

## Summary Table

| Finding | Severity | Blocks MVP-0 |
|---------|----------|--------------|
| 1: Missing evidence-assignment bridge | Critical | Yes |
| 2: Art evidence is pre-annotated | Critical | Yes (logical) |
| 3: Backend interface underestimates POE complexity | High | Partial |
| 4: Auto-promotion contradiction | High | Yes (logical) |
| 5: Latent validation scope mismatch | Medium | No (deferred) |
| 6: Consolidation underspecified | Medium | Partial |
| 7: Pre-created deferred modules | Low | No |
| 8: Concept schema over-specified for MVP | Low | No |
| 9: Model routing underspecified | Low | Partial |
