"""
tests/test_errors.py

Error-path hardening tests.
Corrupt, empty, oversized, password-protected, and path-traversal inputs
must raise clean typed errors — never a bare Exception or stack trace.
Spec: 02_TRD.md §7 S6-S8; 06_Implementation_Plan.md Phase 8 step 7.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services import ingest_service
from domain.errors import (
    ParseError, FileTooLargeError, PathTraversalError,
    PasswordProtectedError, DuplicateEvidenceError,
)
from domain.models import DetectedFormat


# ── Empty file ────────────────────────────────────────────────────────────────

def test_sniff_empty_file_raises(tmp_path):
    f = tmp_path / "empty.csv"
    f.write_bytes(b"")
    with pytest.raises(ParseError, match="empty"):
        ingest_service.sniff(f)


# ── Corrupt / binary file ─────────────────────────────────────────────────────

def test_sniff_corrupt_binary_returns_unknown(tmp_path):
    """Corrupt binary that matches no plugin → UNKNOWN, not crash."""
    f = tmp_path / "corrupt.csv"
    f.write_bytes(bytes(range(256)) * 10)
    result = ingest_service.sniff(f)
    assert result == DetectedFormat.UNKNOWN


# ── Path traversal ────────────────────────────────────────────────────────────

def test_sniff_symlink_raises(tmp_path):
    real = tmp_path / "real.csv"
    real.write_text("A-PARTY NO,B-PARTY NO\n+91999,+91888\n")
    link = tmp_path / "link.csv"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this system")
    with pytest.raises(PathTraversalError):
        ingest_service.sniff(link)


# ── File too large ────────────────────────────────────────────────────────────

def test_sniff_too_large_raises(tmp_path, monkeypatch):
    """Patch stat().st_size to simulate 600 MB file without writing 600 MB."""
    f = tmp_path / "huge.csv"
    f.write_text("A-PARTY NO,B-PARTY NO\n+91999,+91888\n")

    # Patch only the sniff-level limit (500 MB)
    import engine.mapping.sniff as sniff_mod
    original_max = sniff_mod._MAX_SNIFF_BYTES
    monkeypatch.setattr(sniff_mod, "_MAX_SNIFF_BYTES", 10)  # 10 bytes limit
    try:
        with pytest.raises(FileTooLargeError):
            ingest_service.sniff(f)
    finally:
        sniff_mod._MAX_SNIFF_BYTES = original_max


# ── Ingest: missing file ───────────────────────────────────────────────────────

def test_ingest_missing_file_raises(tmp_path):
    from domain.models import Mapping
    import json
    mapping = Mapping(
        id="m1", case_id="case1", detected_kind="CDR",
        header_signature="caller,callee",
        mapping_json=json.dumps({"caller": "A-PARTY NO"}),
        confidence_json=json.dumps({"caller": 0.9}),
    )
    with pytest.raises(ParseError):
        ingest_service.ingest_file("case1", tmp_path / "nonexistent.csv", mapping, "BADGE01")


# ── Auth: lockout ──────────────────────────────────────────────────────────────

def test_auth_lockout_after_5_failures():
    from services.auth_service import hash_password, login
    from domain.errors import InvalidCredentialsError, LockedOutError

    pw_hash = hash_password("correct_password")
    record = {
        "id": "off_1",
        "password_hash": pw_hash,
        "is_active": 1,
        "failed_attempts": 0,
        "locked_until": None,
    }

    # 4 failures — each reduces remaining by 1
    for i in range(4):
        with pytest.raises(InvalidCredentialsError) as exc_info:
            login("BADGE01", "wrong", record, "WS-1")
        # After i+1 failures, remaining = 5 - (i+1)
        assert exc_info.value.attempts_remaining == (4 - i)

    # 5th failure triggers lockout
    with pytest.raises(InvalidCredentialsError):
        login("BADGE01", "wrong", record, "WS-1")

    # Now locked
    with pytest.raises(LockedOutError) as exc_info:
        login("BADGE01", "correct_password", record, "WS-1")
    assert exc_info.value.minutes_remaining > 0


# ── Auth: session expiry ───────────────────────────────────────────────────────

def test_session_expired_raises():
    from services.auth_service import _hash_token
    from services.auth_service import validate_session
    from domain.errors import SessionExpiredError
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    raw_token = "test_token_value_123"
    session = {
        "id": "sess_1",
        "officer_id": "off_1",
        "token_hash": _hash_token(raw_token),
        "issued_at": (now - timedelta(hours=10)).isoformat(),
        "expires_at": (now - timedelta(hours=1)).isoformat(),  # already expired
        "last_seen_at": (now - timedelta(hours=2)).isoformat(),
        "revoked_at": None,
        "workstation_id": "WS-1",
    }
    with pytest.raises(SessionExpiredError):
        validate_session(raw_token, session)


# ── Auth: re-auth required ────────────────────────────────────────────────────

def test_reauth_required_for_brief():
    from services.auth_service import hash_password, require_reauth
    from domain.errors import ReAuthRequired
    from datetime import datetime, timezone, timedelta

    pw_hash = hash_password("correct")
    now = datetime.now(timezone.utc)
    raw_token = "tok_reauth_test"
    from services.auth_service import _hash_token
    session = {
        "id": "s1", "officer_id": "o1",
        "token_hash": _hash_token(raw_token),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=7)).isoformat(),
        "last_seen_at": now.isoformat(),
        "revoked_at": None,
        "workstation_id": "WS-1",
    }
    officer = {"id": "o1", "password_hash": pw_hash}

    # Wrong password → ReAuthRequired
    with pytest.raises(ReAuthRequired):
        require_reauth(raw_token, "wrong_password", session, officer, "BRIEF_GENERATED")

    # Correct password → no exception
    require_reauth(raw_token, "correct", session, officer, "BRIEF_GENERATED")
