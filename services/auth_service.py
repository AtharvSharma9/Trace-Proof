"""
services/auth_service.py

Authentication and session management.
Spec: 05_Backend_Schema.md §4, 02_TRD.md §4.

Security decisions:
  - argon2id (time_cost=3, memory_cost=65536, parallelism=4)
  - token = secrets.token_urlsafe(32); DB stores SHA-256 of token only
  - 8-hour sliding window, hard cap 24 h
  - 5 failures → 15-minute lockout; each failure audited
  - re-auth required for BRIEF_GENERATED and EVIDENCE_EXCLUDED
  - No recovery path; supervisor resets locally

All clock comparisons are done in UTC with timezone-aware datetimes.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from domain.errors import (
    AuthError, LockedOutError, InvalidCredentialsError,
    SessionExpiredError, ReAuthRequired,
)
from domain.models import Session

# ── Thresholds ──────────────────────────────────────────────────────────────
_MAX_ATTEMPTS    = 5
_LOCKOUT_MINUTES = 15
_SESSION_HOURS   = 8
_HARD_CAP_HOURS  = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _from_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plaintext: str) -> str:
    """
    Hash a plaintext password with argon2id.
    Returns the full encoded string (includes salt + params).
    Falls back to bcrypt if argon2 is not installed.
    """
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
        return ph.hash(plaintext)
    except ImportError:
        import bcrypt  # type: ignore
        return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """Verify plaintext against a stored argon2id (or bcrypt fallback) hash."""
    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
        ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
        try:
            return ph.verify(stored_hash, plaintext)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    except ImportError:
        import bcrypt  # type: ignore
        return bcrypt.checkpw(plaintext.encode(), stored_hash.encode())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── Public API ──────────────────────────────────────────────────────────────

def login(
    badge_no: str,
    password: str,
    officer_record: dict,
    workstation_id: str = "WS-1",
) -> tuple[Session, str]:
    """
    Authenticate an officer.

    Args:
        badge_no: The officer's badge number.
        password: Plaintext password.
        officer_record: Dict with keys: id, password_hash, is_active,
                        failed_attempts, locked_until.
        workstation_id: Identifier for the current machine.

    Returns:
        (Session model, raw_token_string)

    Raises:
        LockedOutError          — badge locked; carries minutes_remaining
        InvalidCredentialsError — wrong password; carries attempts_remaining
        AuthError               — account inactive or other
    """
    now = _now()

    if not officer_record.get("is_active", 1):
        raise AuthError(f"Badge {badge_no} is deactivated.")

    # Check lockout
    locked_until_str = officer_record.get("locked_until")
    if locked_until_str:
        locked_until = _from_iso(locked_until_str)
        if now < locked_until:
            mins = (locked_until - now).total_seconds() / 60
            raise LockedOutError(badge_no, mins)

    # Verify password
    if not verify_password(password, officer_record["password_hash"]):
        new_attempts = officer_record.get("failed_attempts", 0) + 1
        remaining = max(0, _MAX_ATTEMPTS - new_attempts)
        # Signal caller to persist updated attempts
        officer_record["failed_attempts"] = new_attempts
        if new_attempts >= _MAX_ATTEMPTS:
            officer_record["locked_until"] = _iso(now + timedelta(minutes=_LOCKOUT_MINUTES))
        raise InvalidCredentialsError(badge_no, remaining)

    # Success — reset failed attempts
    officer_record["failed_attempts"] = 0
    officer_record["locked_until"] = None

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    expires_at = now + timedelta(hours=_SESSION_HOURS)
    session = Session(
        id=str(uuid.uuid4()),
        officer_id=officer_record["id"],
        token_hash=token_hash,
        issued_at=_iso(now),
        expires_at=_iso(expires_at),
        last_seen_at=_iso(now),
        workstation_id=workstation_id,
    )
    return session, raw_token


def logout(session_record: dict) -> dict:
    """
    Revoke a session by setting revoked_at.

    Args:
        session_record: Mutable dict fetched from DB.
    Returns:
        Updated session_record with revoked_at set.
    Raises:
        SessionExpiredError — if already revoked.
    """
    if session_record.get("revoked_at"):
        raise SessionExpiredError("Session already revoked.")
    session_record["revoked_at"] = _iso(_now())
    return session_record


def validate_session(
    raw_token: str,
    session_record: dict,
) -> Session:
    """
    Validate a session token and slide the expiry window.

    Args:
        raw_token: The token from st.session_state (never stored in DB).
        session_record: Dict fetched from DB by token_hash.

    Returns:
        Updated Session model (caller must persist last_seen_at + expires_at).

    Raises:
        SessionExpiredError — revoked or past expires_at
        AuthError           — token hash mismatch
    """
    if session_record.get("revoked_at"):
        raise SessionExpiredError("Session has been revoked.")

    stored_hash = session_record.get("token_hash", "")
    if _hash_token(raw_token) != stored_hash:
        raise AuthError("Token mismatch.")

    now = _now()
    expires_at = _from_iso(session_record["expires_at"])
    issued_at  = _from_iso(session_record["issued_at"])

    if now > expires_at:
        raise SessionExpiredError("Session has expired.")

    # Hard cap: 24 hours from issue
    if now > issued_at + timedelta(hours=_HARD_CAP_HOURS):
        raise SessionExpiredError("Session exceeded 24-hour hard cap.")

    # Slide expiry
    new_expires = min(
        now + timedelta(hours=_SESSION_HOURS),
        issued_at + timedelta(hours=_HARD_CAP_HOURS),
    )
    session_record["expires_at"] = _iso(new_expires)
    session_record["last_seen_at"] = _iso(now)

    return Session(**{k: v for k, v in session_record.items()
                      if k in Session.model_fields})


def require_reauth(
    raw_token: str,
    password: str,
    session_record: dict,
    officer_record: dict,
    action: str,
) -> None:
    """
    Re-authentication gate for high-privilege actions (BRIEF_GENERATED, EVIDENCE_EXCLUDED).

    Validates the session then checks the password again.
    Raises:
        ReAuthRequired      — password wrong or session invalid
        LockedOutError      — badge locked
    """
    _RE_AUTH_ACTIONS = {"BRIEF_GENERATED", "EVIDENCE_EXCLUDED"}
    if action not in _RE_AUTH_ACTIONS:
        return  # no re-auth needed for other actions

    # Validate session first
    try:
        validate_session(raw_token, session_record)
    except (SessionExpiredError, AuthError) as exc:
        raise ReAuthRequired(f"Session invalid: {exc}") from exc

    # Verify password again
    if not verify_password(password, officer_record["password_hash"]):
        raise ReAuthRequired("Re-authentication failed: incorrect password.")
