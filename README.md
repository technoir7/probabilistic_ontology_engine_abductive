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

# Score evidence against active concepts (Assignment Bridge)
poea score-evidence --concepts artifacts/canonical_concepts.json --evidence artifacts/evidence.json --output artifacts/scored_evidence.json --verbose

# Export nodes and run a backend manually
poea export-nodes --concepts artifacts/canonical_concepts.json --output artifacts/nodes.json --domain art
poea run-backend --backend poe --concepts artifacts/canonical_concepts.json --scored-evidence artifacts/scored_evidence.json --output artifacts/poea_graph.json
```

## LLM Provider

Default provider: **Fireworks AI**
Default model: `accounts/fireworks/models/deepseek-v4-pro`
Required env var: `FIREWORKS_API_KEY`

The LLM client is provider-agnostic. `FireworksClient` uses Fireworks' OpenAI-compatible
endpoint. To use a different OpenAI-compatible provider, subclass or replace `FireworksClient`
in `src/poea/llm.py`.

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
poea score-evidence   Score evidence against active concepts (Assignment Bridge)
poea export-nodes     Export active concepts as POE-compatible node objects
poea run-backend      Run a structure-learning backend (--backend null|poe)
poea pipeline         Run evidence → concepts → registry → scoring → backend → report
```

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
Evidence Scoring / Assignment Bridge  ✓ Phase 6 complete
    ↓
Backend Interface + NullBackend       ✓ Phase 7 complete
    ↓
Concept-to-Node Translation           ✓ Phase 8 complete
    ↓
POE Structure Learning                ✓ Phase 9 complete
    ↓
Ontology Graph                        ✓ Phase 10 complete via `poea pipeline`
```

See `SPEC.md` and `IMPLEMENTATION_PLAN.md` for full design documentation.
See `SNAPSHOT.md` for current implementation status and architectural divergences.
See `NEXT.md` for the next implementation phase.
# probabilistic_ontology_engine_abductive
