"""
Mock Local Officer Store for Trace-Proof.
Used by S00 (Setup) and S01 (Login).
"""

from typing import List, Optional
import hashlib
from views.mock.types import Officer

# Initial mock officers store
_MOCK_OFFICERS: List[Officer] = [
    Officer(
        id="off_001",
        badge_no="BP-94821",
        full_name="Inspector Vikram Singh",
        rank="Inspector of Police",
        unit="Cyber Crime Cell, Zone 4",
        role="SUPERVISOR",
        password_hash=hashlib.sha256(b"TraceProof2026!").hexdigest(),
        is_active=True,
        failed_attempts=0,
        created_at="2026-09-01 10:00:00 IST",
        last_login_at="2026-09-21 14:30:00 IST"
    ),
    Officer(
        id="off_002",
        badge_no="BP-88104",
        full_name="Sub-Inspector Ananya Roy",
        rank="Sub-Inspector",
        unit="Cyber Crime Cell, Zone 4",
        role="IO",
        password_hash=hashlib.sha256(b"Officer@1234").hexdigest(),
        is_active=True,
        failed_attempts=0,
        created_at="2026-09-05 11:15:00 IST",
        last_login_at="2026-09-21 11:20:00 IST"
    ),
]

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_officers() -> List[Officer]:
    return _MOCK_OFFICERS

def get_officer_by_badge(badge_no: str) -> Optional[Officer]:
    for off in _MOCK_OFFICERS:
        if off.badge_no == badge_no:
            return off
    return None

def authenticate_officer(badge_no: str, password: str) -> tuple[bool, Optional[Officer], str]:
    officer = get_officer_by_badge(badge_no)
    if not officer:
        return False, None, "Badge number or password is incorrect."
    if not officer.is_active:
        return False, None, "Account is disabled."
    if officer.failed_attempts >= 5:
        return False, None, "Locked for 15 minutes after 5 failed attempts."
    
    if officer.password_hash == hash_password(password):
        officer.failed_attempts = 0
        officer.last_login_at = "21 Sep 2026, 14:32:07 IST"
        return True, officer, "Success"
    else:
        officer.failed_attempts += 1
        return False, None, "Badge number or password is incorrect."

def add_officer(badge_no: str, full_name: str, rank: str, unit: str, role: str, password: str) -> tuple[bool, str, Optional[Officer]]:
    if get_officer_by_badge(badge_no):
        return False, "Badge number already registered on this workstation.", None
    
    new_off = Officer(
        id=f"off_{len(_MOCK_OFFICERS)+1:03d}",
        badge_no=badge_no,
        full_name=full_name,
        rank=rank,
        unit=unit,
        role=role,
        password_hash=hash_password(password),
        is_active=True,
        created_at="21 Sep 2026, 14:32:07 IST"
    )
    _MOCK_OFFICERS.append(new_off)
    return True, "Account created. You are signed in.", new_off

def reset_officer_store():
    global _MOCK_OFFICERS
    _MOCK_OFFICERS = []
