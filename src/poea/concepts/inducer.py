from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from ..evidence.schemas import EvidenceUnit
from ..llm import FireworksClient, LLMClient, is_rate_limit_error
from .prompts import SYSTEM_PROMPT, build_user_message
from .schemas import Concept, InductionBatchResult

logger = logging.getLogger(__name__)

_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_MODEL = "accounts/fireworks/models/deepseek-v4-pro"
_DEFAULT_MAX_RECORDS_PER_BATCH = 10
_RETRY_DELAYS = (2.0, 5.0, 10.0)


@dataclass
class InductionConfig:
    model: str = _DEFAULT_MODEL
    max_records_per_batch: int = _DEFAULT_MAX_RECORDS_PER_BATCH
    min_records_per_batch: int = 5
    max_tokens: int = _DEFAULT_MAX_TOKENS

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InductionConfig":
        models = d.get("models", {})
        batching = d.get("batching", {})
        return cls(
            model=models.get("induction", _DEFAULT_MODEL),
            max_records_per_batch=batching.get("max_records", cls.max_records_per_batch),
            min_records_per_batch=batching.get("min_records", cls.min_records_per_batch),
        )


class ConceptInducer:
    """
    Induces candidate concepts from batches of evidence using an LLM.

    The LLM receives only raw evidence text.  No domain vocabulary,
    ontology node lists, or pre-existing variable names are supplied.

    Any object satisfying the LLMClient protocol may be injected.
    When no client is supplied, a FireworksClient is created from the
    FIREWORKS_API_KEY environment variable.
    """

    def __init__(
        self,
        config: InductionConfig,
        client: LLMClient | None = None,
        debug_responses: bool = False,
    ) -> None:
        self._config = config
        self._debug_responses = debug_responses
        if client is not None:
            self._client = client
        else:
            self._client = FireworksClient.from_env(config.model)

    def induce(self, evidence: list[EvidenceUnit]) -> list[InductionBatchResult]:
        """
        Induce concepts from all evidence units.

        Returns one InductionBatchResult per batch.  Collect all concepts
        via ``[c for r in results for c in r.concepts]``.
        """
        batches = self._make_batches(evidence)
        results: list[InductionBatchResult] = []
        for i, batch in enumerate(batches):
            logger.info(
                "Processing batch %d/%d (%d records)",
                i + 1,
                len(batches),
                len(batch),
            )
            result = self._process_batch(i, batch)
            results.append(result)
            if result.error:
                logger.warning("Batch %d error: %s", i, result.error)
            else:
                logger.info("Batch %d: %d concepts extracted", i, len(result.concepts))
        return results

    # ------------------------------------------------------------------

    def _make_batches(self, evidence: list[EvidenceUnit]) -> list[list[EvidenceUnit]]:
        size = self._config.max_records_per_batch
        return [evidence[i : i + size] for i in range(0, len(evidence), size)]

    def _process_batch(self, index: int, batch: list[EvidenceUnit]) -> InductionBatchResult:
        evidence_ids = [u.evidence_id for u in batch]
        last_error: str | None = None
        last_raw_text: str | None = None

        for attempt, delay in enumerate((*_RETRY_DELAYS, None)):
            try:
                raw_text = self._call_llm(batch)
                last_raw_text = raw_text
                concepts = self._parse_concepts(raw_text, evidence_ids)
                return InductionBatchResult(
                    batch_index=index,
                    evidence_ids=evidence_ids,
                    concepts=concepts,
                    model=self._config.model,
                    raw_response=raw_text if self._debug_responses else None,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if delay is None:
                    break
                if is_rate_limit_error(exc):
                    logger.warning(
                        "Rate limited on batch %d; retrying in %.0fs", index, delay
                    )
                    time.sleep(delay)
                elif attempt < len(_RETRY_DELAYS) - 1:
                    logger.warning(
                        "Batch %d failed (%s); retrying in %.0fs", index, exc, delay
                    )
                    time.sleep(delay)
                else:
                    break

        return InductionBatchResult(
            batch_index=index,
            evidence_ids=evidence_ids,
            concepts=[],
            model=self._config.model,
            error=last_error,
            raw_response=last_raw_text if self._debug_responses else None,
        )

    def _call_llm(self, batch: list[EvidenceUnit]) -> str:
        return self._client.complete(
            system=SYSTEM_PROMPT,
            user=build_user_message(batch),
            max_tokens=self._config.max_tokens,
        )

    def _parse_concepts(self, raw: str, batch_evidence_ids: list[str]) -> list[Concept]:
        """
        Parse LLM response text into a list of Concept objects.

        Handles plain JSON and normalizes citation IDs before validation.
        """
        data = _extract_json(raw)
        if data is None:
            logger.debug("Raw response: %s", raw[:500])
            raise ValueError("LLM response did not contain a complete valid JSON object")

        raw_concepts = data.get("concepts", [])
        if not isinstance(raw_concepts, list):
            raise ValueError("LLM response 'concepts' is not a list")

        valid: list[Concept] = []
        for item in raw_concepts:
            if not isinstance(item, dict):
                continue
            ids = [
                normalized
                for raw_id in item.get("supporting_evidence_ids", [])
                if (normalized := _normalize_evidence_id(raw_id)) in batch_evidence_ids
            ]
            item["supporting_evidence_ids"] = ids
            try:
                valid.append(Concept.model_validate(item))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skipped invalid concept %r: %s", item.get("name"), exc)
        return valid


def _extract_json(text: str) -> dict[str, Any] | None:
    """Try several strategies to pull a JSON object out of a text response."""
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _normalize_evidence_id(value: Any) -> str:
    """Return the raw evidence ID, accepting either raw IDs or EVIDENCE-prefixed tags."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if value.startswith("EVIDENCE-"):
        return value.removeprefix("EVIDENCE-")
    return value
