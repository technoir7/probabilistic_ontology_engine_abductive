"""Tests for concept induction — all use mocked LLM, no live API calls."""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest

from poea.concepts.inducer import ConceptInducer, InductionConfig, _extract_json
from poea.concepts.schemas import Concept
from poea.evidence.schemas import EvidenceUnit


def _make_unit(n: int) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=f"ev{n:04d}",
        source="test.json",
        title=f"Evidence Title {n}",
        domain_tag="test",
        text=f"Body text of evidence record {n}.",
    )


def _make_mock_client(response_dict: dict) -> MagicMock:
    client = MagicMock()
    client.complete.return_value = json.dumps(response_dict)
    return client


# ---------------------------------------------------------------------------
# ConceptInducer.induce
# ---------------------------------------------------------------------------

def test_inducer_returns_concepts(mock_llm_client):
    units = [_make_unit(i) for i in range(3)]
    inducer = ConceptInducer(InductionConfig(), client=mock_llm_client)
    results = inducer.induce(units)
    all_concepts = [c for r in results for c in r.concepts]
    assert len(all_concepts) > 0
    assert all(isinstance(c, Concept) for c in all_concepts)


def test_inducer_no_domain_vocabulary_injected():
    """Verify the prompt contains no domain-specific variable names."""
    from poea.concepts.prompts import SYSTEM_PROMPT, build_user_message

    art_vocabulary = [
        "AuthenticityPremium", "BlueChipConcentration", "MarketUncertainty",
        "CollectorFlightToSafety", "AuctionSpeculationElevated", "MarketPolarization",
        "BiennialFatigue", "PrestigeFragmentation", "RegionalSceneMomentum",
        "RitualAuraPremium",
    ]
    units = [_make_unit(i) for i in range(5)]
    user_msg = build_user_message(units)

    for var in art_vocabulary:
        assert var not in SYSTEM_PROMPT, f"Domain variable '{var}' found in system prompt"
        assert var not in user_msg, f"Domain variable '{var}' found in user message"


def test_inducer_batches_correctly():
    units = [_make_unit(i) for i in range(10)]
    mock_client = _make_mock_client({"concepts": []})
    config = InductionConfig(max_records_per_batch=3)
    inducer = ConceptInducer(config, client=mock_client)
    results = inducer.induce(units)
    assert len(results) == 4
    assert mock_client.complete.call_count == 4


def test_inducer_evidence_ids_restricted_to_batch():
    """Concepts' supporting_evidence_ids must only reference IDs in the current batch."""
    response = {
        "concepts": [
            {
                "name": "TestConcept",
                "definition": "A test concept.",
                "confidence": 0.8,
                "supporting_evidence_ids": ["ev0000", "ev0001", "ev9999"],
            }
        ]
    }
    mock_client = _make_mock_client(response)
    units = [_make_unit(0), _make_unit(1)]
    inducer = ConceptInducer(InductionConfig(), client=mock_client)
    results = inducer.induce(units)
    concepts = results[0].concepts
    assert len(concepts) == 1
    assert "ev9999" not in concepts[0].supporting_evidence_ids
    assert "ev0000" in concepts[0].supporting_evidence_ids


def test_inducer_normalizes_evidence_prefixed_ids():
    response = {
        "concepts": [
            {
                "name": "PrefixedCitationConcept",
                "definition": "A test concept with prefixed evidence citations.",
                "confidence": 0.8,
                "supporting_evidence_ids": ["EVIDENCE-ev0000", "ev0001", "EVIDENCE-ev9999"],
            }
        ]
    }
    mock_client = _make_mock_client(response)
    units = [_make_unit(0), _make_unit(1)]
    inducer = ConceptInducer(InductionConfig(), client=mock_client)
    results = inducer.induce(units)

    assert results[0].error is None
    assert results[0].concepts[0].supporting_evidence_ids == ["ev0000", "ev0001"]


def test_inducer_handles_empty_concept_list():
    mock_client = _make_mock_client({"concepts": []})
    inducer = ConceptInducer(InductionConfig(), client=mock_client)
    results = inducer.induce([_make_unit(0)])
    assert results[0].concepts == []
    assert results[0].error is None


def test_inducer_reports_invalid_json_response(monkeypatch):
    client = MagicMock()
    client.complete.return_value = "This is not JSON at all."
    monkeypatch.setattr("poea.concepts.inducer.time.sleep", lambda _: None)

    inducer = ConceptInducer(InductionConfig(), client=client)
    results = inducer.induce([_make_unit(0)])

    assert results[0].concepts == []
    assert results[0].error is not None
    assert "valid JSON" in results[0].error
    assert client.complete.call_count > 1


def test_inducer_reports_truncated_json_response(monkeypatch):
    client = MagicMock()
    client.complete.return_value = '{"concepts": [{"name": "Broken"'
    monkeypatch.setattr("poea.concepts.inducer.time.sleep", lambda _: None)

    inducer = ConceptInducer(InductionConfig(), client=client)
    results = inducer.induce([_make_unit(0)])

    assert results[0].concepts == []
    assert results[0].error is not None
    assert "valid JSON" in results[0].error


def test_inducer_preserves_debug_response_on_parse_failure(monkeypatch):
    raw_response = '{"concepts": [{"name": "Broken"'
    client = MagicMock()
    client.complete.return_value = raw_response
    monkeypatch.setattr("poea.concepts.inducer.time.sleep", lambda _: None)

    inducer = ConceptInducer(InductionConfig(), client=client, debug_responses=True)
    results = inducer.induce([_make_unit(0)])

    assert results[0].error is not None
    assert results[0].raw_response == raw_response


def test_inducer_preserves_debug_response_on_success():
    response = {"concepts": [{"name": "DebugConcept", "definition": "D.", "confidence": 0.5}]}
    raw_response = json.dumps(response)
    client = MagicMock()
    client.complete.return_value = raw_response

    inducer = ConceptInducer(InductionConfig(), client=client, debug_responses=True)
    results = inducer.induce([_make_unit(0)])

    assert results[0].error is None
    assert results[0].raw_response == raw_response


def test_inducer_handles_json_in_markdown_fence():
    response_json = {"concepts": [{"name": "FenceTest", "definition": "D.", "confidence": 0.5}]}
    client = MagicMock()
    client.complete.return_value = f"Here is the output:\n```json\n{json.dumps(response_json)}\n```"
    inducer = ConceptInducer(InductionConfig(), client=client)
    results = inducer.induce([_make_unit(0)])
    assert any(c.name == "FenceTest" for c in results[0].concepts)


def test_inducer_skips_invalid_concepts():
    response = {
        "concepts": [
            {"name": "ValidConcept", "definition": "Good.", "confidence": 0.8},
            {"name": "", "definition": "Missing name.", "confidence": 0.5},
            {"name": "MissingDef", "definition": "", "confidence": 0.5},
        ]
    }
    mock_client = _make_mock_client(response)
    inducer = ConceptInducer(InductionConfig(), client=mock_client)
    results = inducer.induce([_make_unit(0)])
    names = [c.name for c in results[0].concepts]
    assert "ValidConcept" in names
    assert "" not in names


def test_inducer_records_model_name():
    mock_client = _make_mock_client({"concepts": []})
    config = InductionConfig(model="accounts/fireworks/models/test-model")
    inducer = ConceptInducer(config, client=mock_client)
    results = inducer.induce([_make_unit(0)])
    assert results[0].model == "accounts/fireworks/models/test-model"


def test_inducer_error_captured_on_exception():
    """Exceptions from the LLM client are captured in result.error."""
    client = MagicMock()
    client.complete.side_effect = Exception("Simulated connection failure")

    import poea.concepts.inducer as inducer_mod
    orig_sleep = inducer_mod.time.sleep
    inducer_mod.time.sleep = lambda _: None
    try:
        inducer = ConceptInducer(InductionConfig(), client=client)
        results = inducer.induce([_make_unit(0)])
    finally:
        inducer_mod.time.sleep = orig_sleep

    assert results[0].concepts == []
    assert results[0].error is not None


def test_inducer_retries_on_rate_limit():
    """Rate-limit errors trigger retry logic; call_count should exceed 1."""
    import openai

    client = MagicMock()
    client.complete.side_effect = openai.RateLimitError(
        "rate limited", response=MagicMock(status_code=429), body={}
    )

    import poea.concepts.inducer as inducer_mod
    orig_sleep = inducer_mod.time.sleep
    inducer_mod.time.sleep = lambda _: None
    try:
        inducer = ConceptInducer(InductionConfig(), client=client)
        results = inducer.induce([_make_unit(0)])
    finally:
        inducer_mod.time.sleep = orig_sleep

    assert results[0].error is not None
    assert client.complete.call_count > 1


def test_inducer_complete_called_with_system_and_user():
    """Verify complete() is called with system and user kwargs."""
    mock_client = _make_mock_client({"concepts": []})
    inducer = ConceptInducer(InductionConfig(), client=mock_client)
    inducer.induce([_make_unit(0)])
    call_kwargs = mock_client.complete.call_args
    assert "system" in call_kwargs.kwargs or len(call_kwargs.args) >= 2


def test_inducer_no_anthropic_import():
    """The inducer module must not import anthropic."""
    import poea.concepts.inducer as m

    assert "anthropic" not in dir(m)
    # anthropic must not be in the module's namespace at all
    assert not hasattr(m, "anthropic")


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------

def test_extract_json_plain():
    assert _extract_json('{"concepts": []}') == {"concepts": []}


def test_extract_json_with_preamble():
    text = 'Sure, here is the JSON:\n{"concepts": [{"name": "X"}]}'
    result = _extract_json(text)
    assert result is not None
    assert "concepts" in result


def test_extract_json_from_fence():
    assert _extract_json('```json\n{"concepts": []}\n```') == {"concepts": []}


def test_extract_json_fence_no_lang():
    assert _extract_json('```\n{"concepts": []}\n```') == {"concepts": []}


def test_extract_json_returns_none_for_garbage():
    assert _extract_json("completely invalid text with no json") is None


def test_extract_json_returns_none_for_empty():
    assert _extract_json("") is None


# ---------------------------------------------------------------------------
# Live induction smoke test — skipped unless FIREWORKS_API_KEY is set
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("FIREWORKS_API_KEY"),
    reason="FIREWORKS_API_KEY not set",
)
def test_live_induction_smoke():
    """
    Minimal live smoke test: verify the inducer can call Fireworks and
    return at least one parseable Concept from a small evidence batch.

    Run with:  pytest -m live tests/test_concept_inducer.py::test_live_induction_smoke
    """
    from pathlib import Path

    from poea.evidence.loaders import load_from_path

    art_path = Path("../art-market-domain/data/manual_ingest_split")
    if not art_path.exists():
        pytest.skip("Art domain evidence not available")

    units = load_from_path(art_path, domain_tag="art")[:5]
    config = InductionConfig(
        model="accounts/fireworks/models/deepseek-v4-pro",
        max_records_per_batch=5,
    )
    inducer = ConceptInducer(config)
    results = inducer.induce(units)

    assert len(results) == 1
    assert results[0].error is None, f"Induction error: {results[0].error}"
    assert len(results[0].concepts) > 0, "Expected at least one concept from 5 evidence records"

    for c in results[0].concepts:
        assert c.name
        assert c.definition
        assert 0.0 <= c.confidence <= 1.0
