# Next: Phase 8 — Concept-to-Node Translation

---

## Objective

Translate active concepts from the registry into POE-compatible node objects.

This is a translation/export layer. The POE adapter (Phase 9) will consume these
nodes to build POE `Variable` objects. The format must match POE's expected node
schema.

---

## Inputs Available

| Input | Location | Status |
|-------|----------|--------|
| Active concept set | `artifacts/canonical_concepts.json` | Ready (11 concepts) |
| Backend interface | `src/poea/backends/interface.py` | Ready (Phase 7) |
| NullBackend | `src/poea/backends/null_backend.py` | Ready (Phase 7) |

---

## What Phase 8 Must Produce

### Node artifact format (`artifacts/nodes.json`)

```json
{
  "domain_tag": "art",
  "node_count": 11,
  "nodes": [
    {
      "name": "AuctionCatalystEffect",
      "definition": "...",
      "prior_probability": 0.5,
      "boolean_state": null,
      "source": "poea_induced"
    }
  ]
}
```

### Exporter module — `src/poea/artifacts/exporters.py`

Function to convert active `ConceptEntry` objects into node dicts.

### CLI command

```bash
poea export-nodes \
  --concepts artifacts/canonical_concepts.json \
  --output artifacts/nodes.json \
  [--domain art]
```

Note: the spec uses `--db artifacts/poea_registry.sqlite` but we use `--concepts`
to match the current JSON-based architecture.

---

## Implementation Tasks

1. Create `src/poea/artifacts/` directory with `__init__.py`
2. Implement `src/poea/artifacts/exporters.py`
   - `concepts_to_nodes(concepts, domain_tag) -> list[dict]`
   - Node fields: `name`, `definition`, `prior_probability=0.5`, `boolean_state=None`, `source="poea_induced"`
3. Add `poea export-nodes` CLI command
4. Add tests — `tests/test_export_nodes.py`

---

## Exit Criteria (from IMPLEMENTATION_PLAN.md Phase 8)

- Active concepts export as nodes
- No hardcoded art variables (domain-agnostic)
- `prior_probability = 0.5` for all induced nodes
- `boolean_state = null` for all induced nodes

---

## Phase 8 Unblocks

Phase 9 (POE Adapter) consumes `nodes.json` to build `Variable` objects for POE.
The POE adapter also needs the scored evidence from Phase 6.

After Phase 8, all inputs for Phase 9 will be available:
- `artifacts/nodes.json` — induced concept nodes
- `artifacts/scored_evidence.json` — concept assignments per evidence record
