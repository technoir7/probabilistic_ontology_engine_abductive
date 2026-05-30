from __future__ import annotations

from typing import Any

from .schemas import EvidenceUnit, stable_evidence_id

# Fields that encode pre-existing vocabulary and must never reach concept induction.
_EXCLUDED_FIELDS = frozenset({"assignments", "causal_claims"})

# Fields whose values are pulled into the evidence text.
_TEXT_FIELDS = ("notes", "text", "content", "body", "summary")


def normalize_record(
    raw: dict[str, Any],
    source: str,
    domain_tag: str,
) -> EvidenceUnit:
    """
    Convert a raw evidence dict into an EvidenceUnit.

    Discards all fields in _EXCLUDED_FIELDS.  Only raw text fields
    (title, notes, text, content, …) become the evidence text.
    """
    title = str(raw.get("title") or "").strip()

    text_parts: list[str] = [title] if title else []
    for field in _TEXT_FIELDS:
        value = str(raw.get(field) or "").strip()
        if value and value != title:
            text_parts.append(value)

    text = "\n\n".join(text_parts)

    # Preserve non-excluded, non-text fields as metadata for reference.
    skip = _EXCLUDED_FIELDS | {"title"} | set(_TEXT_FIELDS)
    metadata: dict[str, Any] = {k: v for k, v in raw.items() if k not in skip}
    if not text_parts[1:]:
        # Flag title-only records so callers can weight them appropriately.
        metadata["sparse_text"] = True

    return EvidenceUnit(
        evidence_id=stable_evidence_id(source, title, text),
        source=source,
        title=title,
        published_at=raw.get("published_at"),
        domain_tag=domain_tag,
        text=text,
        metadata=metadata,
    )
