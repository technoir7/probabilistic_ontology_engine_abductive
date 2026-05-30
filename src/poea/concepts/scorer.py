"""
Evidence Scoring (Assignment Bridge) — Phase 6.

Translates normalized evidence records into concept-keyed boolean assignments.
For each evidence record, all active concepts are batched into a single LLM
call to minimise API cost.

Verdict mapping:
    supports_true  → assigned_value=True,  missingness=OBSERVED
                     (SOFT_OBSERVED if confidence < soft_observed_threshold)
    supports_false → assigned_value=False, missingness=OBSERVED
                     (SOFT_OBSERVED if confidence < soft_observed_threshold)
    neutral        → assigned_value=None,  missingness=MISSING

Results are cached in scored_evidence.json.  On re-runs, any evidence record
whose scored concept set is a superset of the current active concept set is
returned from cache without a new LLM call.  Records with a partial cache
(new concepts added since last run) are re-scored in full.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ..evidence.schemas import EvidenceUnit
from ..llm import FireworksClient, LLMClient, is_rate_limit_error
from ..registry.schemas import ConceptEntry

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "accounts/fireworks/models/deepseek-v4-pro"
_DEFAULT_MAX_TOKENS = 2048
_DEFAULT_SOFT_OBSERVED_THRESHOLD = 0.5
_RETRY_DELAYS = (2.0, 5.0, 10.0)

Missingness = Literal["OBSERVED", "SOFT_OBSERVED", "MISSING"]
Verdict = Literal["supports_true", "supports_false", "neutral"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConceptAssignment(BaseModel):
    concept_id: str
    variable_name: str
    assigned_value: bool | None  # True / False / None (neutral)
    confidence: float
    missingness: Missingness

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ScoredRecord(BaseModel):
    evidence_id: str
    assignments: list[ConceptAssignment]
    error: str | None = None  # populated when LLM call or parse fails


class ScoringStats(BaseModel):
    total_records: int
    scored: int
    cache_hits: int
    errors: int
    total_pairs: int
    by_concept: dict[str, dict[str, int]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ScoringConfig:
    model: str = _DEFAULT_MODEL
    max_tokens: int = _DEFAULT_MAX_TOKENS
    soft_observed_threshold: float = _DEFAULT_SOFT_OBSERVED_THRESHOLD

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScoringConfig":
        models = d.get("models", {})
        scoring_cfg = d.get("scoring", {})
        return cls(
            model=models.get("scoring", models.get("induction", _DEFAULT_MODEL)),
            max_tokens=scoring_cfg.get("max_tokens", _DEFAULT_MAX_TOKENS),
            soft_observed_threshold=scoring_cfg.get(
                "soft_observed_threshold", _DEFAULT_SOFT_OBSERVED_THRESHOLD
            ),
        )


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class EvidenceScorer:
    """
    Scores each evidence record against all active concepts in one LLM call.

    Any object satisfying the LLMClient protocol may be injected.
    When no client is supplied, a FireworksClient is built from the
    FIREWORKS_API_KEY environment variable.
    """

    def __init__(
        self,
        config: ScoringConfig,
        client: LLMClient | None = None,
    ) -> None:
        self._config = config
        self._client = client if client is not None else FireworksClient.from_env(config.model)

    def score_all(
        self,
        evidence: list[EvidenceUnit],
        concepts: list[ConceptEntry],
        existing_records: list[ScoredRecord] | None = None,
    ) -> tuple[list[ScoredRecord], ScoringStats]:
        """
        Score all evidence records against all active concepts.

        Records where every active concept is already scored (cache hit) are
        returned without an LLM call.  Records with a partial or absent cache
        entry are scored in full.

        Returns ``(scored_records, stats)``.
        """
        existing_by_id: dict[str, ScoredRecord] = {}
        if existing_records:
            existing_by_id = {r.evidence_id: r for r in existing_records}

        active_concept_ids = {c.concept_id for c in concepts}

        result: list[ScoredRecord] = []
        stats = ScoringStats(
            total_records=len(evidence),
            scored=0,
            cache_hits=0,
            errors=0,
            total_pairs=len(evidence) * len(concepts),
        )

        for ev in evidence:
            existing = existing_by_id.get(ev.evidence_id)
            if existing is not None:
                cached_ids = {a.concept_id for a in existing.assignments}
                if active_concept_ids <= cached_ids:
                    result.append(existing)
                    stats.cache_hits += 1
                    _accumulate_stats(stats, existing, concepts)
                    continue

            scored = self._score_record_with_retry(ev, concepts)
            result.append(scored)
            if scored.error:
                stats.errors += 1
            else:
                stats.scored += 1
            _accumulate_stats(stats, scored, concepts)

        return result, stats

    # ------------------------------------------------------------------

    def _score_record_with_retry(
        self,
        evidence: EvidenceUnit,
        concepts: list[ConceptEntry],
    ) -> ScoredRecord:
        last_error: str | None = None

        for attempt, delay in enumerate((*_RETRY_DELAYS, None)):
            try:
                raw = self._call_llm(evidence, concepts)
                assignments = self._parse_response(raw, concepts)
                return ScoredRecord(evidence_id=evidence.evidence_id, assignments=assignments)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if delay is None:
                    break
                if is_rate_limit_error(exc):
                    logger.warning(
                        "Rate limited scoring %s; retrying in %.0fs",
                        evidence.evidence_id,
                        delay,
                    )
                    time.sleep(delay)
                elif attempt < len(_RETRY_DELAYS) - 1:
                    logger.warning(
                        "Scoring %s failed (%s); retrying in %.0fs",
                        evidence.evidence_id,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    break

        logger.error("Failed to score %s after retries: %s", evidence.evidence_id, last_error)
        return ScoredRecord(
            evidence_id=evidence.evidence_id,
            assignments=_neutral_assignments(concepts),
            error=last_error,
        )

    def _call_llm(self, evidence: EvidenceUnit, concepts: list[ConceptEntry]) -> str:
        from .scorer_prompts import SCORER_SYSTEM_PROMPT, build_scorer_user_message

        return self._client.complete(
            system=SCORER_SYSTEM_PROMPT,
            user=build_scorer_user_message(evidence, concepts),
            max_tokens=self._config.max_tokens,
        )

    def _parse_response(
        self,
        raw: str,
        concepts: list[ConceptEntry],
    ) -> list[ConceptAssignment]:
        """
        Parse LLM response JSON into ConceptAssignment objects.

        Concepts absent from the response default to neutral/MISSING.
        Extra keys in the response are ignored.
        Raises ValueError if the response contains no parseable JSON.
        """
        data = _extract_json_object(raw)
        if data is None:
            raise ValueError(
                f"LLM response contained no parseable JSON: {raw[:300]!r}"
            )

        assignments: list[ConceptAssignment] = []
        for concept in concepts:
            raw_verdict = data.get(concept.name, {})
            if not isinstance(raw_verdict, dict):
                raw_verdict = {}

            verdict_str = str(raw_verdict.get("verdict", "neutral"))
            raw_conf = raw_verdict.get("confidence", 0.0)
            try:
                confidence = float(raw_conf)
            except (TypeError, ValueError):
                confidence = 0.0

            assignments.append(
                _build_assignment(
                    concept=concept,
                    verdict_str=verdict_str,
                    confidence=confidence,
                    soft_threshold=self._config.soft_observed_threshold,
                )
            )

        return assignments


# ---------------------------------------------------------------------------
# Pure helpers (also exported for unit testing)
# ---------------------------------------------------------------------------

def _build_assignment(
    concept: ConceptEntry,
    verdict_str: str,
    confidence: float,
    soft_threshold: float,
) -> ConceptAssignment:
    """Map a raw LLM verdict string to a ConceptAssignment."""
    confidence = max(0.0, min(1.0, confidence))

    if verdict_str == "supports_true":
        assigned_value: bool | None = True
        missingness: Missingness = (
            "SOFT_OBSERVED" if confidence < soft_threshold else "OBSERVED"
        )
    elif verdict_str == "supports_false":
        assigned_value = False
        missingness = (
            "SOFT_OBSERVED" if confidence < soft_threshold else "OBSERVED"
        )
    else:
        assigned_value = None
        missingness = "MISSING"

    return ConceptAssignment(
        concept_id=concept.concept_id,
        variable_name=concept.name,
        assigned_value=assigned_value,
        confidence=confidence,
        missingness=missingness,
    )


def _neutral_assignments(concepts: list[ConceptEntry]) -> list[ConceptAssignment]:
    """Return all-neutral assignments — used as a fallback when scoring fails."""
    return [
        ConceptAssignment(
            concept_id=c.concept_id,
            variable_name=c.name,
            assigned_value=None,
            confidence=0.0,
            missingness="MISSING",
        )
        for c in concepts
    ]


def _accumulate_stats(
    stats: ScoringStats,
    record: ScoredRecord,
    concepts: list[ConceptEntry],
) -> None:
    concept_id_to_name = {c.concept_id: c.name for c in concepts}
    for a in record.assignments:
        name = concept_id_to_name.get(a.concept_id, a.variable_name)
        bucket = stats.by_concept.setdefault(name, {"true": 0, "false": 0, "neutral": 0})
        if a.assigned_value is True:
            bucket["true"] += 1
        elif a.assigned_value is False:
            bucket["false"] += 1
        else:
            bucket["neutral"] += 1


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first valid JSON object from an LLM text response."""
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def load_scored_evidence(path: str | Path) -> list[ScoredRecord]:
    """
    Load existing scored records from a scored_evidence.json artifact.

    Returns an empty list if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    return [ScoredRecord.model_validate(r) for r in data.get("scored_records", [])]


def save_scored_evidence(
    path: str | Path,
    records: list[ScoredRecord],
    stats: ScoringStats,
    metadata: dict[str, Any],
) -> None:
    """Write scored records and summary to a scored_evidence.json artifact."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": metadata,
                "summary": stats.model_dump(),
                "scored_records": [r.model_dump() for r in records],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
