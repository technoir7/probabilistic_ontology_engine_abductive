"""
Prompt templates for evidence scoring (Phase 6).

The scorer asks the LLM: for each active concept, does this evidence record
support it being True, False, or is it neutral?

Compacted 2026-05-30: removed per-call response schema block (saved ~297 tokens/call),
shortened system prompt (saved ~165 tokens/call).  Output schema is preserved; JSON
parsing is unchanged.
"""
from __future__ import annotations

from ..evidence.schemas import EvidenceUnit
from ..registry.schemas import ConceptEntry

SCORER_SYSTEM_PROMPT = """\
You are an evidence analyst. For each concept listed, decide whether the \
evidence supports it being active (True), absent (False), or is neutral.

Concepts are causal mechanisms—active (True) or absent (False) in context.

Verdicts:
- "supports_true": evidence implies concept is active or present
- "supports_false": evidence implies concept is absent or inactive
- "neutral": evidence doesn't address the concept, or is ambiguous

Confidence 0.0–1.0: 0.9+ if the evidence directly addresses the concept; \
prefer "neutral" below 0.4.

Rules: assign every concept a verdict. Don't hedge with "neutral" when \
the evidence clearly supports true or false.
Output: a single compact JSON object. One key per concept name. \
No markdown, no code fences, no prose, no trailing text.\
"""


def build_scorer_user_message(
    evidence: EvidenceUnit,
    concepts: list[ConceptEntry],
) -> str:
    """Build the compact user message for scoring one evidence record against all concepts."""
    evidence_block = evidence.title
    if evidence.text and evidence.text.strip() and evidence.text.strip() != evidence.title.strip():
        evidence_block += f"\n\n{evidence.text}"

    concept_lines = [
        f'  "{c.name}": "{c.definition}"'
        for c in concepts
    ]
    concept_block = "{\n" + ",\n".join(concept_lines) + "\n}"

    return (
        f"[{evidence.evidence_id}] {evidence_block}\n\n"
        f"Concepts:\n{concept_block}\n\n"
        f'JSON (one key per concept, value: {{"verdict": "supports_true|supports_false|neutral", "confidence": N}}):'
    )
