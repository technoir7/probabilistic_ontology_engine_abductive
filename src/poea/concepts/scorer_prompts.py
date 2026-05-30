"""
Prompt templates for evidence scoring (Phase 6).

The scorer asks the LLM: for each active concept, does this evidence record
support it being True, False, or is it neutral?
"""
from __future__ import annotations

from ..evidence.schemas import EvidenceUnit
from ..registry.schemas import ConceptEntry

SCORER_SYSTEM_PROMPT = """\
You are an evidence analyst. Your task is to evaluate whether a piece of \
evidence supports, contradicts, or is neutral toward each of a set of \
candidate concepts.

A concept is a causal mechanism or structural force that can be active (True) \
or absent (False) in a given context.

For each concept, determine exactly one verdict:
- "supports_true": the evidence is consistent with or implies this concept \
being active or present in this context
- "supports_false": the evidence implies this concept is absent or inactive \
in this context
- "neutral": the evidence does not address this concept, or is ambiguous

For each verdict also provide a confidence score from 0.0 to 1.0:
- 0.9–1.0: the evidence directly and explicitly addresses this concept
- 0.7–0.8: the evidence is clearly consistent with this verdict
- 0.5–0.6: the evidence weakly implies this verdict
- 0.0–0.4: the concept is barely touched; prefer "neutral" here

Rules:
- Assign a verdict to every concept listed.
- Use "neutral" when the evidence simply does not mention or imply the concept.
- Do not hedge with "neutral" when the evidence clearly supports true or false.
- Output compact valid JSON only. No markdown. No prose. No code fences. \
No trailing text. The entire response must be a single JSON object.\
"""


def build_scorer_user_message(
    evidence: EvidenceUnit,
    concepts: list[ConceptEntry],
) -> str:
    """Build the user message for scoring a single evidence record against all concepts."""
    evidence_block = f"Title: {evidence.title}"
    if evidence.text and evidence.text.strip() and evidence.text.strip() != evidence.title.strip():
        evidence_block += f"\n\n{evidence.text}"

    concept_lines = [
        f'  "{c.name}": "{c.definition}"'
        for c in concepts
    ]
    concept_block = "{\n" + ",\n".join(concept_lines) + "\n}"

    schema_lines = ",\n".join(
        f'  "{c.name}": {{"verdict": "supports_true | supports_false | neutral", "confidence": 0.0}}'
        for c in concepts
    )
    schema_block = "{\n" + schema_lines + "\n}"

    return (
        f"Evidence record [ID: {evidence.evidence_id}]:\n"
        f"{evidence_block}\n\n"
        f"---\n\n"
        f"Concepts to evaluate:\n{concept_block}\n\n"
        f"---\n\n"
        f"Return this exact JSON structure with one entry per concept name:\n"
        f"{schema_block}"
    )
