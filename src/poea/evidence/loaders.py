from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .normalizer import normalize_record
from .schemas import EvidenceUnit

logger = logging.getLogger(__name__)


def load_from_path(
    path: str | Path,
    domain_tag: str,
) -> list[EvidenceUnit]:
    """
    Load evidence from a JSON file or a directory of JSON files.

    Each file may be a JSON array of records or a single JSON object.
    Records lacking a title are skipped with a warning.
    """
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("*.json"))
        if not files:
            raise ValueError(f"No JSON files found in directory: {p}")
        units: list[EvidenceUnit] = []
        for f in files:
            units.extend(_load_file(f, domain_tag))
        return units
    return _load_file(p, domain_tag)


def _load_file(path: Path, domain_tag: str) -> list[EvidenceUnit]:
    source = path.name
    try:
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return []

    records: list[dict[str, Any]] = raw if isinstance(raw, list) else [raw]

    units: list[EvidenceUnit] = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            logger.warning("Skipping non-dict record %d in %s", i, source)
            continue
        if not record.get("title"):
            logger.warning("Skipping record %d in %s: missing title", i, source)
            continue
        units.append(normalize_record(record, source, domain_tag))

    logger.info("Loaded %d evidence units from %s", len(units), source)
    return units
