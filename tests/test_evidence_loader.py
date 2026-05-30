"""Tests for evidence loading from files and directories."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from poea.evidence.loaders import load_from_path
from poea.evidence.schemas import EvidenceUnit


def _write_json(path: Path, data) -> None:
    with path.open("w") as f:
        json.dump(data, f)


def test_load_single_file_array(annotated_evidence_path):
    units = load_from_path(annotated_evidence_path, domain_tag="art")
    assert len(units) == 3
    assert all(isinstance(u, EvidenceUnit) for u in units)


def test_load_assigns_domain_tag(annotated_evidence_path):
    units = load_from_path(annotated_evidence_path, domain_tag="finance")
    assert all(u.domain_tag == "finance" for u in units)


def test_load_strips_annotations(annotated_evidence_path):
    units = load_from_path(annotated_evidence_path, domain_tag="art")
    for u in units:
        assert "assignments" not in u.metadata
        assert "causal_claims" not in u.metadata


def test_load_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _write_json(d / "file1.json", [{"title": "Record One", "notes": "Body one."}])
        _write_json(d / "file2.json", [{"title": "Record Two", "notes": "Body two."}])
        units = load_from_path(d, domain_tag="test")
    assert len(units) == 2
    titles = {u.title for u in units}
    assert "Record One" in titles
    assert "Record Two" in titles


def test_load_single_object_file():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"title": "Single Object", "notes": "Text."}, f)
        path = Path(f.name)
    try:
        units = load_from_path(path, domain_tag="test")
        assert len(units) == 1
        assert units[0].title == "Single Object"
    finally:
        path.unlink()


def test_records_missing_title_are_skipped():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump([
            {"title": "Valid Record", "notes": "Text."},
            {"notes": "No title here."},
        ], f)
        path = Path(f.name)
    try:
        units = load_from_path(path, domain_tag="test")
        assert len(units) == 1
        assert units[0].title == "Valid Record"
    finally:
        path.unlink()


def test_evidence_ids_are_stable_across_loads(annotated_evidence_path):
    units1 = load_from_path(annotated_evidence_path, domain_tag="art")
    units2 = load_from_path(annotated_evidence_path, domain_tag="art")
    ids1 = [u.evidence_id for u in units1]
    ids2 = [u.evidence_id for u in units2]
    assert ids1 == ids2


def test_evidence_ids_are_unique(annotated_evidence_path):
    units = load_from_path(annotated_evidence_path, domain_tag="art")
    ids = [u.evidence_id for u in units]
    assert len(ids) == len(set(ids))


def test_empty_directory_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="No JSON files"):
            load_from_path(tmpdir, domain_tag="test")


def test_text_contains_title_and_notes(annotated_evidence_path):
    units = load_from_path(annotated_evidence_path, domain_tag="art")
    first = units[0]
    assert first.title in first.text
    assert "Spring contemporary auction" in first.text


def test_source_is_filename(annotated_evidence_path):
    units = load_from_path(annotated_evidence_path, domain_tag="art")
    assert all(u.source == "sample_evidence_annotated.json" for u in units)


def test_load_real_art_evidence():
    """Smoke test: load actual art domain evidence without errors."""
    art_path = Path("../art-market-domain/data/manual_ingest_split")
    if not art_path.exists():
        pytest.skip("Art domain data not available")
    units = load_from_path(art_path, domain_tag="art")
    assert len(units) > 0
    for u in units:
        assert "assignments" not in u.metadata
        assert "causal_claims" not in u.metadata
        assert u.evidence_id
        assert u.title


def test_real_art_evidence_no_id_collisions():
    """Previously, SFMOMA duplicate-title records produced the same evidence_id."""
    art_path = Path("../art-market-domain/data/manual_ingest_split")
    if not art_path.exists():
        pytest.skip("Art domain data not available")
    units = load_from_path(art_path, domain_tag="art")
    ids = [u.evidence_id for u in units]
    duplicates = [eid for eid in set(ids) if ids.count(eid) > 1]
    assert duplicates == [], f"Duplicate evidence IDs: {duplicates}"
