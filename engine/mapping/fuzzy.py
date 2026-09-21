"""
engine/mapping/fuzzy.py

RapidFuzz-based header-to-canonical-field mapping.
Target: < 50 ms per file (spec: 02_TRD.md §8).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from rapidfuzz import process, fuzz

_SCHEMA_PATH = Path(__file__).parent.parent.parent / "config" / "canonical_schema.yaml"

_CANONICAL: Dict[str, str] = {}

def _load_schema() -> Dict[str, str]:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {k: v for k, v in data.get("canonical_schema", {}).items()}


def _get_canonical() -> Dict[str, str]:
    global _CANONICAL
    if not _CANONICAL:
        _CANONICAL = _load_schema()
    return _CANONICAL


def _normalise(h: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]', ' ', h.lower()).strip()


def propose_mapping(
    headers: List[str],
    fmt_kind: str,
    plugin_columns: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Dict]:
    """
    Fuzzy-match headers to canonical field names.

    1. First tries exact / alias match from the format plugin (plugin_columns).
    2. Falls back to RapidFuzz extractOne against the canonical schema keys.

    Returns:
        {
          "caller": {"source_col": "A-PARTY NO", "confidence": 0.94},
          ...
        }
    """
    canonical = list(_get_canonical().keys())
    result: Dict[str, Dict] = {}
    used_sources: set = set()

    norm_headers = {h: _normalise(h) for h in headers}

    # Phase 1: plugin-provided aliases
    if plugin_columns:
        for field, aliases in plugin_columns.items():
            for col_raw, col_norm in norm_headers.items():
                if col_raw in used_sources:
                    continue
                for alias in aliases:
                    if _normalise(alias) == col_norm:
                        result[field] = {"source_col": col_raw, "confidence": 1.0}
                        used_sources.add(col_raw)
                        break
                if field in result:
                    break

    # Phase 2: RapidFuzz fallback
    for col_raw, col_norm in norm_headers.items():
        if col_raw in used_sources:
            continue
        match = process.extractOne(
            col_norm, canonical,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=60,
        )
        if match:
            field_name, score, _ = match
            if field_name not in {v["source_col"] for v in result.values() if "source_col" in v}:
                if field_name not in result or result[field_name]["confidence"] < score / 100:
                    result[field_name] = {"source_col": col_raw, "confidence": round(score / 100, 4)}
                    used_sources.add(col_raw)

    return result
