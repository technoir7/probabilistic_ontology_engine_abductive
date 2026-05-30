"""Tests for evidence normalization — focusing on annotation stripping."""
from __future__ import annotations

from poea.evidence.normalizer import _EXCLUDED_FIELDS, normalize_record
from poea.evidence.schemas import stable_evidence_id


def test_assignments_are_discarded():
    raw = {
        "title": "Test Article",
        "notes": "Some evidence text.",
        "assignments": {"SomeVariable": {"value": True, "confidence": 0.9}},
    }
    unit = normalize_record(raw, source="test.json", domain_tag="test")
    assert "assignments" not in unit.metadata
    assert "assignments" not in unit.model_dump()


def test_causal_claims_are_discarded():
    raw = {
        "title": "Test Article",
        "notes": "Some evidence text.",
        "causal_claims": [{"cause": "A", "effect": "B"}],
    }
    unit = normalize_record(raw, source="test.json", domain_tag="test")
    assert "causal_claims" not in unit.metadata
    assert "causal_claims" not in unit.model_dump()


def test_text_built_from_title_and_notes():
    raw = {
        "title": "Market Report",
        "notes": "Detailed analysis of market conditions.",
        "assignments": {},
    }
    unit = normalize_record(raw, source="test.json", domain_tag="art")
    assert "Market Report" in unit.text
    assert "Detailed analysis" in unit.text


def test_title_only_record_flagged_sparse():
    raw = {"title": "Brief Headline With No Body"}
    unit = normalize_record(raw, source="test.json", domain_tag="art")
    assert unit.text == "Brief Headline With No Body"
    assert unit.metadata.get("sparse_text") is True


def test_record_with_notes_not_sparse():
    raw = {"title": "Article Title", "notes": "Substantial body text here."}
    unit = normalize_record(raw, source="test.json", domain_tag="art")
    assert not unit.metadata.get("sparse_text")


def test_stable_id_deterministic():
    raw = {"title": "Consistent Title", "notes": "Text."}
    unit1 = normalize_record(raw, source="file.json", domain_tag="art")
    unit2 = normalize_record(raw, source="file.json", domain_tag="art")
    assert unit1.evidence_id == unit2.evidence_id


def test_stable_id_varies_with_source():
    raw = {"title": "Same Title", "notes": "Same text."}
    u1 = normalize_record(raw, source="file_a.json", domain_tag="art")
    u2 = normalize_record(raw, source="file_b.json", domain_tag="art")
    assert u1.evidence_id != u2.evidence_id


def test_stable_id_varies_with_title():
    u1 = normalize_record({"title": "Title A"}, source="file.json", domain_tag="art")
    u2 = normalize_record({"title": "Title B"}, source="file.json", domain_tag="art")
    assert u1.evidence_id != u2.evidence_id


def test_metadata_preserves_url():
    raw = {
        "title": "Article",
        "notes": "Text.",
        "url": "https://example.com/article",
        "published_at": "2026-01-01",
        "assignments": {"Var": {"value": True}},
    }
    unit = normalize_record(raw, source="file.json", domain_tag="art")
    assert unit.metadata.get("url") == "https://example.com/article"


def test_domain_tag_preserved():
    raw = {"title": "Article", "notes": "Text."}
    unit = normalize_record(raw, source="file.json", domain_tag="art")
    assert unit.domain_tag == "art"


def test_excluded_fields_constant():
    assert "assignments" in _EXCLUDED_FIELDS
    assert "causal_claims" in _EXCLUDED_FIELDS


def test_no_domain_vocabulary_in_text():
    """Text must not contain values from assignments or causal_claims fields."""
    raw = {
        "title": "Clean Article",
        "notes": "Evidence body text.",
        "assignments": {
            "SecretVariable": {"value": True, "rationale": "secret rationale text"}
        },
        "causal_claims": [{"cause": "A", "effect": "SecretVariable"}],
    }
    unit = normalize_record(raw, source="file.json", domain_tag="art")
    assert "SecretVariable" not in unit.text
    assert "secret rationale text" not in unit.text


# ---------------------------------------------------------------------------
# ID collision tests (the bug this fix addresses)
# ---------------------------------------------------------------------------

def test_same_title_different_notes_produces_different_ids():
    """Two records with identical titles but different body text must not collide."""
    raw_a = {"title": "Shared Title", "notes": "First article body text."}
    raw_b = {"title": "Shared Title", "notes": "Second article body text, different."}
    unit_a = normalize_record(raw_a, source="file.json", domain_tag="art")
    unit_b = normalize_record(raw_b, source="file.json", domain_tag="art")
    assert unit_a.evidence_id != unit_b.evidence_id


def test_identical_content_produces_same_id():
    """Same record loaded twice must produce the same ID."""
    raw = {"title": "Consistent Record", "notes": "Consistent body text."}
    unit_a = normalize_record(raw, source="file.json", domain_tag="art")
    unit_b = normalize_record(raw, source="file.json", domain_tag="art")
    assert unit_a.evidence_id == unit_b.evidence_id


def test_stable_evidence_id_uses_text():
    """stable_evidence_id must differ when text differs, even with same title."""
    id_a = stable_evidence_id("src.json", "Same Title", "First body.")
    id_b = stable_evidence_id("src.json", "Same Title", "Second body.")
    assert id_a != id_b


def test_stable_evidence_id_stable_with_same_inputs():
    id_a = stable_evidence_id("src.json", "Title", "Body text.")
    id_b = stable_evidence_id("src.json", "Title", "Body text.")
    assert id_a == id_b


def test_stable_evidence_id_normalises_whitespace():
    """Leading/trailing whitespace must not change the ID."""
    id_a = stable_evidence_id("src.json", "Title", "Body text.")
    id_b = stable_evidence_id("src.json", "  Title  ", "  Body text.  ")
    assert id_a == id_b


def test_stable_evidence_id_case_insensitive():
    """Case differences must not change the ID."""
    id_a = stable_evidence_id("src.json", "Title", "Body text.")
    id_b = stable_evidence_id("src.json", "TITLE", "BODY TEXT.")
    assert id_a == id_b
