from __future__ import annotations

from ..evidence.schemas import EvidenceUnit

SYSTEM_PROMPT = """\
You are an epistemic analyst. Your task is to identify candidate explanatory concepts \
from a set of evidence documents.

A concept is a MECHANISM, FORCE, or STRUCTURAL FACTOR that drives or constrains other \
phenomena. A concept is NOT a topic label or a description of what the documents are about.

A good concept:
- Appears across multiple documents (not specific to one event)
- Explains WHY something happens, not just WHAT happened
- Could be True or False for a given time period or context
- Has causal power: its presence or absence changes outcomes
- Is precise enough to be operationally defined

Examples of the TYPE of concept to find (these are generic patterns, not answers):
- Demand compression in a specific market tier
- Information asymmetry between buyers and sellers
- Liquidity constraints driven by macro conditions
- Flight-to-quality concentration in high-certainty assets
- Institutional validation as a pricing mechanism
- Speculation premium over intrinsic-value pricing

Avoid:
- Labels that name the domain you are studying (e.g., the name of the field)
- Proper nouns for specific people, companies, or events unless they represent a \
reusable structural mechanism
- Descriptions of individual events or outcomes
- Vague abstractions without causal content (e.g., "market dynamics")
- Synonyms of concepts you have already identified in this batch

For each concept you identify, provide:
- name: 2–4 words, CamelCase, specific and precise
- definition: 2–3 sentences. What is it? How does it work? What does it cause or enable?
- confidence: 0.0–1.0. How consistently and strongly does this concept appear \
across the evidence? Higher if it appears in many documents and is clearly causal.
- supporting_evidence_ids: list of exact evidence_id strings copied from the \
evidence records. Do not add prefixes. Do not use [EVIDENCE-xxx] tag text.

Output requirements:
- Return compact valid JSON only.
- The entire response must parse with json.loads.
- No markdown.
- No prose outside JSON.
- No trailing commentary.
- No code fences.
- No ellipses or incomplete objects.
- Use only exact evidence_id strings from the evidence records in \
supporting_evidence_ids.
\
"""

_RESPONSE_SCHEMA = """\
{
  "concepts": [
    {
      "name": "ConceptName",
      "definition": "Clear explanation of the concept and its causal role.",
      "confidence": 0.75,
      "supporting_evidence_ids": ["evidence_id_1", "evidence_id_2"]
    }
  ]
}\
"""


def format_evidence_batch(batch: list[EvidenceUnit]) -> str:
    """Format a list of EvidenceUnit objects into the evidence block for the prompt."""
    sections: list[str] = []
    for unit in batch:
        section = (
            f"[EVIDENCE-{unit.evidence_id}]\n"
            f"evidence_id: {unit.evidence_id}\n"
            f"Title: {unit.title}"
        )
        if unit.published_at:
            section += f"\nPublished: {unit.published_at}"
        if unit.text and unit.text.strip() != unit.title.strip():
            section += f"\n\n{unit.text}"
        sections.append(section)
    return "\n\n---\n\n".join(sections)


def build_user_message(batch: list[EvidenceUnit]) -> str:
    evidence_block = format_evidence_batch(batch)
    return (
        f"Evidence documents:\n\n{evidence_block}\n\n"
        "Return exactly one compact JSON object using this structure. "
        "Do not include markdown, prose, comments, code fences, or text after the JSON:\n"
        f"{_RESPONSE_SCHEMA}"
    )
