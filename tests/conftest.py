"""Shared pytest fixtures for POE-A tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def annotated_evidence_path() -> Path:
    return FIXTURES_DIR / "sample_evidence_annotated.json"


@pytest.fixture
def sample_concepts_response() -> dict:
    with (FIXTURES_DIR / "sample_concepts_response.json").open() as f:
        return json.load(f)


@pytest.fixture
def mock_llm_client(sample_concepts_response):
    """
    Mock LLMClient that returns sample concepts JSON from its complete() method.

    Satisfies the LLMClient protocol without touching any real provider SDK.
    """
    client = MagicMock()
    client.complete.return_value = json.dumps(sample_concepts_response)
    return client
