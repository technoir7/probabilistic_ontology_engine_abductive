# POE-A Risk Register

**Version:** 1.0
**Date:** 2026-05-30

Severity: Critical / High / Medium / Low
Likelihood: High / Medium / Low

---

## Technical Risks

---

### T1: Concept Explosion

**Severity:** Critical
**Likelihood:** High

Without effective consolidation, each induction run generates 50-200 candidate concepts from batched evidence. Multiple runs compound this: by run 3 the registry may contain 300-500 candidates, the majority being near-duplicates. This makes the active concept set unmanageably large, degrades POE performance (quadratic edge count growth), and makes run reports unreadable.

**Why it will happen:** LLMs are generative. Given the same evidence with minor variation in batch composition, they propose the same constructs under different names. Without consolidation, every variation enters the registry.

**Mitigation:**
1. Consolidation runs after every induction pass, not as an optional step.
2. Two-pass deduplication: exact normalized name matching first, LLM-assisted semantic merge second.
3. Hard cap on active concepts per domain (configurable, default 30). If promotion would exceed the cap, only the top-confidence candidates promote.
4. Monitor concept count per run in the run report. Flag runs that produce more than 2x the previous run's concept count.

---

### T2: Evidence Scoring Failure or Noise

**Severity:** High
**Likelihood:** Medium

The evidence-to-assignment bridge (Finding 1 in architecture review) requires scoring each (evidence record, concept) pair to produce a boolean assignment. If this scoring is noisy or biased, POE receives corrupt evidence records. Corrupt evidence records will produce an incorrect graph regardless of how well concept induction works. The failure is silent: POE will produce a graph, but the graph will reflect scoring noise rather than the actual causal structure in the evidence.

**Why it will happen:** LLM scoring of (evidence, concept) pairs is sensitive to concept definition quality and prompt framing. Vaguely defined concepts produce inconsistent True/False assignments across evidence records.

**Mitigation:**
1. Score at least 5-10 evidence records per concept before promoting a concept to active. Concepts that produce scoring distributions near 50/50 (neither clearly True nor clearly False across evidence) are uninformative and should be flagged.
2. Include neutral ("this evidence does not bear on this concept") as a valid scoring outcome. Map neutral to POE's `MISSING` missingness type rather than forcing a True/False assignment.
3. Add concept definition quality check to the induction prompt: concepts must be operationally defined (how would you determine if this is true or false in a document?) not just semantically labeled.
4. Store scoring output in the registry (`concept_evidence_links.support_strength`) for auditability.

---

### T3: Unstable Concept Names Across Runs

**Severity:** High
**Likelihood:** High

LLMs do not produce consistent names for the same underlying concept across multiple induction runs. "AuthenticityPremium" in run 1 may become "AuthenticValue" in run 2 and "RealnessDemand" in run 3. These are semantically identical but will enter the registry as three distinct candidates unless consolidation catches them.

The deeper problem: if consolidation misses the merge, the POE variable UUID (derived from concept name) will differ across runs. POE uses stable UUIDs to match historical evidence records to current variable definitions. Unstable names produce UUID drift, which means each run starts learning from scratch.

**Mitigation:**
1. Stable variable UUIDs must be derived from the **canonical name** in the registry, not from the LLM-proposed name. Canonical name is set at first creation and never changed (renames are merges with history).
2. Consolidation should run across runs, not just within a single run. At the start of each induction pass, load all existing active/candidate concepts and include them in the deduplication comparison.
3. After MVP-0, consider a name normalization step that maps LLM-proposed names to canonical forms before registry insertion.

---

### T4: POE Integration Brittleness

**Severity:** High
**Likelihood:** Medium

POE-A's POE adapter constructs a dynamic domain module from induced concepts. This is not a use case POE was designed for. Specifically:
- POE's initial candidate construction expects domain-specific edge topology, not all-pairs
- All-pairs edges with N concepts produce N*(N-1) edges. At N=20 this is 380 edges. POE's population manager will explore all of these, which may be computationally expensive and produce structurally noisy results.
- POE's `_restore_candidate_scores` at startup expects stable UUIDs. Dynamically generated UUIDs must be derived deterministically, not from `uuid4()`.

**Mitigation:**
1. Use `stable_variable_id(domain_id, concept_name)` (POE's existing deterministic hash) for all variable UUIDs in the POE adapter.
2. Build the null backend first. Validate the full pipeline works without POE. Only then add the POE adapter.
3. Start with a smaller active concept set (10-15 concepts) for initial POE integration testing. Validate that POE learns a non-trivial graph before scaling up.
4. Consider a sparse initial edge topology: instead of all-pairs, seed only edges where both concepts appeared in the same evidence record. This reduces edge count from O(N²) to O(E) where E is the number of co-occurring pairs.

---

### T5: LLM API Failures and Cost Overruns

**Severity:** Medium
**Likelihood:** Medium

Concept induction, consolidation, and evidence scoring all require LLM API calls. For a 50-record evidence set with 20 active concepts, evidence scoring requires 50×20 = 1000 API calls (or efficient batching). A full pipeline run may cost $5-50 depending on model and batching strategy.

Additionally, API rate limits and transient failures will interrupt multi-step pipeline runs. Without idempotent processing, a failure mid-run wastes all prior API spend.

**Mitigation:**
1. Implement a simple cache layer for LLM calls keyed on (prompt_hash, model). Cache hits avoid re-calling the API on retries. Cache lives in the registry SQLite file.
2. Evidence scoring should be batched: score all concepts for a single evidence record in one API call (not one call per concept per record).
3. Induction runs should checkpoint after each batch. A failed run can resume from the last successful batch.
4. Default to a cost-efficient model for evidence scoring (smaller, faster model). Reserve the more capable model for concept induction.

---

### T6: Registry Corruption

**Severity:** Medium
**Likelihood:** Low

SQLite is single-writer. If two pipeline processes run concurrently against the same registry file, WAL mode will serialize writes, but a poorly timed interrupt during a multi-statement transaction may leave the registry in an inconsistent state. More likely: a bug in lifecycle.py that produces an invalid status transition.

**Mitigation:**
1. All registry writes use transactions. No partial state is possible.
2. Status transitions are validated before write: illegal transitions (e.g., `rejected → active`) raise an exception.
3. Add a registry integrity check command: `poea registry check --db ...` that validates referential integrity and status consistency.
4. The `concept_events` table is append-only and is never modified. It serves as a recovery log.

---

## Research Risks

---

### R1: Induced Concepts Are Trivial

**Severity:** High
**Likelihood:** Medium

The LLM may induce concepts that are obvious topic labels rather than explanatory mechanisms. For art market evidence: "ArtSales," "GalleryRevenue," "MarketGrowth" are accurate summaries of the evidence but are not causally interesting. They do not discriminate between competing causal stories. A graph built from trivial concepts will look complete but will have no explanatory power.

**Signs of this failure:** Active concepts are all nouns that appear directly in document titles. Concepts have near-identical support evidence (every document supports every concept).

**Mitigation:**
1. The induction prompt must explicitly instruct the LLM to look for **mechanism** variables — constructs that could be causally upstream or downstream of other constructs — not topic labels.
2. Include a negative example in the prompt: "Do not propose concepts like 'ArtMarket' or 'GallerySales' — these describe the domain but do not explain causation within it."
3. After MVP-0, evaluate concept quality by checking whether the induced graph has non-trivial structure (not a fully connected clique, not a single chain).

---

### R2: Concepts Collapse into Document Topics

**Severity:** High
**Likelihood:** Medium

A closely related failure: instead of cross-cutting mechanisms, the LLM induces concepts that are essentially chapter headings of the evidence corpus. Each concept corresponds to one article's main topic. The registry grows proportionally with the evidence set without producing genuine ontological structure.

**Signs of this failure:** Each concept is supported by only 1-2 evidence records. Consolidation produces no merges. Graph has low density.

**Mitigation:**
1. The batch size must be large enough that concepts must appear across multiple documents within a batch. Batches of fewer than 10 documents will tend to produce per-document concepts.
2. The multi-batch requirement (concepts must appear in at least 2 batches to survive consolidation) is a crucial filter and must be enforced.
3. The induction prompt should explicitly ask: "Would this concept appear if you were analyzing evidence from a different time period or a different subset of this corpus? If not, it is too specific."

---

### R3: Induced Vocabulary Fails to Generalize

**Severity:** Medium
**Likelihood:** Medium

Concepts induced from 2026 art market evidence may be too time-specific to generalize to other evidence periods. "AIImageSaturation" is a 2026 phenomenon. A vocabulary that only works for one time slice is not a reusable ontology.

This risk matters most for the long-term vision of POE-A as a continuous ontology system. For MVP-0, it is not a blocker since the goal is to demonstrate vocabulary-free construction, not temporal generalization.

**Mitigation:**
1. Deferred to post-MVP evaluation.
2. The cross-run stability metrics in Phase 13 are the primary mitigation: concepts that appear consistently across runs on different evidence slices are generalizable; those that don't are time-specific and should be flagged for review.

---

### R4: Concept Definitions Are Inconsistent Across Batches

**Severity:** Medium
**Likelihood:** High

The same underlying concept may be defined differently in different induction batches. "AuthenticityPremium" in batch 1 may be defined as "buyers' preference for hand-made over AI-generated work" while in batch 3 it is defined as "price premium for certified provenance." These are related but not identical. Consolidation must detect and reconcile these definitional variations.

If consolidation merges them with the batch 1 definition, the merged concept's definition may not accurately represent all its supporting evidence. If consolidation doesn't merge them, the registry has two near-identical concepts with inconsistent definitions.

**Mitigation:**
1. When merging two concepts, the canonical definition should be synthesized from both, not just the "winner's" definition. The merge step should include a definition synthesis prompt: "Given these two definitions for the same underlying concept, produce a unified definition that captures both."
2. Track `definition_version` in the registry. When a merge updates the canonical definition, record the change as a `concept_event`.

---

### R5: Latent Validation Is Inconclusive

**Severity:** Low
**Likelihood:** Medium

When latent validation is added (Phase 12), it may produce alignment scores that don't discriminate well between useful and useless concepts. If most concepts are "ungrounded" (no strong latent factor alignment), the ungrounded retention policy means the validation layer adds no signal.

This is a research risk specific to text domains: text evidence lacks the numeric signal structure that makes PCA/ICA alignment meaningful. In the art domain, there may simply not be enough numeric signal to validate semantic concepts.

**Mitigation:**
1. Do not let latent validation block post-MVP progress. If validation proves inconclusive, document it as a finding and proceed.
2. The fallback is that concept quality is assessed by graph usefulness (downstream) rather than latent alignment (upstream). POE's own learning metrics become the validation signal.

---

## Architectural Risks

---

### A1: POE Interface Instability

**Severity:** High
**Likelihood:** Medium

POE-A depends on POE's internal schemas (`Variable`, `DependencyEdge`, `OntologyCandidate`, `EvidenceRecord`, `ObservedAssignment`). If POE refactors its schema — renames a field, changes a type, restructures `OntologyCandidate` — the POE adapter breaks silently or with cryptic errors.

**Mitigation:**
1. The POE dependency is isolated to `backends/poe_backend.py`. Any breaking change in POE requires changes only in that single file.
2. The `test_poe_backend.py` test imports POE's schemas directly and validates that the POE adapter's output matches them. If POE changes, this test will break visibly.
3. Maintain a documented list of POE schema fields that the POE adapter uses. Before updating the POE dependency, check the list.

---

### A2: Registry Becomes the Bottleneck

**Severity:** Medium
**Likelihood:** Low (for MVP scale, High for 10k+ concept scale)

SQLite's single-writer model is adequate for MVP. If POE-A runs multiple induction jobs in parallel (different domains, scheduled runs), registry write contention becomes a bottleneck. At 500+ active concepts the consolidation pass (which reads all concepts for comparison) becomes slow.

**Mitigation:**
1. For MVP-0, this is not a concern. Document the limitation.
2. If scaling becomes necessary, the registry schema is already PostgreSQL-compatible per POE's precedent. Migration path exists.
3. Consolidation can be run as a batch operation against a read-consistent snapshot. It does not need to lock the registry during comparison.

---

### A3: Evidence Scorer Becomes the Latent Source of Truth

**Severity:** Medium
**Likelihood:** Medium

The evidence scorer assigns True/False/neutral to each (evidence, concept) pair. These assignments become the data that POE learns from. If the scorer is systematically biased — e.g., it assigns True to "high-prestige" concepts more often than warranted — the resulting graph will reflect the scorer's biases, not the actual evidence structure.

This is a subtle and serious risk: the evidence scorer inserts an interpretation layer between raw evidence and structure learning. POE v1 avoids this by having domain experts provide explicit `assignments` fields. POE-A replaces domain expert annotation with LLM annotation. LLM annotation introduces different (possibly less visible) biases.

**Mitigation:**
1. Expose scorer output in the run report. Every (evidence, concept, assignment) triple should be inspectable.
2. Include a `scoring_confidence` field in `ObservedAssignment`. Low-confidence assignments should use POE's `SOFT_OBSERVED` missingness type, not hard True/False.
3. Post-MVP: add a human spot-check workflow where a sample of scorer outputs are reviewed against the original text.

---

### A4: Overcoupling to Art Domain

**Severity:** Low
**Likelihood:** Medium

The evidence loaders, example fixtures, and CLI defaults are all art-domain specific. If the configuration and examples assume art evidence format, the system will not generalize to other domains without significant changes.

**Mitigation:**
1. The evidence normalizer must be domain-agnostic. Art-specific handling (stripping the `assignments` field) should be configurable, not hardcoded.
2. The `domain_tag` config field is the only domain-specific input. Everything else should work for any text evidence corpus.
3. After MVP-0, test against a second domain (the AI regime domain evidence is a natural candidate) to confirm generalization.

---

### A5: Spec-Code Drift

**Severity:** Low
**Likelihood:** High (over time)

The spec (SPEC.md), the implementation plan, and the architecture review documents describe design intent. As implementation proceeds and decisions are made, these documents will diverge from the code. In a research system that evolves rapidly, spec-code drift is nearly inevitable.

**Mitigation:**
1. Do not try to keep SPEC.md perfectly synchronized — it is a design artifact, not a living document.
2. The run report is the living record of what the system actually does. It should be authoritative about runtime behavior.
3. When a design decision diverges from SPEC.md or IMPLEMENTATION_PLAN.md, record the divergence in a DECISIONS.md file with a brief rationale. This preserves design history without requiring spec rewrites.
