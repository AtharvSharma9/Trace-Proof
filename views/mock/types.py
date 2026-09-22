"""
Type definitions for Trace-Proof mock data layer.
Named as specified in docs/05_Backend_Schema.md.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Officer:
    id: str
    badge_no: str
    full_name: str
    rank: str
    unit: str
    role: str  # 'IO', 'ANALYST', 'SUPERVISOR'
    password_hash: str
    is_active: bool = True
    failed_attempts: int = 0
    locked_until: Optional[str] = None
    created_at: str = ""
    last_login_at: Optional[str] = None

@dataclass
class Case:
    id: str
    case_number: str
    title: str
    fir_number: Optional[str]
    police_station: str
    complaint_date: str
    description: str
    created_by_badge: str
    created_by_name: str
    created_at: str
    status: str = "OPEN"  # 'OPEN', 'UNDER_REVIEW', 'CLOSED'
    integrity_status: str = "VERIFIED"  # 'UNVERIFIED', 'VERIFIED', 'COMPROMISED'
    last_verified_at: Optional[str] = None
    schema_version: int = 1

@dataclass
class EvidenceRowRef:
    filename: str
    row_number: int
    sha256: str

@dataclass
class EvidenceFile:
    id: str
    case_id: str
    original_filename: str
    original_path: str
    stored_path: str
    sha256: str
    size_bytes: int
    detected_kind: str  # 'CDR', 'IPDR', 'BANK', 'UPI', 'EML', 'ANDROID_DUMP', 'APK', 'UNKNOWN'
    detection_confidence: float
    rows_total: int
    rows_parsed: int
    rows_rejected: int
    parse_status: str  # 'PENDING', 'MAPPED', 'PARSED', 'FAILED', 'EXCLUDED'
    ingested_by_badge: str
    ingested_at: str
    md5: Optional[str] = None
    mime_type: Optional[str] = None
    mapping_id: Optional[str] = None
    parse_notes: Optional[str] = None
    exclusion_reason: Optional[str] = None

@dataclass
class Entity:
    id: str
    case_id: str
    entity_type: str  # 'PHONE', 'IMEI', 'IMSI', 'UPI', 'BANK_ACCOUNT', 'IFSC', 'IP', 'MAC', 'EMAIL', 'APK_CERT'
    value: str
    normalized_value: str
    occurrences: int
    first_seen: str
    last_seen: str
    created_at: str
    risk_score: float = 0.0
    risk_band: str = "Low"  # 'Low', 'Medium', 'High', 'Critical'
    is_victim: bool = False
    is_cashout: bool = False

@dataclass
class Event:
    id: str
    case_id: str
    event_type: str  # 'CALL', 'TRANSACTION', 'IP_ACTIVITY', 'EMAIL', 'LOGIN', 'WITHDRAWAL'
    event_time: str
    source_filename: str
    source_row: int
    source_sha256: str
    description: str
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    created_at: str = ""

@dataclass
class EntityLink:
    id: str
    case_id: str
    entity_a_id: str
    entity_b_id: str
    link_type: str  # 'SHARED_IMEI', 'SHARED_IMSI', 'SHARED_DEVICE', 'SHARED_IP_SUBNET', 'RECURRING_BENEFICIARY', 'SHARED_MAC', 'FUND_FLOW', 'SHARED_APK_CERT'
    confidence: float
    rationale: str
    created_at: str
    supporting_evidence: List[EvidenceRowRef] = field(default_factory=list)
    created_by_run_id: Optional[str] = None
    dismissed: bool = False
    dismiss_reason: Optional[str] = None

@dataclass
class RiskReason:
    id: str
    risk_score_id: str
    rule_code: str  # 'R01' to 'R12'
    reason_text: str
    weight: float
    triggered: bool
    evidence_refs: List[EvidenceRowRef] = field(default_factory=list)

@dataclass
class RiskScore:
    id: str
    case_id: str
    entity_id: str
    score: float
    band: str  # 'Low', 'Medium', 'High', 'Critical'
    rule_score: float
    ml_score: float
    ml_enabled: bool
    calculated_at: str
    reasons: List[RiskReason] = field(default_factory=list)
    analysis_run_id: Optional[str] = None

@dataclass
class AuditEntry:
    sequence: int
    case_id: str
    officer_badge: str
    officer_name: str
    action: str
    object_type: str
    object_id: str
    timestamp: str
    details_json: str
    previous_hash: str
    entry_hash: str

@dataclass
class SeizureRecommendation:
    entity_id: str
    entity_value: str
    account_number: str
    bank_ifsc: str
    estimated_balance: float
    risk_score: float
    risk_band: str
    recommendation_text: str
