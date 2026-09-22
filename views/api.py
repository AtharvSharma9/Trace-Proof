"""
Trace-Proof Data API Layer.
Sole data module imported by all screens (S00 - S17).

Controlled by environment variable TRACEPROOF_USE_REAL:
- Default (0): returns mock data from views/mock/
- Real (1): routes to services/ module functions if implemented
"""

import os
from typing import List, Dict, Any, Optional
from views.mock.types import (
    Officer, Case, EvidenceFile, Entity, Event, EntityLink,
    RiskScore, RiskReason, AuditEntry, SeizureRecommendation
)
from views.mock import officers as mock_officers
from views.mock import fixtures as mock_fixtures

# Check execution mode
USE_REAL_SERVICES = os.environ.get("TRACEPROOF_USE_REAL", "0") == "1"


def _check_real_mode(function_name: str):
    """If REAL mode is enabled but no service exists, raise an error card error."""
    if USE_REAL_SERVICES:
        raise NotImplementedError(
            f"[TRACEPROOF_USE_REAL=1] Real service backend for '{function_name}' is not yet connected."
        )


# ── AUTHENTICATION & OFFICERS (S00, S01) ────────────────────────────────────

def get_officer_count() -> int:
    """TAG: CONTRACT-NEEDED. Returns count of registered officers on workstation."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_officer_count")
    return len(mock_officers.get_officers())


def authenticate_officer(badge_no: str, password: str) -> tuple[bool, Optional[Officer], str]:
    """TAG: CONTRACT-NEEDED. Authenticates badge & password against officer store."""
    if USE_REAL_SERVICES:
        _check_real_mode("authenticate_officer")
    return mock_officers.authenticate_officer(badge_no, password)


def create_officer(badge_no: str, full_name: str, rank: str, unit: str, role: str, password: str) -> tuple[bool, str, Optional[Officer]]:
    """TAG: CONTRACT-NEEDED. Creates new officer account (S00 setup)."""
    if USE_REAL_SERVICES:
        _check_real_mode("create_officer")
    return mock_officers.add_officer(badge_no, full_name, rank, unit, role, password)


# ── CASE MANAGEMENT (S02, S03, S04) ─────────────────────────────────────────

def list_cases(search_query: str = "", status_filter: str = "ALL") -> List[Case]:
    """TAG: CONTRACT-NEEDED. Returns list of cases for Case List (S02)."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_cases")
    cases = [mock_fixtures.DEMO_CASE]
    if search_query:
        q = search_query.lower()
        cases = [c for c in cases if q in c.case_number.lower() or q in c.title.lower() or (c.fir_number and q in c.fir_number.lower())]
    if status_filter != "ALL":
        cases = [c for c in cases if c.status == status_filter]
    return cases


def get_case_by_id(case_id: str) -> Optional[Case]:
    """TAG: CONTRACT-NEEDED. Returns details for a specific case."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_case_by_id")
    if case_id == mock_fixtures.DEMO_CASE.id or case_id == mock_fixtures.DEMO_CASE.case_number:
        return mock_fixtures.DEMO_CASE
    return None


def create_case(case_number: str, title: str, fir_number: Optional[str], police_station: str, complaint_date: str, description: str, created_by_badge: str, created_by_name: str) -> Case:
    """TAG: CONTRACT-NEEDED. Creates a new case (S03)."""
    if USE_REAL_SERVICES:
        _check_real_mode("create_case")
    new_case = Case(
        id=f"case_{case_number.lower()}",
        case_number=case_number,
        title=title,
        fir_number=fir_number,
        police_station=police_station,
        complaint_date=complaint_date,
        description=description,
        created_by_badge=created_by_badge,
        created_by_name=created_by_name,
        created_at="21 Sep 2026, 14:30:00 IST",
        status="OPEN",
        integrity_status="VERIFIED"
    )
    return new_case


def create_sample_case() -> Case:
    """TAG: CONTRACT-NEEDED. Fast rehearsal shortcut to load Seed 42 demo case."""
    if USE_REAL_SERVICES:
        _check_real_mode("create_sample_case")
    return mock_fixtures.DEMO_CASE


def get_case_dashboard_counts(case_id: str) -> Dict[str, Any]:
    """TAG: CONTRACT-NEEDED. Returns tile summary numbers for S04."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_case_dashboard_counts")
    return {
        "files_count": len(mock_fixtures.EVIDENCE_FILES),
        "rows_count": sum(f.rows_parsed for f in mock_fixtures.EVIDENCE_FILES),
        "entities_count": 412,
        "links_count": 87,
        "top_risk_score": 94.0,
        "top_risk_band": "Critical",
        "top_suspect_name": "SBI 10928374651 (Rajesh Kumar)"
    }


def get_pipeline_status(case_id: str) -> Dict[str, str]:
    """TAG: CONTRACT-NEEDED. Returns pipeline step status dict for S04."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_pipeline_status")
    return {
        "Ingest": "Done",
        "Hash": "Done",
        "Correlate": "Done",
        "Graph": "Done",
        "Score": "Done",
        "Brief": "Pending"
    }


# ── INGESTION & EVIDENCE (S05, S06, S07) ────────────────────────────────────

def list_evidence_files(case_id: str) -> List[EvidenceFile]:
    """TAG: CONTRACT-NEEDED. Returns evidence register files for S05, S07."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_evidence_files")
    return mock_fixtures.EVIDENCE_FILES


def confirm_file_mapping(evidence_file_id: str, mapping_json: Dict[str, str], datetime_format: str) -> bool:
    """TAG: CONTRACT-NEEDED. Approves column mapping in S06."""
    if USE_REAL_SERVICES:
        _check_real_mode("confirm_file_mapping")
    return True


def exclude_evidence_file(evidence_file_id: str, reason: str) -> bool:
    """TAG: CONTRACT-NEEDED. Marks an evidence file excluded with audited reason."""
    if USE_REAL_SERVICES:
        _check_real_mode("exclude_evidence_file")
    for ef in mock_fixtures.EVIDENCE_FILES:
        if ef.id == evidence_file_id:
            ef.parse_status = "EXCLUDED"
            ef.exclusion_reason = reason
            return True
    return False


# ── ENTITIES & LINKS (S08, S11) ──────────────────────────────────────────────

def list_entities(case_id: str, entity_type: Optional[str] = None, search: str = "") -> List[Entity]:
    """TAG: CONTRACT-NEEDED. Returns entities list for S08."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_entities")
    entities = mock_fixtures.ENTITIES
    if entity_type and entity_type != "ALL":
        entities = [e for e in entities if e.entity_type == entity_type]
    if search:
        s = search.lower()
        entities = [e for e in entities if s in e.value.lower() or s in e.normalized_value.lower()]
    return entities


def get_entity_by_id(case_id: str, entity_id: str) -> Optional[Entity]:
    """TAG: CONTRACT-NEEDED. Returns single entity drill-down for S11."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_entity_by_id")
    for e in mock_fixtures.ENTITIES:
        if e.id == entity_id or e.value == entity_id:
            return e
    return None


def list_entity_links(case_id: str, min_confidence: float = 0.75) -> List[EntityLink]:
    """TAG: CONTRACT-NEEDED. Returns correlated links for S08."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_entity_links")
    return [l for l in mock_fixtures.LINKS if l.confidence >= min_confidence and not l.dismissed]


def dismiss_link(link_id: str, reason: str) -> bool:
    """TAG: CONTRACT-NEEDED. Dismisses a link with typed reason."""
    if USE_REAL_SERVICES:
        _check_real_mode("dismiss_link")
    for l in mock_fixtures.LINKS:
        if l.id == link_id:
            l.dismissed = True
            l.dismiss_reason = reason
            return True
    return False


# ── NETWORK GRAPH (S09) ─────────────────────────────────────────────────────

def get_graph_data(case_id: str, min_confidence: float = 0.75, top_n: int = 50) -> Dict[str, Any]:
    """TAG: CONTRACT-NEEDED. Returns nodes, edges and highlighted path for PyVis graph (S09)."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_graph_data")
    
    nodes = []
    for e in mock_fixtures.ENTITIES:
        nodes.append({
            "id": e.id,
            "label": e.value,
            "type": e.entity_type,
            "risk_score": e.risk_score,
            "risk_band": e.risk_band,
            "is_victim": e.is_victim,
            "is_cashout": e.is_cashout
        })
    
    edges = []
    for l in mock_fixtures.LINKS:
        if l.confidence >= min_confidence and not l.dismissed:
            edges.append({
                "id": l.id,
                "from": l.entity_a_id,
                "to": l.entity_b_id,
                "link_type": l.link_type,
                "confidence": l.confidence,
                "label": f"{l.link_type} ({int(l.confidence*100)}%)"
            })
            
    highlighted_path = [
        "ent_victim_acc", "ent_mule1a_acc", "ent_mule2a_acc", "ent_cashout_atm"
    ]
    
    return {
        "nodes": nodes[:top_n],
        "edges": edges,
        "highlighted_path": highlighted_path,
        "summary": "Victim → 3 mules → ATM cash-out · ₹4,80,000 · 11 minutes"
    }


# ── RISK BOARD & REASONS (S10, S11) ──────────────────────────────────────────

def list_risk_scores(case_id: str, band_filter: Optional[str] = None, entity_type: Optional[str] = None, only_path: bool = False, ml_enabled: bool = True) -> List[RiskScore]:
    """TAG: CONTRACT-NEEDED. Returns scored entities with reason codes for S10."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_risk_scores")
    scores = mock_fixtures.RISK_SCORES
    if band_filter and band_filter != "ALL":
        scores = [s for s in scores if s.band.lower() == band_filter.lower()]
    return scores


def get_risk_score_for_entity(case_id: str, entity_id: str) -> Optional[RiskScore]:
    """TAG: CONTRACT-NEEDED. Returns detailed risk score for single entity drill-down (S11)."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_risk_score_for_entity")
    for s in mock_fixtures.RISK_SCORES:
        if s.entity_id == entity_id:
            return s
    return None


def get_seizure_recommendations(case_id: str) -> List[SeizureRecommendation]:
    """TAG: CONTRACT-NEEDED. Returns frozen account seizure recommendations for S10."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_seizure_recommendations")
    return mock_fixtures.SEIZURE_RECOMMENDATIONS


# ── TIMELINE (S12) ──────────────────────────────────────────────────────────

def list_timeline_events(case_id: str, entity_id: Optional[str] = None) -> List[Event]:
    """TAG: CONTRACT-NEEDED. Returns chronological events list for S12."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_timeline_events")
    return mock_fixtures.EVENTS


# ── INTEGRITY VERIFICATION (S13, S17) ───────────────────────────────────────

def verify_case_integrity(case_id: str) -> Dict[str, Any]:
    """TAG: CONTRACT-NEEDED. Performs verification walk across evidence & audit chain for S13."""
    if USE_REAL_SERVICES:
        _check_real_mode("verify_case_integrity")
    
    if mock_fixtures.is_tampering_simulated():
        file_status = [
            {"filename": f.original_filename, "sha256_ingested": f.sha256, 
             "sha256_now": "ff8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e" if f.original_filename == "bank_statement_hdfc.xlsx" else f.sha256,
             "status": "CHANGED" if f.original_filename == "bank_statement_hdfc.xlsx" else "UNCHANGED"}
            for f in mock_fixtures.EVIDENCE_FILES
        ]
        return {
            "status": "COMPROMISED",
            "is_intact": False,
            "message": "TAMPER DETECTED. 1 file has changed since ingestion.",
            "file_status": file_status,
            "total_entries": 5,
            "chain_intact": True,
            "head_hash": "a1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2"
        }
    else:
        file_status = [
            {"filename": f.original_filename, "sha256_ingested": f.sha256, "sha256_now": f.sha256, "status": "UNCHANGED"}
            for f in mock_fixtures.EVIDENCE_FILES
        ]
        return {
            "status": "VERIFIED",
            "is_intact": True,
            "message": "Integrity verified. 7 of 7 evidence files unchanged. Audit chain intact across 5 entries.",
            "file_status": file_status,
            "total_entries": 5,
            "chain_intact": True,
            "head_hash": "a1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2"
        }


def simulate_tampering(enabled: bool) -> None:
    """TAG: CONTRACT-NEEDED. Toggles tampering simulation for demo rehearsal (S17)."""
    mock_fixtures.set_simulate_tampering(enabled)


# ── AUDIT LOG (S14) ──────────────────────────────────────────────────────────

def list_audit_entries(case_id: str, action_filter: Optional[str] = None) -> List[AuditEntry]:
    """TAG: CONTRACT-NEEDED. Returns append-only audit log for S14."""
    if USE_REAL_SERVICES:
        _check_real_mode("list_audit_entries")
    return mock_fixtures.AUDIT_LOG


# ── BRIEF BUILDER (S15) ──────────────────────────────────────────────────────

def generate_brief(case_id: str, officer_badge: str, password: str, sections: Dict[str, bool], remarks: str) -> Dict[str, Any]:
    """TAG: CONTRACT-NEEDED. Generates defensible 1-page PDF brief (S15). Requires re-auth."""
    import os, json, hashlib
    if USE_REAL_SERVICES:
        _check_real_mode("generate_brief")
    
    # Re-authenticate
    ok, officer, msg = mock_officers.authenticate_officer(officer_badge, password)
    if not ok:
        raise ValueError(f"Re-authentication failed: {msg}")

    c = get_case_by_id(case_id)
    case_num = c.case_number if c else case_id
    fir_num = c.fir_number if c else "N/A"
    desc = c.description if c else "Forensic Triage Summary"
    officer_name = officer.full_name if officer else "Inspector Vikram Singh"
    station = c.police_station if c else "Cyber Crime PS"

    os.makedirs("case_exports", exist_ok=True)
    pdf_filename = f"brief_{case_id}_20260921.pdf"
    pdf_filepath = os.path.join("case_exports", pdf_filename)
    json_filename = f"brief_{case_id}_20260921.json"
    json_filepath = os.path.join("case_exports", json_filename)

    # Generate PDF via ReportLab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        cv = canvas.Canvas(pdf_filepath, pagesize=letter)
        width, height = letter
        
        # Title & Banner
        cv.setFillColorRGB(0.106, 0.227, 0.361)  # #1B3A5C
        cv.rect(40, height - 60, width - 80, 40, fill=True, stroke=False)
        cv.setFillColorRGB(1, 1, 1)
        cv.setFont("Helvetica-Bold", 14)
        cv.drawString(50, height - 42, "TRACE-PROOF — CYBER FRAUD TRIAGE BRIEF")
        cv.setFont("Helvetica", 9)
        cv.drawString(50, height - 54, "OFFLINE FORENSIC EVIDENTIARY SUMMARY REPORT")
        
        # Meta Box
        cv.setFillColorRGB(0.06, 0.09, 0.16)
        cv.setFont("Helvetica-Bold", 10)
        cv.drawString(50, height - 85, f"Case Number: {case_num}    |    FIR: {fir_num}    |    Date: 21 Sep 2026")
        cv.setFont("Helvetica", 9)
        cv.drawString(50, height - 100, f"Investigating Officer: {officer_name} ({officer_badge})    |    Station: {station}")
        
        cv.setStrokeColorRGB(0.8, 0.84, 0.88)
        cv.line(50, height - 110, width - 50, height - 110)
        
        y = height - 130
        if sections.get("header", True):
            cv.setFont("Helvetica-Bold", 11)
            cv.setFillColorRGB(0.106, 0.227, 0.361)
            cv.drawString(50, y, "1. Case Overview")
            y -= 16
            cv.setFont("Helvetica", 9.5)
            cv.setFillColorRGB(0.1, 0.1, 0.1)
            cv.drawString(50, y, desc[:110])
            y -= 25
            
        if sections.get("suspects", True):
            cv.setFont("Helvetica-Bold", 11)
            cv.setFillColorRGB(0.106, 0.227, 0.361)
            cv.drawString(50, y, "2. Prime Suspect Endpoints")
            y -= 16
            cv.setFont("Helvetica", 9)
            cv.setFillColorRGB(0.1, 0.1, 0.1)
            cv.drawString(60, y, "• SBI 10928374651 (Rajesh Kumar) - Risk 94 (Critical) - Rapid pass-through (96% in 4m)")
            y -= 14
            cv.drawString(60, y, "• ICICI 40928172635 (Suresh Patel) - Risk 91 (Critical) - Shared IMEI 358941092837412")
            y -= 14
            cv.drawString(60, y, "• merchanthub.pay@okhdfcbank (Amit Verma) - Risk 89 (Critical) - Recurring beneficiary")
            y -= 25

        cv.setFont("Helvetica-Bold", 11)
        cv.setFillColorRGB(0.106, 0.227, 0.361)
        cv.drawString(50, y, "3. Officer's Remarks")
        y -= 16
        cv.setFont("Helvetica-Oblique", 9)
        cv.setFillColorRGB(0.2, 0.2, 0.2)
        cv.drawString(50, y, f'"{remarks[:120]}"')
        y -= 25

        cv.setFont("Helvetica-Bold", 11)
        cv.setFillColorRGB(0.106, 0.227, 0.361)
        cv.drawString(50, y, "4. Evidence Hash Appendix (SHA-256 Provenance)")
        y -= 16
        cv.setFont("Helvetica", 8)
        cv.setFillColorRGB(0.3, 0.3, 0.3)
        cv.drawString(60, y, "• cdr_operator_airtel.csv : e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        y -= 12
        cv.drawString(60, y, "• bank_statement_hdfc.xlsx : 9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e")
        y -= 12
        cv.drawString(60, y, "• bank_statement_sbi.xlsx  : 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b")
        
        # Footer
        cv.setStrokeColorRGB(0.106, 0.227, 0.361)
        cv.line(50, 50, width - 50, 50)
        cv.setFont("Helvetica", 8)
        cv.drawString(50, 38, "Workstation Head Hash: a1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2")
        cv.drawRightString(width - 50, 38, "Verified Offline Output — Page 1 of 1")
        
        cv.save()
        with open(pdf_filepath, "rb") as f:
            pdf_bytes = f.read()
    except Exception as err:
        pdf_bytes = f"%PDF-1.4 Mock Brief for {case_num}\nRemarks: {remarks}".encode("utf-8")
        with open(pdf_filepath, "wb") as f:
            f.write(pdf_bytes)

    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # JSON export dict
    json_data = {
        "case_id": case_id,
        "case_number": case_num,
        "fir_number": fir_num,
        "officer": {"name": officer_name, "badge": officer_badge, "station": station},
        "remarks": remarks,
        "pdf_sha256": sha256_hash,
        "sections_included": sections,
        "timestamp": "2026-09-22T09:15:00Z"
    }
    json_bytes = json.dumps(json_data, indent=2).encode("utf-8")
    with open(json_filepath, "wb") as f:
        f.write(json_bytes)

    return {
        "status": "SUCCESS",
        "file_path": pdf_filepath,
        "file_name": pdf_filename,
        "pdf_bytes": pdf_bytes,
        "json_bytes": json_bytes,
        "json_file_name": json_filename,
        "sha256": sha256_hash,
        "audit_head_hash": "a1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2"
    }


# ── SETTINGS (S16) ───────────────────────────────────────────────────────────

def get_risk_weights() -> List[Dict[str, Any]]:
    """TAG: CONTRACT-NEEDED. Returns rule weights for S16."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_risk_weights")
    return [
        {"code": "R01", "name": "Rapid pass-through", "weight": 18, "threshold": "≥ 85% in < 60m"},
        {"code": "R02", "name": "Fan-in", "weight": 12, "threshold": "≥ 8 sources in 2h"},
        {"code": "R03", "name": "Fan-out", "weight": 12, "threshold": "≥ 8 dests in 2h"},
        {"code": "R04", "name": "Layering depth", "weight": 12, "threshold": "≥ 3 hops in < 30m"},
        {"code": "R05", "name": "SIM-switch velocity", "weight": 10, "threshold": "≥ 3 IMSIs in 7d"},
        {"code": "R06", "name": "Device sharing", "weight": 8, "threshold": "≥ 3 phones on 1 IMEI"},
        {"code": "R07", "name": "New account, high volume", "weight": 10, "threshold": "< 30 days & > ₹5L"},
        {"code": "R08", "name": "Cash-out terminal", "weight": 14, "threshold": "ATM/wallet withdrawal"},
        {"code": "R09", "name": "Spoofed header", "weight": 8, "threshold": "SPF fail / mismatched From"},
        {"code": "R10", "name": "Odd-hour burst", "weight": 5, "threshold": "≥ 5 txns 00-05h IST"},
        {"code": "R11", "name": "Call-then-transfer", "weight": 12, "threshold": "Call < 15m before debit"},
        {"code": "R12", "name": "Centrality", "weight": 10, "threshold": "Top 5th percentile"},
    ]


def get_workstation_info() -> Dict[str, Any]:
    """TAG: CONTRACT-NEEDED. Returns workstation details for S16."""
    if USE_REAL_SERVICES:
        _check_real_mode("get_workstation_info")
    return {
        "app_name": "Trace-Proof",
        "version": "1.0.0-offline",
        "offline_status": "Strictly Offline · 0 network calls",
        "workstation_id": "WS-CYBER-DELHI-04",
        "db_location": "C:\\TraceProof\\data\\pramaan_app.db"
    }
