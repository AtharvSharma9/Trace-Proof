import os
from pathlib import Path
import networkx as nx
from domain.models import BriefArtifacts
from engine.integrity.hashing import hash_file
from engine.reports.json_builder import build_json_brief
from engine.reports.graph_renderer import render_static_graph
from engine.reports.pdf_builder import build_pdf_brief

def _mock_data_fetch(case_id: str):
    """Stub to fetch case data since DB/Phase 0 is not done yet."""
    return {
        "case": {"case_number": "PRM-1234", "fir_number": "FIR/2026/09", "created_by_badge": "B123", "created_by_name": "Officer Sharma"},
        "events": [{"occurred_at": "2026-09-21T10:00:00Z", "event_type": "FUND_TRANSFER", "amount": 50000}],
        "suspects": [{"rank": 1, "id": "E-999", "type": "PHONE", "score": 95, "band": "Critical", "reason": "Layer 1 Mule"}],
        "evidence": [{"filename": "statement.csv", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}],
        "graph": nx.karate_club_graph() # Mock graph
    }

def build_brief(case_id: str, officer_id: str) -> BriefArtifacts:
    """
    Generates the final one-page PDF and JSON investigative brief.
    Pre-generation checks and audit logging are mocked/stubbed for now.
    """
    # 1. Fetch data
    data = _mock_data_fetch(case_id)
    
    export_dir = Path("case/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = export_dir / f"{case_id}_brief.json"
    graph_path = export_dir / f"{case_id}_graph.png"
    pdf_path = export_dir / f"{case_id}_brief.pdf"
    
    # 2. Build JSON contract
    build_json_brief(data["case"], data["events"], data["suspects"], {}, data["evidence"], str(json_path))
    
    # 3. Render static graph
    render_static_graph(data["graph"], str(graph_path))
    
    # 4. Build PDF
    build_pdf_brief(str(json_path), str(graph_path), str(pdf_path))
    
    # 5. Hash the generated report
    report_hash = hash_file(pdf_path)
    audit_hash = "mock_audit_head_hash_e3b0c44"
    
    return BriefArtifacts(
        pdf_path=str(pdf_path),
        json_path=str(json_path),
        report_sha256=report_hash,
        audit_head_hash=audit_hash
    )
