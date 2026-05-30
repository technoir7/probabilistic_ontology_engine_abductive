from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field


class EvidenceUnit(BaseModel):
    evidence_id: str
    source: str
    title: str
    published_at: str | None = None
    domain_tag: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def stable_evidence_id(source: str, title: str, text: str = "") -> str:
    """
    Deterministic 16-char hex ID derived from source, title, and full text.

    Using the full text (not just title) prevents ID collisions when two records
    from the same source share an identical title but have different content.
    All three inputs are normalised (stripped, lowercased) before hashing so
    that minor whitespace variation does not produce different IDs.
    """
    normalized = (
        f"{source.strip().lower()}"
        f":{title.strip().lower()}"
        f":{text.strip().lower()}"
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
