from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Concept(BaseModel):
    name: str
    definition: str
    confidence: float
    supporting_evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @field_validator("name")
    @classmethod
    def name_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Concept name must not be empty")
        return v

    @field_validator("definition")
    @classmethod
    def definition_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Concept definition must not be empty")
        return v


class InductionBatchResult(BaseModel):
    batch_index: int
    evidence_ids: list[str]
    concepts: list[Concept]
    model: str
    error: str | None = None
    raw_response: str | None = None
