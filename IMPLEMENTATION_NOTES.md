# Implementation Notes: Phases 0–2 (updated: provider migration)

**Date:** 2026-05-30
**Status:** Phase 2 complete. Stopping for review before Phase 3.

---

## Files Created / Modified

```
pyproject.toml               (anthropic → openai)
README.md                    (updated for Fireworks)
.gitignore
configs/induction_config.yaml (model → deepseek-v3, batch size → 20)

src/poea/__init__.py
src/poea/cli.py
src/poea/llm.py              (NEW: LLMClient protocol + FireworksClient)

src/poea/evidence/__init__.py
src/poea/evidence/schemas.py  (stable_evidence_id now hashes full text)
src/poea/evidence/normalizer.py (passes text to stable_evidence_id)
src/poea/evidence/loaders.py

src/poea/concepts/__init__.py
src/poea/concepts/schemas.py
src/poea/concepts/prompts.py
src/poea/concepts/inducer.py  (removed anthropic; uses LLMClient protocol)

tests/conftest.py             (mock_anthropic_client → mock_llm_client)
tests/fixtures/sample_evidence_annotated.json
tests/fixtures/sample_concepts_response.json
tests/test_evidence_normalizer.py (+ 6 ID collision tests)
tests/test_evidence_loader.py     (+ test_real_art_evidence_no_id_collisions)
tests/test_concept_schema.py
tests/test_concept_inducer.py     (removed anthropic; + live smoke test)
```

---

## Test Results

```
62 passed, 1 skipped (live test, requires FIREWORKS_API_KEY)
ruff: all checks passed
```

No live API calls in the test suite. All LLM interactions are mocked.

---

## CLI Usage

```bash
# Install
pip install -e .

# Phase 1: load evidence
poea ingest \
  --input ../art-market-domain/data/manual_ingest_split \
  --domain art \
  --output artifacts/evidence.json

# Inspect prompt without spending API budget
poea induce --evidence artifacts/evidence.json --dry-run

# Phase 2: induce concepts (requires FIREWORKS_API_KEY)
export FIREWORKS_API_KEY=your-key-here
poea induce \
  --evidence artifacts/evidence.json \
  --output artifacts/raw_concepts.json \
  --verbose
```

---

## Architecture Decisions

### Evidence IDs

Stable IDs are computed as `sha256(source_filename:title)[:16]`. This means the same article loaded from the same file always gets the same ID across runs, enabling stable cross-run references in Phase 3 (registry) and Phase 6 (evidence scoring).

### Pre-Annotation Stripping

The `_EXCLUDED_FIELDS` constant in `normalizer.py` governs which fields are discarded. Currently `{assignments, causal_claims}`. This is the enforcement point for the architectural constraint. The test `test_no_domain_vocabulary_in_text` verifies that variable names and rationale text from the `assignments` field do not appear in the normalized evidence text.

### Batching

The inducer splits evidence into batches of up to `max_records_per_batch` (default 40) and calls the LLM once per batch. Each batch result is independent — if one batch fails, others proceed. The full output includes one `InductionBatchResult` per batch, each with its own concept list.

### JSON Extraction

LLMs sometimes wrap JSON in markdown code fences or add preamble text. `_extract_json()` tries three strategies: direct parse, extract from ` ```json ``` ` fences, and regex extraction of the first `{...}` block. This handles real-world LLM output variation reliably.

### Evidence ID Restriction in Concepts

When the LLM proposes `supporting_evidence_ids`, the inducer filters out any ID not present in the current batch. This prevents the LLM from hallucinating evidence IDs from other batches or from memory.

### Prompt Domain-Agnosticism

The system prompt and user message format contain no domain-specific vocabulary. The prompt describes the epistemological structure of a "concept" in generic terms (mechanism, force, structural factor) and gives generic examples of the *type* of concept to find. The test `test_inducer_no_domain_vocabulary_injected` verifies this by checking that all known art ontology variable names are absent from both the system prompt and the user message.

### Sparse Record Handling

Records from `huge_evidence_27may26.json` have only a title (no `notes` body). These are flagged with `metadata["sparse_text"] = True`. The CLI reports the count of sparse records. The inducer treats them identically to full records — the LLM will extract less from a title than from a full article, but the information in news article titles (auction results, market events) still provides some signal.

---

## Issues Discovered

### Duplicate Evidence IDs in Art Data

The SFMOMA file (`sfmoma_2026_exhibitions.fixed.json`) contains two records with identical titles:
```
"Exclusive SFMOMA Presentation of Matisse's Femme au chapeau:..."
```

Since the stable ID is derived from `source:title`, both records receive the same `evidence_id` (`0022a6b2980fa4a6`). The ingest output shows 70 records loaded but only 69 unique IDs.

**Impact on Phase 2:** Low. The inducer processes all 70 records regardless of ID uniqueness. Concept proposals that reference this ID will be consistent since both records have similar content.

**Recommended fix for Phase 3:** Update `stable_evidence_id` to include the first 50 characters of `notes` in the hash, or add a per-file deduplication pass in the loader that appends an index suffix to duplicate IDs. The fix should happen before Phase 3 creates the registry, since registry keys are based on `evidence_id`.

### Title-Only Records (21 of 70)

All 21 title-only records come from `huge_evidence_27may26.json`. These are news article headlines without body text. The LLM can extract some concept signal from titles (e.g., "Trophy Buyers Drive Decorative Art Sales" implies a `TrophyBuyerConcentration` mechanism), but concept proposals from these records will be less precise than those from full articles.

**Recommendation:** Do not exclude these records. Their titles are informative. But when evaluating concept quality in Phase 2, note which concepts are primarily supported by title-only evidence.

---

## Recommendations Before Phase 3

### 1. Fix Duplicate Evidence IDs

Before implementing the registry (Phase 3), update the ID generation to prevent collisions. The simplest fix:

```python
def stable_evidence_id(source: str, title: str, text_prefix: str = "") -> str:
    payload = f"{source}:{title}:{text_prefix[:50]}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
```

Or add a loader-level deduplication pass.

### 2. Run a Live Induction Pass Before Phase 3

Before designing the registry schema extensions, run `poea induce` on the actual art evidence with a live API key and inspect the output. This will reveal:
- Typical concept count per batch (affects consolidation design)
- Concept naming patterns (affects deduplication strategy)
- Quality range (affects promotion threshold calibration)

The registry schema in Phase 3 should be informed by what the inducer actually produces, not only by what we expect it to produce.

### 3. Consider Batch Size for Art Evidence

With 70 records and a batch size of 40, the inducer runs 2 batches. The first batch (40 records) is heterogeneous — it mixes Hiscox report sections, art market analysis, and news headlines. The second batch (30 records) is more focused.

Consider reducing batch size to 15-20 for richer induction (more focused evidence clusters) vs larger batches for cross-document concept generalization. Test both before committing to a default.

### 4. Consolidation Must Be Ready Before Registry Grows

The consolidation module (Phase 4) is more critical than the registry alone. Run Phase 2 (induction) → Phase 4 (consolidation) before Phase 3 (registry persistence) at scale. This avoids importing hundreds of near-duplicate candidates that then need cleanup.

The recommended build order within Phase 3-4: implement registry + consolidation as a unit, not as sequential stand-alone phases.

---

## Example Output Format

When `poea induce` completes successfully, `artifacts/raw_concepts.json` will have this structure:

```json
{
  "model": "claude-sonnet-4-6",
  "evidence_count": 70,
  "batch_count": 2,
  "concept_count": 24,
  "errors": [],
  "concepts": [
    {
      "name": "ConceptName",
      "definition": "What it is and how it works.",
      "confidence": 0.82,
      "supporting_evidence_ids": ["abc123def456", "def456abc789"]
    }
  ]
}
```
