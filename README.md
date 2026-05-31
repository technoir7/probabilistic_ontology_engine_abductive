# Probabilistic Ontology Engine Abductive (POE-A)

POE-A constructs ontology graphs from evidence without requiring a fixed, hand-authored domain vocabulary.

## Quickstart

```bash
# Install
pip install -e .

# Run the full pipeline from raw evidence to graph
export FIREWORKS_API_KEY=your-key-here
poea pipeline \
  --domain art \
  --input ../art-market-domain/data/manual_ingest_split \
  --backend poe \
  --output artifacts/poea_graph.json
```

The pipeline reuses existing intermediate artifacts unless `--force` is passed.
It writes `artifacts/run_report.md` on every run.

Regenerate the latest report from existing artifacts without live API calls:

```bash
poea report --run latest
```

## Manual Stage Commands

```bash
# Load evidence (strips pre-existing variable annotations)
poea ingest --input ../art-market-domain/data/manual_ingest_split --domain art --output artifacts/evidence.json

# Inspect the prompt without spending API budget
poea induce --evidence artifacts/evidence.json --dry-run

# Induce concepts (requires Fireworks API key)
export FIREWORKS_API_KEY=your-key-here
poea induce --evidence artifacts/evidence.json --output artifacts/raw_concepts.json --verbose

# Build concept registry and select active concepts
poea consolidate --concepts artifacts/raw_concepts.json --output-dir artifacts

# Re-apply promotion with adjusted thresholds (no re-induction needed)
poea registry promote --include-suppressed --confidence 0.65 --auto

# Assign evidence against active concepts.
# Structured evidence routes through deterministic/direct assignment; prose routes through the LLM scorer.
poea score-evidence --concepts artifacts/canonical_concepts.json --evidence artifacts/evidence.json --output artifacts/scored_evidence.json --verbose

# Export nodes and run a backend manually
poea export-nodes --concepts artifacts/canonical_concepts.json --output artifacts/nodes.json --domain art
poea run-backend --backend poe --concepts artifacts/canonical_concepts.json --scored-evidence artifacts/scored_evidence.json --output artifacts/poea_graph.json

# Regenerate an audit report from the current artifacts
poea report --run latest --output-dir artifacts
```

## LLM Provider

Default provider: **Fireworks AI**
Default model: `accounts/fireworks/models/deepseek-v4-pro`
Required env var: `FIREWORKS_API_KEY`

The LLM client is provider-agnostic. `FireworksClient` uses Fireworks' OpenAI-compatible
endpoint. To use a different OpenAI-compatible provider, subclass or replace `FireworksClient`
in `src/poea/llm.py`.

**Assignment routing** is deterministic. The default route is deterministic/direct
assignment — not LLM scoring. LLM scoring is opt-in for explicit prose evidence only.

- `evidence_type: prose_text` / `unstructured_text` → `SemanticLLMScorerBackend` (Fireworks)
- `evidence_type: structured_numeric` / `tabular` / `api_derived` → `DeterministicMapperBackend` (0 Fireworks calls)
- `assignment_mode: direct_structured` or pre-existing assignments in metadata → `DirectStructuredAssignmentBackend` (0 Fireworks calls)
- `evidence_type: mixed` → `HybridPrefilterScorerBackend` (direct where possible, semantic fallback)
- Unknown structured evidence → explicit routing error, no LLM fallback

Old POE deterministic mappers from the sibling `../probabilistic_ontology_engine/src/domains/`
are reused via `OldPOEDomainMapperAdapter`. Supported domains: macro-regime-v1,
natural-gas-v1, ai-regime-v1, sovereign-debt-v1, credit-cycle-v1, energy-regime-v1,
labor-market-v1, crypto-regime-v1, geopolitics-v1, and sf-urban-v1.

Art-market articles are ingested with `--domain art`, which marks them as `prose_text`
and preserves semantic scoring for that corpus while keeping structured evidence
deterministic.

**Semantic prompt compaction** (implemented 2026-05-30) reduced per-call input tokens
by ~430 tokens (~26% reduction) by removing the redundant per-concept response schema
from user messages while preserving JSON output schema compatibility.

**Shadow prefilter** runs in read-only mode alongside semantic scoring, reporting which
evidence/concept pairs would be skipped by a future lexical prefilter without actually
skipping any scoring calls. Check `assignment_router.shadow_prefilter` in the scored
evidence metadata for savings estimates.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest                    # unit tests only (no API calls)
pytest -m live            # includes live API tests (requires FIREWORKS_API_KEY)
```

## Configuration

Edit `configs/induction_config.yaml` to change model, batch size, and thresholds.

Key promotion settings:

```yaml
concepts:
  promotion_confidence: 0.75    # min LLM confidence to promote to active
  min_supporting_evidence: 2    # min evidence records required
  max_active_concepts: 30       # hard cap on active concept count
```

## CLI Reference

```
poea ingest           Load and normalize evidence records
poea induce           Induce candidate concepts from evidence using an LLM
poea consolidate      Build concept registry and select active concepts
poea registry promote Re-apply promotion rules to registry (threshold tuning)
poea score-evidence   Assign evidence against active concepts via deterministic/semantic routing
poea export-nodes     Export active concepts as POE-compatible node objects
poea run-backend      Run a structure-learning backend (--backend null|poe)
poea pipeline         Run evidence → concepts → registry → scoring → backend → report
poea report           Regenerate run_report.md from existing artifacts
```

## Report Sections

`poea pipeline --backend poe` produces `artifacts/run_report.md` with:

| Section | Source |
|---------|--------|
| Run Summary | POE-A artifact counts |
| Concept Registry | POE-A registry |
| Evidence Scoring Summary | POE-A scorer |
| Routing and Cost Summary | POE-A router + shadow prefilter |
| Assignments Per Concept | POE-A scorer |
| Sample Scorer Outputs | POE-A scorer |
| Graph Summary | Old POE `engine.learn()` |
| **Posterior Inference** | Old POE `engine.query()` → pgmpy VariableElimination |
| **Variable Uncertainty Ranking** | Arithmetic over old POE posteriors |
| **Structure Diagnostics** | Old POE `build_structure_diagnostics()` → BIC decomposition |
| **Evidence Entropy and MI** | Old POE `build_entropy_diagnostics()` |
| Backend Candidates | Old POE population |

Bold sections surface old POE epistemic information. No new inference is computed
in POE-A; all computation is delegated to old POE.

See `POSTERIOR_SURFACE_AUDIT.md` for a complete inventory of available old POE
outputs and `QUERY_TEMPLATE_DESIGN.md` for a framework of useful questions.

## Architecture

```
Evidence (raw text, annotations stripped)
    ↓
Concept Induction (LLM, domain-agnostic prompt)
    ↓
Concept Consolidation + Registry
    ↓
Active Concept Selection (configurable thresholds, hard cap)
    ↓
Assignment Router                     ✓ deterministic/direct/semantic modes
    ↓
Evidence Scoring / Assignment Bridge  ✓ Phase 6 complete
    ↓
Backend Interface + NullBackend       ✓ Phase 7 complete
    ↓
Concept-to-Node Translation           ✓ Phase 8 complete
    ↓
POE Structure Learning                ✓ Phase 9 complete
    ↓
Ontology Graph                        ✓ Phase 10 complete via `poea pipeline`
Run Reports                           ✓ Phase 11 complete via `poea report`
```

See `SPEC.md` and `IMPLEMENTATION_PLAN.md` for full design documentation.
See `SNAPSHOT.md` for current implementation status and architectural divergences.
See `NEXT.md` for the next implementation phase.
# probabilistic_ontology_engine_abductive
