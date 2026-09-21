from pathlib import Path
from services import (
    case_service,
    auth_service,
    ingest_service,
    correlate_service,
    risk_service,
    integrity_service,
    report_service
)
from domain.models import DetectedFormat, Mapping

def test_smoke_all_services():
    # case_service
    case = case_service.create_case("CASE_2026_01", "Test Title", "BADGE01")
    assert case is not None
    cases = case_service.list_cases()
    assert isinstance(cases, list)
    case_opt = case_service.get_case("case_1")
    
    # auth_service
    officer = {"id": "1", "password_hash": auth_service.hash_password("password123"), "is_active": 1, "failed_attempts": 0, "locked_until": None}
    session, token = auth_service.login("BADGE01", "password123", officer)
    assert session is not None
    sess_dict = session.model_dump()
    auth_service.validate_session(token, sess_dict)
    auth_service.logout(sess_dict)
    
    # ingest_service
    import tempfile
    import os
    dummy_path = Path("dummy.csv")
    dummy_path.write_text("calling,imei\n123,456")
    try:
        fmt = ingest_service.sniff(dummy_path)
        assert fmt == DetectedFormat.CDR
        h = ingest_service.hash_file(dummy_path)
        assert isinstance(h, str)
        prop = ingest_service.propose_mapping(["calling", "imei"], fmt)
        assert prop is not None
        
        mapping = Mapping(
            id="map_1", case_id="case_1", detected_kind="CDR",
            header_signature="calling,imei", mapping_json="{}",
            confidence_json="{}"
        )
        res = ingest_service.ingest_file("case_1", dummy_path, mapping, "BADGE01")
        assert res is not None
    finally:
        if dummy_path.exists():
            os.remove(dummy_path)
    
    # correlate_service
    entities_raw = []
    events = []
    entities = correlate_service.extract_entities(entities_raw)
    assert isinstance(entities, list)
    links = correlate_service.resolve_links(entities_raw, events, "case_1")
    assert isinstance(links, list)
    g = correlate_service.build_graph(entities_raw, [], events)
    assert g is not None
    
    # risk_service
    features = risk_service.compute_features(g)
    assert features is not None
    scores = risk_service.score("case_1")
    assert isinstance(scores, list)
    
    # integrity_service
    entry = integrity_service.append_audit("case_1", "BADGE01", "TEST_ACTION", "TARGET", "id1", {})
    assert entry is not None
    cv = integrity_service.verify_chain("case_1")
    assert cv is not None
    fv = integrity_service.verify_evidence("case_1")
    assert isinstance(fv, list)
    
    # report_service
    brief = report_service.build_brief("case_1", "BADGE01")
    assert brief is not None
