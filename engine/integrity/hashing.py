"""
engine/integrity/hashing.py

SHA-256 hashing and audit-chain helpers.
Spec: 02_TRD.md §7, S3; 05_Backend_Schema.md §3.12.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Optional
from pathlib import Path

_CHUNK = 1024 * 1024  # 1 MiB


def hash_file(path: Path, progress_cb: Optional[Callable[[int, int], None]] = None) -> str:
    """
    Compute SHA-256 of a file using 1 MiB chunks.

    Args:
        path: Path to the file.
        progress_cb: Optional callback(bytes_done, bytes_total).
    Returns:
        64-character lowercase hex string.
    """
    h = hashlib.sha256()
    total = path.stat().st_size
    done = 0
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
    return h.hexdigest()


def canonical_json(payload: dict) -> str:
    """Sorted-key, no-whitespace, UTF-8 JSON for deterministic hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_payload(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


_SEP = "\x1f"


def compute_entry_hash(
    prev_hash: str,
    seq: int,
    occurred_at: str,
    officer_badge: str,
    action: str,
    target_type: str,
    target_id: str,
    payload_hash: str,
) -> str:
    """
    Compute the chain entry hash exactly as specified in 05_Backend_Schema.md §3.12.

    entry_hash = SHA256(prev_hash ‖ seq ‖ occurred_at ‖ officer_badge ‖
                        action ‖ target_type ‖ target_id ‖ payload_hash)
    Fields are joined with \\x1f to prevent boundary ambiguity.
    """
    parts = [
        prev_hash,
        str(seq),
        occurred_at,
        officer_badge,
        action,
        target_type or "",
        target_id or "",
        payload_hash,
    ]
    raw = _SEP.join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
