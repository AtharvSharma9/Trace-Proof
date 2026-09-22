"""
Coherent Mock Case Fixtures (Seed 42) for Trace-Proof.
Contains 1 victim, 1 fraudster, 3 layer-1 mules, 2 layer-2 mules, 1 ATM cash-out.
₹4,80,000 moves in 11 minutes across 3 hops (96% pass-through).
Includes all forensic hooks (shared IMEI, multi-IMSI, recurring UPI, SPF mismatch, spoofed call)
and legitimate decoys (high fan-in grocery store, family phone, shared /24 IP).
Every risk reason explicitly references raw evidence rows (filename, row, sha256).
"""

from typing import List, Dict, Any
from views.mock.types import (
    Case, EvidenceFile, EvidenceRowRef, Entity, Event, EntityLink,
    RiskScore, RiskReason, AuditEntry, SeizureRecommendation
)

# ── 1. EVIDENCE FILES ────────────────────────────────────────────────────────
EVIDENCE_FILES: List[EvidenceFile] = [
    EvidenceFile(
        id="ev_001",
        case_id="CASE_2026_0142",
        original_filename="cdr_operator_airtel.csv",
        original_path="/evidence/raw/cdr_operator_airtel.csv",
        stored_path="case_2026_0142/evidence/cdr_operator_airtel.csv",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        size_bytes=4821040,
        detected_kind="CDR",
        detection_confidence=0.96,
        rows_total=18450,
        rows_parsed=18442,
        rows_rejected=8,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:02:10 IST"
    ),
    EvidenceFile(
        id="ev_002",
        case_id="CASE_2026_0142",
        original_filename="cdr_operator_jio.csv",
        original_path="/evidence/raw/cdr_operator_jio.csv",
        stored_path="case_2026_0142/evidence/cdr_operator_jio.csv",
        sha256="a4f1c9d2e8b394a105c71d6e2f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a",
        size_bytes=6120480,
        detected_kind="CDR",
        detection_confidence=0.98,
        rows_total=24120,
        rows_parsed=24115,
        rows_rejected=5,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:02:45 IST"
    ),
    EvidenceFile(
        id="ev_003",
        case_id="CASE_2026_0142",
        original_filename="bank_statement_hdfc.xlsx",
        original_path="/evidence/raw/bank_statement_hdfc.xlsx",
        stored_path="case_2026_0142/evidence/bank_statement_hdfc.xlsx",
        sha256="9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
        size_bytes=8420100,
        detected_kind="BANK",
        detection_confidence=0.92,
        rows_total=31200,
        rows_parsed=31198,
        rows_rejected=2,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:03:12 IST"
    ),
    EvidenceFile(
        id="ev_004",
        case_id="CASE_2026_0142",
        original_filename="bank_statement_sbi.xlsx",
        original_path="/evidence/raw/bank_statement_sbi.xlsx",
        stored_path="case_2026_0142/evidence/bank_statement_sbi.xlsx",
        sha256="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
        size_bytes=7310450,
        detected_kind="BANK",
        detection_confidence=0.94,
        rows_total=28900,
        rows_parsed=28895,
        rows_rejected=5,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:03:50 IST"
    ),
    EvidenceFile(
        id="ev_005",
        case_id="CASE_2026_0142",
        original_filename="upi_settlement_icici.xlsx",
        original_path="/evidence/raw/upi_settlement_icici.xlsx",
        stored_path="case_2026_0142/evidence/upi_settlement_icici.xlsx",
        sha256="7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e",
        size_bytes=4100200,
        detected_kind="UPI",
        detection_confidence=0.91,
        rows_total=15800,
        rows_parsed=15796,
        rows_rejected=4,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:04:15 IST"
    ),
    EvidenceFile(
        id="ev_006",
        case_id="CASE_2026_0142",
        original_filename="ipdr_gateway_logs.csv",
        original_path="/evidence/raw/ipdr_gateway_logs.csv",
        stored_path="case_2026_0142/evidence/ipdr_gateway_logs.csv",
        sha256="4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c",
        size_bytes=2980100,
        detected_kind="IPDR",
        detection_confidence=0.89,
        rows_total=9960,
        rows_parsed=9955,
        rows_rejected=5,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:04:40 IST"
    ),
    EvidenceFile(
        id="ev_007",
        case_id="CASE_2026_0142",
        original_filename="phishing_alert.eml",
        original_path="/evidence/raw/phishing_alert.eml",
        stored_path="case_2026_0142/evidence/phishing_alert.eml",
        sha256="8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b",
        size_bytes=42010,
        detected_kind="EML",
        detection_confidence=0.99,
        rows_total=1,
        rows_parsed=1,
        rows_rejected=0,
        parse_status="PARSED",
        ingested_by_badge="BP-94821",
        ingested_at="21 Sep 2026, 14:05:00 IST"
    ),
]

# Helper dict for fast lookup of hashes by filename
FILE_HASH_MAP = {f.original_filename: f.sha256 for f in EVIDENCE_FILES}


# ── 2. CASE OBJECT ───────────────────────────────────────────────────────────
DEMO_CASE = Case(
    id="case_2026_0142",
    case_number="CASE_2026_0142",
    title="Cyber Fraud — Unauthorized INR 4.8L Fund Diversion via Mule Mesh",
    fir_number="FIR-2026-08912",
    police_station="Cyber Crime PS, Zone 4",
    complaint_date="21 Sep 2026",
    description="Investment fraud / APK phishing leading to unauthorized debits of ₹4,80,000 from victim account, layered across 3 mule levels to ATM cash-out within 11 minutes.",
    created_by_badge="BP-94821",
    created_by_name="Inspector Vikram Singh",
    created_at="21 Sep 2026, 13:45:00 IST",
    status="OPEN",
    integrity_status="VERIFIED",
    last_verified_at="21 Sep 2026, 14:10:00 IST",
    schema_version=1
)


# ── 3. ENTITIES ──────────────────────────────────────────────────────────────
ENTITIES: List[Entity] = [
    # Victim
    Entity(
        id="ent_victim_ph", case_id="case_2026_0142", entity_type="PHONE",
        value="+91 98765 43210", normalized_value="919876543210", occurrences=14,
        first_seen="21 Sep 2026, 14:20:00 IST", last_seen="21 Sep 2026, 14:32:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=0.0, risk_band="Low", is_victim=True
    ),
    Entity(
        id="ent_victim_acc", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="HDFC 30491029384", normalized_value="30491029384", occurrences=6,
        first_seen="21 Sep 2026, 14:30:00 IST", last_seen="21 Sep 2026, 14:32:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=0.0, risk_band="Low", is_victim=True
    ),

    # Fraudster contact
    Entity(
        id="ent_fraudster_ph", case_id="case_2026_0142", entity_type="PHONE",
        value="+91 91234 56789", normalized_value="919123456789", occurrences=8,
        first_seen="21 Sep 2026, 14:21:00 IST", last_seen="21 Sep 2026, 14:29:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=78.0, risk_band="High"
    ),

    # Mule Layer 1-A (Rajesh Kumar)
    Entity(
        id="ent_mule1a_acc", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="SBI 10928374651", normalized_value="10928374651", occurrences=28,
        first_seen="21 Sep 2026, 14:30:00 IST", last_seen="21 Sep 2026, 14:35:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=94.0, risk_band="Critical"
    ),
    Entity(
        id="ent_mule1a_ph", case_id="case_2026_0142", entity_type="PHONE",
        value="+91 98111 22233", normalized_value="919811122233", occurrences=18,
        first_seen="21 Sep 2026, 14:25:00 IST", last_seen="21 Sep 2026, 14:38:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=88.0, risk_band="Critical"
    ),
    Entity(
        id="ent_shared_imei_1", case_id="case_2026_0142", entity_type="IMEI",
        value="358941092837412", normalized_value="358941092837412", occurrences=42,
        first_seen="21 Sep 2026, 14:00:00 IST", last_seen="21 Sep 2026, 14:40:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=82.0, risk_band="Critical"
    ),

    # Mule Layer 1-B (Suresh Patel)
    Entity(
        id="ent_mule1b_acc", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="ICICI 40928172635", normalized_value="40928172635", occurrences=22,
        first_seen="21 Sep 2026, 14:31:00 IST", last_seen="21 Sep 2026, 14:36:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=91.0, risk_band="Critical"
    ),
    Entity(
        id="ent_mule1b_ph", case_id="case_2026_0142", entity_type="PHONE",
        value="+91 98111 44455", normalized_value="919811144455", occurrences=15,
        first_seen="21 Sep 2026, 14:26:00 IST", last_seen="21 Sep 2026, 14:39:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=86.0, risk_band="Critical"
    ),

    # Mule Layer 1-C (Amit Verma - Recurring UPI)
    Entity(
        id="ent_mule1c_upi", case_id="case_2026_0142", entity_type="UPI",
        value="merchanthub.pay@okhdfcbank", normalized_value="merchanthub.pay@okhdfcbank", occurrences=34,
        first_seen="21 Sep 2026, 14:30:00 IST", last_seen="21 Sep 2026, 14:37:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=89.0, risk_band="Critical"
    ),

    # Mule Layer 2-A (Vikram Yadav)
    Entity(
        id="ent_mule2a_acc", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="PNB 50192837465", normalized_value="50192837465", occurrences=19,
        first_seen="21 Sep 2026, 14:35:00 IST", last_seen="21 Sep 2026, 14:40:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=85.0, risk_band="Critical"
    ),

    # Mule Layer 2-B (Manoj Singh)
    Entity(
        id="ent_mule2b_acc", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="CANARA 60293847561", normalized_value="60293847561", occurrences=16,
        first_seen="21 Sep 2026, 14:36:00 IST", last_seen="21 Sep 2026, 14:41:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=84.0, risk_band="Critical"
    ),

    # Cash-out ATM Terminal
    Entity(
        id="ent_cashout_atm", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="ATM BANDRA 042 (Card 4591••••1049)", normalized_value="ATM_MUMBAI_BANDRA_042", occurrences=5,
        first_seen="21 Sep 2026, 14:41:00 IST", last_seen="21 Sep 2026, 14:43:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=96.0, risk_band="Critical", is_cashout=True
    ),

    # Phishing Email domain
    Entity(
        id="ent_phish_email", case_id="case_2026_0142", entity_type="EMAIL",
        value="support@kyc-update-sbi-portal.com", normalized_value="support@kyc-update-sbi-portal.com", occurrences=1,
        first_seen="21 Sep 2026, 14:15:00 IST", last_seen="21 Sep 2026, 14:15:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=76.0, risk_band="High"
    ),

    # Multi-IMSI IMEI device (Hook 2)
    Entity(
        id="ent_multi_imsi_imei", case_id="case_2026_0142", entity_type="IMEI",
        value="354019283746109", normalized_value="354019283746109", occurrences=56,
        first_seen="15 Sep 2026, 00:00:00 IST", last_seen="21 Sep 2026, 14:40:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=80.0, risk_band="Critical"
    ),

    # ── DECOYS (Must stay Low / Medium) ──────────────────────────────────────
    Entity(
        id="ent_decoy_kirana", case_id="case_2026_0142", entity_type="BANK_ACCOUNT",
        value="ICICI 20918273645 (Ramesh Kirana Stores)", normalized_value="20918273645", occurrences=412,
        first_seen="21 Sep 2026, 09:00:00 IST", last_seen="21 Sep 2026, 14:45:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=22.0, risk_band="Low"
    ),
    Entity(
        id="ent_decoy_family_phone", case_id="case_2026_0142", entity_type="PHONE",
        value="+91 99000 11122 (Kishore Sharma)", normalized_value="919900011122", occurrences=8,
        first_seen="21 Sep 2026, 10:00:00 IST", last_seen="21 Sep 2026, 14:00:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=15.0, risk_band="Low"
    ),
    Entity(
        id="ent_decoy_subnet_ip", case_id="case_2026_0142", entity_type="IP",
        value="103.21.244.15", normalized_value="103.21.244.15", occurrences=12,
        first_seen="21 Sep 2026, 12:00:00 IST", last_seen="21 Sep 2026, 14:30:00 IST",
        created_at="21 Sep 2026, 14:05:00 IST", risk_score=10.0, risk_band="Low"
    ),
]


# ── 4. EVENTS & PROVENANCE ───────────────────────────────────────────────────
EVENTS: List[Event] = [
    # Spoofed Call 9 mins before debit
    Event(
        id="evt_001", case_id="case_2026_0142", event_type="CALL",
        event_time="21 Sep 2026, 14:21:00 IST",
        source_filename="cdr_operator_airtel.csv", source_row=142,
        source_sha256=FILE_HASH_MAP["cdr_operator_airtel.csv"],
        description="Inbound call from unknown number +91 91234 56789 to victim Sunita Sharma (+91 98765 43210), duration 240s",
        amount=None, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Phishing Email
    Event(
        id="evt_002", case_id="case_2026_0142", event_type="EMAIL",
        event_time="21 Sep 2026, 14:15:00 IST",
        source_filename="phishing_alert.eml", source_row=1,
        source_sha256=FILE_HASH_MAP["phishing_alert.eml"],
        description="Phishing email received from support@kyc-update-sbi-portal.com with SPF FAIL and mismatched Return-Path",
        amount=None, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Hop 0: Victim Debit -> Mule 1A (₹2,50,000)
    Event(
        id="evt_003", case_id="case_2026_0142", event_type="TRANSACTION",
        event_time="21 Sep 2026, 14:30:00 IST",
        source_filename="bank_statement_hdfc.xlsx", source_row=1482,
        source_sha256=FILE_HASH_MAP["bank_statement_hdfc.xlsx"],
        description="Debit from Victim HDFC 30491029384 to SBI 10928374651 (Rajesh Kumar)",
        amount=250000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Hop 0: Victim Debit -> Mule 1B (₹1,50,000)
    Event(
        id="evt_004", case_id="case_2026_0142", event_type="TRANSACTION",
        event_time="21 Sep 2026, 14:31:00 IST",
        source_filename="bank_statement_hdfc.xlsx", source_row=1485,
        source_sha256=FILE_HASH_MAP["bank_statement_hdfc.xlsx"],
        description="Debit from Victim HDFC 30491029384 to ICICI 40928172635 (Suresh Patel)",
        amount=150000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Hop 0: Victim Debit -> Mule 1C via UPI (₹80,000)
    Event(
        id="evt_005", case_id="case_2026_0142", event_type="TRANSACTION",
        event_time="21 Sep 2026, 14:31:30 IST",
        source_filename="upi_settlement_icici.xlsx", source_row=892,
        source_sha256=FILE_HASH_MAP["upi_settlement_icici.xlsx"],
        description="UPI Transfer from Victim to merchanthub.pay@okhdfcbank",
        amount=80000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Hop 1: Mule 1A -> Mule 2A (96% pass-through: ₹2,40,000 in 4 mins)
    Event(
        id="evt_006", case_id="case_2026_0142", event_type="TRANSACTION",
        event_time="21 Sep 2026, 14:34:00 IST",
        source_filename="bank_statement_sbi.xlsx", source_row=2301,
        source_sha256=FILE_HASH_MAP["bank_statement_sbi.xlsx"],
        description="Rapid debit from SBI 10928374651 to PNB 50192837465 (Mule 2A Vikram Yadav)",
        amount=240000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Hop 1: Mule 1B -> Mule 2B (96% pass-through: ₹1,44,000 in 4 mins)
    Event(
        id="evt_007", case_id="case_2026_0142", event_type="TRANSACTION",
        event_time="21 Sep 2026, 14:35:00 IST",
        source_filename="bank_statement_hdfc.xlsx", source_row=1602,
        source_sha256=FILE_HASH_MAP["bank_statement_hdfc.xlsx"],
        description="Rapid debit from ICICI 40928172635 to CANARA 60293847561 (Mule 2B Manoj Singh)",
        amount=144000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    # Hop 2: Mule 2A + 2B -> Cash-out ATM (₹4,40,000 at 14:41 - 14:43 IST)
    Event(
        id="evt_008", case_id="case_2026_0142", event_type="WITHDRAWAL",
        event_time="21 Sep 2026, 14:41:00 IST",
        source_filename="bank_statement_sbi.xlsx", source_row=2415,
        source_sha256=FILE_HASH_MAP["bank_statement_sbi.xlsx"],
        description="ATM cash withdrawal at ATM BANDRA 042 from PNB 50192837465",
        amount=230000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
    Event(
        id="evt_009", case_id="case_2026_0142", event_type="WITHDRAWAL",
        event_time="21 Sep 2026, 14:43:00 IST",
        source_filename="bank_statement_sbi.xlsx", source_row=2418,
        source_sha256=FILE_HASH_MAP["bank_statement_sbi.xlsx"],
        description="ATM cash withdrawal at ATM BANDRA 042 from CANARA 60293847561",
        amount=210000.0, currency="INR", created_at="21 Sep 2026, 14:05:00 IST"
    ),
]


# ── 5. ENTITY LINKS & CORRELATIONS ───────────────────────────────────────────
LINKS: List[EntityLink] = [
    # Hook 1: Mules 1A & 1B sharing one IMEI
    EntityLink(
        id="link_001", case_id="case_2026_0142",
        entity_a_id="ent_mule1a_ph", entity_b_id="ent_mule1b_ph",
        link_type="SHARED_IMEI", confidence=0.98,
        rationale="Both handset numbers +91 98111 22233 and +91 98111 44455 used IMEI 358941092837412 within 15 minutes of fraud event.",
        created_at="21 Sep 2026, 14:10:00 IST",
        supporting_evidence=[
            EvidenceRowRef("cdr_operator_airtel.csv", 412, FILE_HASH_MAP["cdr_operator_airtel.csv"]),
            EvidenceRowRef("cdr_operator_jio.csv", 819, FILE_HASH_MAP["cdr_operator_jio.csv"]),
        ]
    ),
    # Hook 2: Multi-IMSI SIM Switch
    EntityLink(
        id="link_002", case_id="case_2026_0142",
        entity_a_id="ent_multi_imsi_imei", entity_b_id="ent_mule1a_ph",
        link_type="SHARED_IMSI", confidence=0.95,
        rationale="IMEI 354019283746109 observed cycling across 4 distinct IMSIs in 7 days.",
        created_at="21 Sep 2026, 14:10:00 IST",
        supporting_evidence=[
            EvidenceRowRef("cdr_operator_airtel.csv", 1024, FILE_HASH_MAP["cdr_operator_airtel.csv"])
        ]
    ),
    # Hook 3: Recurring UPI beneficiary
    EntityLink(
        id="link_003", case_id="case_2026_0142",
        entity_a_id="ent_victim_acc", entity_b_id="ent_mule1c_upi",
        link_type="RECURRING_BENEFICIARY", confidence=0.92,
        rationale="UPI ID merchanthub.pay@okhdfcbank received debits from 3 unrelated victims in past 48 hours.",
        created_at="21 Sep 2026, 14:10:00 IST",
        supporting_evidence=[
            EvidenceRowRef("upi_settlement_icici.xlsx", 892, FILE_HASH_MAP["upi_settlement_icici.xlsx"])
        ]
    ),
    # Fund flow links
    EntityLink(
        id="link_004", case_id="case_2026_0142",
        entity_a_id="ent_victim_acc", entity_b_id="ent_mule1a_acc",
        link_type="FUND_FLOW", confidence=1.0,
        rationale="Direct fund transfer of ₹2,50,000 at 14:30:00 IST.",
        created_at="21 Sep 2026, 14:10:00 IST",
        supporting_evidence=[
            EvidenceRowRef("bank_statement_hdfc.xlsx", 1482, FILE_HASH_MAP["bank_statement_hdfc.xlsx"])
        ]
    ),
    EntityLink(
        id="link_005", case_id="case_2026_0142",
        entity_a_id="ent_mule1a_acc", entity_b_id="ent_mule2a_acc",
        link_type="FUND_FLOW", confidence=1.0,
        rationale="Rapid pass-through transfer of ₹2,40,000 (96%) within 4 minutes.",
        created_at="21 Sep 2026, 14:10:00 IST",
        supporting_evidence=[
            EvidenceRowRef("bank_statement_sbi.xlsx", 2301, FILE_HASH_MAP["bank_statement_sbi.xlsx"])
        ]
    ),
    EntityLink(
        id="link_006", case_id="case_2026_0142",
        entity_a_id="ent_mule2a_acc", entity_b_id="ent_cashout_atm",
        link_type="FUND_FLOW", confidence=1.0,
        rationale="ATM cash withdrawal of ₹2,30,000 at ATM BANDRA 042.",
        created_at="21 Sep 2026, 14:10:00 IST",
        supporting_evidence=[
            EvidenceRowRef("bank_statement_sbi.xlsx", 2415, FILE_HASH_MAP["bank_statement_sbi.xlsx"])
        ]
    ),
]


# ── 6. RISK SCORES & REASONS ────────────────────────────────────────────────
RISK_SCORES: List[RiskScore] = [
    # Top Suspect: Mule 1A (Rajesh Kumar)
    RiskScore(
        id="rs_001", case_id="case_2026_0142", entity_id="ent_mule1a_acc",
        score=94.0, band="Critical", rule_score=94.0, ml_score=91.5, ml_enabled=True,
        calculated_at="21 Sep 2026, 14:12:00 IST",
        reasons=[
            RiskReason(
                id="rr_001", risk_score_id="rs_001", rule_code="R01",
                reason_text="Forwarded 96% of credited funds within 4 minutes (R01 Rapid pass-through)",
                weight=18.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("bank_statement_hdfc.xlsx", 1482, FILE_HASH_MAP["bank_statement_hdfc.xlsx"]),
                    EvidenceRowRef("bank_statement_sbi.xlsx", 2301, FILE_HASH_MAP["bank_statement_sbi.xlsx"])
                ]
            ),
            RiskReason(
                id="rr_002", risk_score_id="rs_001", rule_code="R04",
                reason_text="Sits on a chain of 3 hops completed in 11 minutes (R04 Layering depth)",
                weight=12.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("bank_statement_sbi.xlsx", 2301, FILE_HASH_MAP["bank_statement_sbi.xlsx"])
                ]
            ),
            RiskReason(
                id="rr_003", risk_score_id="rs_001", rule_code="R06",
                reason_text="One handset (IMEI 358941092837412) used across multiple suspect SIMs (R06 Device sharing)",
                weight=8.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("cdr_operator_airtel.csv", 412, FILE_HASH_MAP["cdr_operator_airtel.csv"])
                ]
            ),
            RiskReason(
                id="rr_004", risk_score_id="rs_001", rule_code="R12",
                reason_text="Sits on 95% of all victim-to-cash-out paths (R12 Centrality)",
                weight=10.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("bank_statement_hdfc.xlsx", 1482, FILE_HASH_MAP["bank_statement_hdfc.xlsx"])
                ]
            )
        ]
    ),

    # Suspect: Mule 1B (Suresh Patel)
    RiskScore(
        id="rs_002", case_id="case_2026_0142", entity_id="ent_mule1b_acc",
        score=91.0, band="Critical", rule_score=91.0, ml_score=88.0, ml_enabled=True,
        calculated_at="21 Sep 2026, 14:12:00 IST",
        reasons=[
            RiskReason(
                id="rr_005", risk_score_id="rs_002", rule_code="R01",
                reason_text="Forwarded 96% of credited funds within 4 minutes (R01 Rapid pass-through)",
                weight=18.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("bank_statement_hdfc.xlsx", 1485, FILE_HASH_MAP["bank_statement_hdfc.xlsx"]),
                    EvidenceRowRef("bank_statement_hdfc.xlsx", 1602, FILE_HASH_MAP["bank_statement_hdfc.xlsx"])
                ]
            ),
            RiskReason(
                id="rr_006", risk_score_id="rs_002", rule_code="R06",
                reason_text="Handset IMEI 358941092837412 shared with primary suspect (R06 Device sharing)",
                weight=8.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("cdr_operator_jio.csv", 819, FILE_HASH_MAP["cdr_operator_jio.csv"])
                ]
            )
        ]
    ),

    # Suspect: Phishing Mail Domain
    RiskScore(
        id="rs_003", case_id="case_2026_0142", entity_id="ent_phish_email",
        score=76.0, band="High", rule_score=76.0, ml_score=70.0, ml_enabled=True,
        calculated_at="21 Sep 2026, 14:12:00 IST",
        reasons=[
            RiskReason(
                id="rr_007", risk_score_id="rs_003", rule_code="R09",
                reason_text="Sender domain fails SPF check and From address does not match Return-Path (R09 Spoofed header)",
                weight=8.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("phishing_alert.eml", 1, FILE_HASH_MAP["phishing_alert.eml"])
                ]
            )
        ]
    ),

    # Fraudster Contact
    RiskScore(
        id="rs_004", case_id="case_2026_0142", entity_id="ent_fraudster_ph",
        score=78.0, band="High", rule_score=78.0, ml_score=75.0, ml_enabled=True,
        calculated_at="21 Sep 2026, 14:12:00 IST",
        reasons=[
            RiskReason(
                id="rr_008", risk_score_id="rs_004", rule_code="R11",
                reason_text="Inbound call from unknown number 9 minutes before victim's first debit (R11 Call-then-transfer)",
                weight=12.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("cdr_operator_airtel.csv", 142, FILE_HASH_MAP["cdr_operator_airtel.csv"])
                ]
            )
        ]
    ),

    # Decoy: Ramesh Kirana (High Fan-In, Low Risk)
    RiskScore(
        id="rs_005", case_id="case_2026_0142", entity_id="ent_decoy_kirana",
        score=22.0, band="Low", rule_score=22.0, ml_score=15.0, ml_enabled=True,
        calculated_at="21 Sep 2026, 14:12:00 IST",
        reasons=[
            RiskReason(
                id="rr_009", risk_score_id="rs_005", rule_code="R02",
                reason_text="Received funds from 412 small customer transactions over 8 hours (R02 Fan-in, Legitimate Retail Pattern)",
                weight=12.0, triggered=True,
                evidence_refs=[
                    EvidenceRowRef("upi_settlement_icici.xlsx", 12, FILE_HASH_MAP["upi_settlement_icici.xlsx"])
                ]
            )
        ]
    ),
]


# ── 7. SEIZURE RECOMMENDATIONS ──────────────────────────────────────────────
SEIZURE_RECOMMENDATIONS: List[SeizureRecommendation] = [
    SeizureRecommendation(
        entity_id="ent_mule1a_acc",
        entity_value="SBI 10928374651",
        account_number="10928374651",
        bank_ifsc="SBIN0001042",
        estimated_balance=10000.0,
        risk_score=94.0,
        risk_band="Critical",
        recommendation_text="IMMEDIATE FREEZE: Layer-1 mule account (Rajesh Kumar). Received ₹2,50,000 from victim. ₹10,000 residual balance recoverable."
    ),
    SeizureRecommendation(
        entity_id="ent_mule2a_acc",
        entity_value="PNB 50192837465",
        account_number="50192837465",
        bank_ifsc="PUNB0109200",
        estimated_balance=10000.0,
        risk_score=85.0,
        risk_band="Critical",
        recommendation_text="IMMEDIATE FREEZE: Layer-2 mule account (Vikram Yadav). Received ₹2,40,000 pass-through from Layer-1. ₹10,000 residual balance."
    ),
    SeizureRecommendation(
        entity_id="ent_mule1c_upi",
        entity_value="merchanthub.pay@okhdfcbank",
        account_number="90817263541",
        bank_ifsc="HDFC0000142",
        estimated_balance=80000.0,
        risk_score=89.0,
        risk_band="Critical",
        recommendation_text="URGENT FREEZE: Recurring beneficiary UPI account (Amit Verma). Received ₹80,000. Full amount currently unwithdrawn."
    ),
]


# ── 8. AUDIT LOG ─────────────────────────────────────────────────────────────
AUDIT_LOG: List[AuditEntry] = [
    AuditEntry(
        sequence=1, case_id="case_2026_0142",
        officer_badge="BP-94821", officer_name="Inspector Vikram Singh",
        action="CASE_CREATED", object_type="CASE", object_id="case_2026_0142",
        timestamp="21 Sep 2026, 13:45:00 IST",
        details_json='{"title": "Cyber Fraud — Unauthorized INR 4.8L Fund Diversion"}',
        previous_hash="0000000000000000000000000000000000000000000000000000000000000000",
        entry_hash="c7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8"
    ),
    AuditEntry(
        sequence=2, case_id="case_2026_0142",
        officer_badge="BP-94821", officer_name="Inspector Vikram Singh",
        action="EVIDENCE_INGESTED", object_type="EVIDENCE_FILE", object_id="ev_001",
        timestamp="21 Sep 2026, 14:02:10 IST",
        details_json='{"filename": "cdr_operator_airtel.csv", "rows": 18450}',
        previous_hash="c7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8",
        entry_hash="d8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9"
    ),
    AuditEntry(
        sequence=3, case_id="case_2026_0142",
        officer_badge="BP-94821", officer_name="Inspector Vikram Singh",
        action="CORRELATION_RUN", object_type="ANALYSIS_RUN", object_id="run_corr_01",
        timestamp="21 Sep 2026, 14:10:00 IST",
        details_json='{"entities_found": 412, "links_found": 87}',
        previous_hash="d8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9",
        entry_hash="e9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0"
    ),
    AuditEntry(
        sequence=4, case_id="case_2026_0142",
        officer_badge="BP-94821", officer_name="Inspector Vikram Singh",
        action="RISK_SCORING_RUN", object_type="ANALYSIS_RUN", object_id="run_risk_01",
        timestamp="21 Sep 2026, 14:12:00 IST",
        details_json='{"scored_entities": 412, "critical": 6, "high": 14}',
        previous_hash="e9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0",
        entry_hash="f0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1"
    ),
    AuditEntry(
        sequence=5, case_id="case_2026_0142",
        officer_badge="BP-94821", officer_name="Inspector Vikram Singh",
        action="INTEGRITY_VERIFIED", object_type="CASE", object_id="case_2026_0142",
        timestamp="21 Sep 2026, 14:15:00 IST",
        details_json='{"status": "PASSED", "files_verified": 7, "mismatches": 0}',
        previous_hash="f0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1",
        entry_hash="a1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2"
    )
]

# State variable for demo tampering simulation (S17 checkbox)
_SIMULATE_TAMPERING = False

def set_simulate_tampering(enabled: bool):
    global _SIMULATE_TAMPERING
    _SIMULATE_TAMPERING = enabled

def is_tampering_simulated() -> bool:
    return _SIMULATE_TAMPERING
