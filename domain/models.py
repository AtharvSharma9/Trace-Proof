from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum
from pathlib import Path

class DetectedFormat(str, Enum):
    CDR = 'CDR'
    IPDR = 'IPDR'
    BANK = 'BANK'
    UPI = 'UPI'
    EML = 'EML'
    ANDROID_DUMP = 'ANDROID_DUMP'
    APK = 'APK'
    UNKNOWN = 'UNKNOWN'

class MappingProposal(BaseModel):
    detected_kind: DetectedFormat
    header_signature: str
    mapping_json: Dict[str, str]
    confidence_json: Dict[str, float]
    datetime_format: Optional[str] = None

class Mapping(BaseModel):
    id: str
    case_id: str
    evidence_file_id: Optional[str] = None
    detected_kind: str
    header_signature: str
    mapping_json: str
    confidence_json: str
    datetime_format: Optional[str] = None
    auto_generated: int = 1
    confirmed_by_badge: Optional[str] = None
    confirmed_at: Optional[str] = None
    saved_as_plugin: int = 0

class IngestResult(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    evidence_file_id: str
    rows_total: int
    rows_parsed: int
    rows_rejected: int
    status: str
    # In-process payload — not persisted, not serialised
    _entities: list = PrivateAttr(default_factory=list)
    _events: list = PrivateAttr(default_factory=list)
    _rejects: list = PrivateAttr(default_factory=list)

    def __init__(self, *, _entities=None, _events=None, _rejects=None, **data):
        super().__init__(**data)
        self._entities = _entities or []
        self._events = _events or []
        self._rejects = _rejects or []


class BriefArtifacts(BaseModel):
    pdf_path: str
    json_path: str
    report_sha256: str
    audit_head_hash: str

class FileVerification(BaseModel):
    file_id: str
    filename: str
    original_sha256: str
    current_sha256: Optional[str] = None
    status: str # UNCHANGED, CHANGED, MISSING

class ChainVerification(BaseModel):
    intact: bool
    broken_at_seq: Optional[int] = None
    total_entries: int
    genesis_hash: str
    head_hash: str

class Case(BaseModel):
    id: str
    case_number: str
    title: str
    fir_number: Optional[str] = None
    police_station: Optional[str] = None
    complaint_date: Optional[str] = None
    description: Optional[str] = None
    created_by_badge: str
    created_by_name: str
    created_at: str
    status: str = 'OPEN'
    integrity_status: str = 'UNVERIFIED'
    last_verified_at: Optional[str] = None
    schema_version: int = 1

class Officer(BaseModel):
    id: str
    badge_no: str
    full_name: str
    rank: Optional[str] = None
    unit: Optional[str] = None
    role: str = 'IO'
    password_hash: str
    is_active: int = 1
    failed_attempts: int = 0
    locked_until: Optional[str] = None
    created_at: str
    last_login_at: Optional[str] = None

class Session(BaseModel):
    id: str
    officer_id: str
    token_hash: str
    issued_at: str
    expires_at: str
    last_seen_at: str
    revoked_at: Optional[str] = None
    workstation_id: str

class Entity(BaseModel):
    id: str
    case_id: str
    entity_type: str
    raw_value: str
    normalized_value: str
    label: Optional[str] = None
    role: str = 'UNKNOWN'
    occurrences: int = 0
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    attributes_json: str = '{}'
    created_at: str
    
class Event(BaseModel):
    id: str
    case_id: str
    event_type: str
    occurred_at: str
    occurred_at_tz: str = 'Asia/Kolkata'
    src_entity_id: Optional[str] = None
    dst_entity_id: Optional[str] = None
    device_entity_id: Optional[str] = None
    sim_entity_id: Optional[str] = None
    ip_entity_id: Optional[str] = None
    amount: Optional[float] = None
    currency: str = 'INR'
    direction: Optional[str] = None
    duration_sec: Optional[int] = None
    channel: Optional[str] = None
    reference_no: Optional[str] = None
    balance_after: Optional[float] = None
    raw_json: Optional[str] = None
    # Provenance triple - REQUIRED
    evidence_file_id: str
    source_row: int
    source_sha256: str
    created_at: str

class EntityLink(BaseModel):
    id: str
    case_id: str
    entity_a_id: str
    entity_b_id: str
    link_type: str
    confidence: float
    rationale: str
    support_count: int = 1
    supporting_event_ids: str = '[]'
    total_amount: Optional[float] = None
    first_at: Optional[str] = None
    last_at: Optional[str] = None
    status: str = 'ACTIVE'
    dismissed_by_badge: Optional[str] = None
    dismissal_reason: Optional[str] = None
    created_at: str

class RiskReason(BaseModel):
    id: str
    risk_score_id: str
    rule_code: str
    rule_name: str
    triggered: int
    raw_value: Optional[float] = None
    threshold: Optional[float] = None
    weight: float
    points_contributed: float
    plain_text: str
    display_order: int

class RiskScore(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    case_id: str
    entity_id: str
    score: float
    band: str
    rules_score: float
    anomaly_score: Optional[float] = None
    anomaly_used: int = 0
    rank_in_case: Optional[int] = None
    features_json: str
    model_version: str
    weights_hash: str
    random_seed: Optional[int] = None
    computed_by_badge: str
    computed_at: str
    is_current: int = 1
    reasons: List[RiskReason] = Field(default_factory=list)

class AuditEntry(BaseModel):
    id: str
    case_id: str
    seq: int
    occurred_at: str
    officer_badge: str
    officer_name: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    payload_json: str = '{}'
    payload_hash: str
    prev_hash: str
    entry_hash: str
