"""
tests/test_db.py

Comprehensive test suite for PRAMAAN SQLite database architecture.
Verifies:
  - Both schemas (pramaan_app.db & case.pramaan)
  - Forensic append-only triggers on audit_log
  - Foreign key enforcement
  - Entity resolution unique constraint & upsert logic
  - Event provenance triple enforcement
  - Bulk insertion performance and correctness
  - Audit log hash chaining
  - services/case_service integration
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import uuid
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pytest
except ImportError:
    import contextlib

    class _PytestFallback:
        @staticmethod
        @contextlib.contextmanager
        def raises(expected_exception):
            class ExcInfo:
                value = None
            info = ExcInfo()
            try:
                yield info
            except expected_exception as e:
                info.value = e
            else:
                raise AssertionError(f"Expected exception {expected_exception} was not raised")

    pytest = _PytestFallback()  # type: ignore

from db.init import (
    configure_connection,
    get_app_connection,
    initialize_app_database,
    verify_app_database,
    initialize_case_database,
    verify_case_database,
    get_case_connection,
)
from db import repository as repo
from services import case_service


def test_app_database_schema_and_operations():
    """Verify pramaan_app.db initializes with required tables and handles officer/session ops."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "pramaan_app.db"
        conn = initialize_app_database(db_path)
        try:
            assert verify_app_database(conn) is True

            # Initially 0 officers
            assert repo.count_officers(conn) == 0

            # Create officer
            officer_id = repo.create_officer(
                conn,
                {
                    "badge_no": "BADGE_99",
                    "full_name": "Test Investigator",
                    "role": "IO",
                    "password_hash": "argon2_test_hash",
                },
            )
            assert officer_id is not None
            assert repo.count_officers(conn) == 1

            # Get officer
            off = repo.get_officer_by_badge(conn, "BADGE_99")
            assert off is not None
            assert off["full_name"] == "Test Investigator"

            # Create session
            sess_id = repo.create_session(
                conn,
                {
                    "officer_id": officer_id,
                    "token_hash": "sha256_token_digest",
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": datetime.now(timezone.utc).isoformat(),
                    "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    "workstation_id": "WS-TEST",
                },
            )
            assert sess_id is not None

            # Get session
            sess = repo.get_session_by_token_hash(conn, "sha256_token_digest")
            assert sess is not None
            assert sess["officer_id"] == officer_id

            # Revoke session
            repo.revoke_session(conn, sess_id, datetime.now(timezone.utc).isoformat())
            sess_revoked = repo.get_session_by_token_hash(conn, "sha256_token_digest")
            assert sess_revoked["revoked_at"] is not None

        finally:
            conn.close()


def test_case_database_schema_and_genesis():
    """Verify case.pramaan initializes with all 14 tables and writes the genesis audit entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "CASE_TEST_001"
        case_payload = {
            "id": "case_test_id",
            "case_number": "CASE_2026_001",
            "title": "Operation Mule Hunter",
            "created_by_badge": "IO_42",
            "created_by_name": "Inspector Vijay",
        }
        conn = initialize_case_database(case_dir, case_payload)
        try:
            assert verify_case_database(conn) is True

            # Check folder structure
            assert (case_dir / "evidence").is_dir()
            assert (case_dir / "staging").is_dir()
            assert (case_dir / "exports").is_dir()
            assert (case_dir / "manifest.json").is_file()
            assert (case_dir / "app.log").is_file()

            # Verify case table entry
            case_row = repo.get_case(conn, "case_test_id")
            assert case_row is not None
            assert case_row["case_number"] == "CASE_2026_001"
            assert case_row["title"] == "Operation Mule Hunter"
            assert case_row["created_by_badge"] == "IO_42"

            # Verify Genesis Audit Log Entry (seq=0, prev_hash=64 zeros)
            seq, head_hash = repo.get_audit_head(conn, "case_test_id")
            assert seq == 0
            assert len(head_hash) == 64

            audit_entries = repo.get_audit_chain(conn, "case_test_id")
            assert len(audit_entries) == 1
            genesis = audit_entries[0]
            assert genesis["seq"] == 0
            assert genesis["prev_hash"] == "0" * 64
            assert genesis["action"] == "CASE_CREATED"
            assert genesis["officer_badge"] == "IO_42"

            # Check manifest head hash matches genesis entry
            manifest = json.loads((case_dir / "manifest.json").read_text())
            assert manifest["audit_head_hash"] == head_hash

        finally:
            conn.close()


def test_audit_log_append_only_triggers():
    """Verify that SQLite triggers block UPDATE and DELETE on audit_log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "CASE_TRIGGER_TEST"
        conn = initialize_case_database(
            case_dir,
            {
                "id": "case_trig",
                "case_number": "CASE_TRIG_01",
                "title": "Trigger Test",
                "created_by_badge": "IO_01",
            },
        )
        try:
            # 1. Attempt UPDATE on audit_log -> MUST fail with trigger abort
            with pytest.raises(sqlite3.IntegrityError) as exc_info:
                conn.execute("UPDATE audit_log SET action = 'TAMPERED'")
            assert "audit_log is append-only" in str(exc_info.value)

            # 2. Attempt DELETE on audit_log -> MUST fail with trigger abort
            with pytest.raises(sqlite3.IntegrityError) as exc_info2:
                conn.execute("DELETE FROM audit_log")
            assert "audit_log is append-only" in str(exc_info2.value)

        finally:
            conn.close()


def test_foreign_key_enforcement():
    """Verify that SQLite enforces PRAGMA foreign_keys = ON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "CASE_FK_TEST"
        conn = initialize_case_database(
            case_dir,
            {
                "id": "case_fk",
                "case_number": "CASE_FK_01",
                "title": "FK Test",
                "created_by_badge": "IO_01",
            },
        )
        try:
            # Attempting to insert evidence_file referencing non-existent case_id must fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO evidence_files (
                        id, case_id, original_filename, stored_path, sha256,
                        size_bytes, detected_kind, ingested_by_badge, ingested_at
                    ) VALUES ('ev1', 'non_existent_case', 'cdr.csv', 'stored/cdr.csv',
                              'hash123', 100, 'CDR', 'BADGE', '2026-09-21T00:00:00Z')
                    """
                )
        finally:
            conn.close()


def test_provenance_triple_enforcement():
    """Verify that event records reject missing evidence_file_id, source_row, or source_sha256."""
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "CASE_PROV_TEST"
        conn = initialize_case_database(
            case_dir,
            {
                "id": "case_prov",
                "case_number": "CASE_PROV_01",
                "title": "Provenance Test",
                "created_by_badge": "IO_01",
            },
        )
        try:
            # Insert valid evidence file first
            ev_id = repo.insert_evidence_file(
                conn,
                {
                    "case_id": "case_prov",
                    "original_filename": "cdr.csv",
                    "stored_path": "evidence/cdr.csv",
                    "sha256": "f" * 64,
                    "size_bytes": 1024,
                    "detected_kind": "CDR",
                    "ingested_by_badge": "IO_01",
                    "ingested_at": "2026-09-21T10:00:00Z",
                },
            )

            # Missing source_row (NULL) should raise IntegrityError
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO events (
                        id, case_id, event_type, occurred_at, evidence_file_id,
                        source_row, source_sha256, created_at
                    ) VALUES ('ev_1', 'case_prov', 'CALL', '2026-09-21T10:00:00Z', ?, NULL, ?, ?)
                    """,
                    (ev_id, "f" * 64, "2026-09-21T10:00:00Z"),
                )

            # Valid provenance triple succeeds
            conn.execute(
                """
                INSERT INTO events (
                    id, case_id, event_type, occurred_at, evidence_file_id,
                    source_row, source_sha256, created_at
                ) VALUES ('ev_1', 'case_prov', 'CALL', '2026-09-21T10:00:00Z', ?, 42, ?, ?)
                """,
                (ev_id, "f" * 64, "2026-09-21T10:00:00Z"),
            )
            conn.commit()

            events = repo.get_events(conn, "case_prov")
            assert len(events) == 1
            assert events[0]["source_row"] == 42
            assert events[0]["source_sha256"] == "f" * 64

        finally:
            conn.close()


def test_bulk_insert_and_entity_resolution():
    """Verify bulk insertion and entity resolution upsert logic on normalized_value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "CASE_BULK_TEST"
        case_id = "case_bulk"
        conn = initialize_case_database(
            case_dir,
            {
                "id": case_id,
                "case_number": "CASE_BULK_01",
                "title": "Bulk Ingest Test",
                "created_by_badge": "IO_01",
            },
        )
        try:
            ev_id = repo.insert_evidence_file(
                conn,
                {
                    "case_id": case_id,
                    "original_filename": "cdr.csv",
                    "stored_path": "evidence/cdr.csv",
                    "sha256": "a" * 64,
                    "size_bytes": 2048,
                    "detected_kind": "CDR",
                    "ingested_by_badge": "IO_01",
                    "ingested_at": "2026-09-21T10:00:00Z",
                },
            )

            # Round 1: Entities and events
            entities_r1 = [
                {
                    "id": "phone_1",
                    "entity_type": "PHONE",
                    "raw_value": "9876543210",
                    "normalized_value": "+919876543210",
                    "role": "SUSPECT",
                    "occurrences": 1,
                    "first_seen_at": "2026-09-21T10:00:00Z",
                    "last_seen_at": "2026-09-21T10:00:00Z",
                }
            ]
            events_r1 = [
                {
                    "id": "evt_1",
                    "event_type": "CALL",
                    "occurred_at": "2026-09-21T10:00:00Z",
                    "src_entity_id": "phone_1",
                    "source_row": 2,
                    "source_sha256": "a" * 64,
                }
            ]
            rejects_r1 = [
                {
                    "source_row": 3,
                    "raw_line": "corrupt,line,,data",
                    "reason": "Missing required callee field",
                }
            ]

            repo.bulk_insert_events_and_entities(
                conn, case_id, ev_id, events_r1, entities_r1, rejects_r1
            )

            # Check entities
            ents = repo.get_entities(conn, case_id)
            assert len(ents) == 1
            assert ents[0]["normalized_value"] == "+919876543210"
            assert ents[0]["occurrences"] == 1

            # Check rejects
            rejs = repo.get_parse_rejects(conn, ev_id)
            assert len(rejs) == 1
            assert rejs[0]["reason"] == "Missing required callee field"

            # Round 2: Ingest same entity again (e.g. from row 4)
            entities_r2 = [
                {
                    "id": "phone_1_duplicate_id",
                    "entity_type": "PHONE",
                    "raw_value": "09876543210",
                    "normalized_value": "+919876543210",  # Same normalized
                    "role": "UNKNOWN",
                    "occurrences": 1,
                    "first_seen_at": "2026-09-21T10:05:00Z",
                    "last_seen_at": "2026-09-21T10:05:00Z",
                }
            ]
            events_r2 = [
                {
                    "id": "evt_2",
                    "event_type": "CALL",
                    "occurred_at": "2026-09-21T10:05:00Z",
                    "src_entity_id": "phone_1",
                    "source_row": 4,
                    "source_sha256": "a" * 64,
                }
            ]
            repo.bulk_insert_events_and_entities(
                conn, case_id, ev_id, events_r2, entities_r2, []
            )

            # Entity resolution check: STILL 1 entity, occurrences incremented to 2, role preserved
            ents_updated = repo.get_entities(conn, case_id)
            assert len(ents_updated) == 1
            assert ents_updated[0]["occurrences"] == 2
            assert ents_updated[0]["role"] == "SUSPECT"
            assert ents_updated[0]["last_seen_at"] == "2026-09-21T10:05:00Z"

            # Events table has 2 events
            all_events = repo.get_events(conn, case_id)
            assert len(all_events) == 2

        finally:
            conn.close()


def test_audit_hash_chain_walking():
    """Verify audit log sequential chaining and cryptographic walk verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        case_dir = Path(tmpdir) / "CASE_CHAIN_TEST"
        case_id = "case_chain"
        conn = initialize_case_database(
            case_dir,
            {
                "id": case_id,
                "case_number": "CASE_CHAIN_01",
                "title": "Chain Test",
                "created_by_badge": "IO_01",
            },
        )
        try:
            # Genesis is seq 0
            seq_0, hash_0 = repo.get_audit_head(conn, case_id)
            assert seq_0 == 0

            # Append entry seq 1
            e1 = repo.append_audit_entry(
                conn,
                case_id=case_id,
                officer_badge="IO_01",
                officer_name="Inspector Vijay",
                action="EVIDENCE_INGESTED",
                target_type="EVIDENCE_FILE",
                target_id="file_123",
                payload={"filename": "cdr.csv", "sha256": "abc"},
            )
            assert e1["seq"] == 1
            assert e1["prev_hash"] == hash_0

            # Append entry seq 2
            e2 = repo.append_audit_entry(
                conn,
                case_id=case_id,
                officer_badge="IO_01",
                officer_name="Inspector Vijay",
                action="CORRELATION_RUN",
                target_type="GRAPH",
                target_id="graph_1",
                payload={"links_count": 5},
            )
            assert e2["seq"] == 2
            assert e2["prev_hash"] == e1["entry_hash"]

            # Chain verification walk
            chain = repo.get_audit_chain(conn, case_id)
            assert len(chain) == 3
            for i in range(1, len(chain)):
                assert chain[i]["prev_hash"] == chain[i - 1]["entry_hash"]
                assert chain[i]["seq"] == chain[i - 1]["seq"] + 1

        finally:
            conn.close()


def test_case_service_end_to_end():
    """Verify case_service.create_case, list_cases, and get_case with SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cases_root = Path(tmpdir) / "cases"

        case = case_service.create_case(
            case_number="CASE_SVC_001",
            title="Service Integration Case",
            created_by="BADGE_TEST_99",
            created_by_name="Senior IO Sharma",
            cases_root=cases_root,
        )
        assert case.case_number == "CASE_SVC_001"
        assert case.title == "Service Integration Case"

        # Check list_cases
        cases_list = case_service.list_cases()
        matching = [c for c in cases_list if c.case_number == "CASE_SVC_001"]
        assert len(matching) == 1

        # Check get_case
        retrieved = case_service.get_case(case.id)
        assert retrieved is not None
        assert retrieved.case_number == "CASE_SVC_001"
        assert retrieved.created_by_badge == "BADGE_TEST_99"


if __name__ == "__main__":
    test_app_database_schema_and_operations()
    test_case_database_schema_and_genesis()
    test_audit_log_append_only_triggers()
    test_foreign_key_enforcement()
    test_provenance_triple_enforcement()
    test_bulk_insert_and_entity_resolution()
    test_audit_hash_chain_walking()
    test_case_service_end_to_end()
    print("All SQLite tests passed successfully!")
