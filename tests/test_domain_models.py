import pytest
from datetime import datetime
from pydantic import ValidationError
from domain.models import Event

def test_event_requires_provenance():
    # Should raise validation error without provenance fields
    with pytest.raises(ValidationError):
        Event(
            id="evt_1",
            case_id="case_1",
            event_type="CALL",
            occurred_at="2026-09-21T10:00:00Z",
            created_at="2026-09-21T10:00:00Z"
        )

def test_event_valid_with_provenance():
    # Should pass with provenance fields
    evt = Event(
        id="evt_1",
        case_id="case_1",
        event_type="CALL",
        occurred_at="2026-09-21T10:00:00Z",
        evidence_file_id="file_1",
        source_row=123,
        source_sha256="abc123hash",
        created_at="2026-09-21T10:00:00Z"
    )
    assert evt.evidence_file_id == "file_1"
    assert evt.source_row == 123
    assert evt.source_sha256 == "abc123hash"
