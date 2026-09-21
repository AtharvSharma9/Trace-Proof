"""
db/repository.py

PRAMAAN SQLite Data Access Layer (DAL) / Repository.
Encapsulates all database interactions for pramaan_app.db and case.pramaan.
Spec: 05_Backend_Schema.md, 02_TRD.md, SERVICES.md.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.integrity.hashing import (
    canonical_json,
    compute_entry_hash,
    hash_payload,
)


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row is not None else None


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[dict]:
    return [dict(r) for r in rows]


# ============================================================
# 1. OFFICERS & SESSIONS (pramaan_app.db)
# ============================================================

def count_officers(conn: sqlite3.Connection) -> int:
    """Check number of registered officers (for S00 first-run check)."""
    row = conn.execute("SELECT COUNT(*) AS cnt FROM officers").fetchone()
    return row["cnt"] if row else 0


def create_officer(conn: sqlite3.Connection, officer: dict) -> str:
    """
    Register a new officer.
    officer dict: {id?, badge_no, full_name, rank, unit, role, password_hash, created_at?}
    """
    officer_id = officer.get("id") or str(uuid.uuid4())
    created_at = officer.get("created_at") or datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO officers (
            id, badge_no, full_name, rank, unit, role,
            password_hash, is_active, failed_attempts,
            locked_until, created_at, last_login_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            officer_id,
            officer["badge_no"],
            officer["full_name"],
            officer.get("rank"),
            officer.get("unit"),
            officer.get("role", "IO"),
            officer["password_hash"],
            officer.get("is_active", 1),
            officer.get("failed_attempts", 0),
            officer.get("locked_until"),
            created_at,
            officer.get("last_login_at"),
        ),
    )
    conn.commit()
    return officer_id


def get_officer_by_badge(conn: sqlite3.Connection, badge_no: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM officers WHERE badge_no = ?", (badge_no,)
    ).fetchone()
    return _row_to_dict(row)


def get_officer_by_id(conn: sqlite3.Connection, officer_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM officers WHERE id = ?", (officer_id,)
    ).fetchone()
    return _row_to_dict(row)


def update_officer_attempts(
    conn: sqlite3.Connection,
    officer_id: str,
    failed_attempts: int,
    locked_until: Optional[str] = None,
) -> None:
    conn.execute(
        """
        UPDATE officers
        SET failed_attempts = ?, locked_until = ?
        WHERE id = ?
        """,
        (failed_attempts, locked_until, officer_id),
    )
    conn.commit()


def record_officer_login(
    conn: sqlite3.Connection,
    officer_id: str,
    last_login_at: str,
) -> None:
    conn.execute(
        """
        UPDATE officers
        SET last_login_at = ?, failed_attempts = 0, locked_until = NULL
        WHERE id = ?
        """,
        (last_login_at, officer_id),
    )
    conn.commit()


def create_session(conn: sqlite3.Connection, session: dict) -> str:
    """
    Store an active session token hash.
    session: {id?, officer_id, token_hash, issued_at, expires_at, last_seen_at, workstation_id}
    """
    sess_id = session.get("id") or str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO sessions (
            id, officer_id, token_hash, issued_at,
            expires_at, last_seen_at, revoked_at, workstation_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sess_id,
            session["officer_id"],
            session["token_hash"],
            session["issued_at"],
            session["expires_at"],
            session["last_seen_at"],
            session.get("revoked_at"),
            session.get("workstation_id", "WS-1"),
        ),
    )
    conn.commit()
    return sess_id


def get_session_by_token_hash(conn: sqlite3.Connection, token_hash: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM sessions WHERE token_hash = ?", (token_hash,)
    ).fetchone()
    return _row_to_dict(row)


def update_session_activity(
    conn: sqlite3.Connection,
    session_id: str,
    last_seen_at: str,
    expires_at: str,
) -> None:
    conn.execute(
        """
        UPDATE sessions
        SET last_seen_at = ?, expires_at = ?
        WHERE id = ?
        """,
        (last_seen_at, expires_at, session_id),
    )
    conn.commit()


def revoke_session(
    conn: sqlite3.Connection,
    session_id: str,
    revoked_at: str,
) -> None:
    conn.execute(
        "UPDATE sessions SET revoked_at = ? WHERE id = ?",
        (revoked_at, session_id),
    )
    conn.commit()


# ============================================================
# 2. CASE REGISTRY (pramaan_app.db)
# ============================================================

def register_case(conn: sqlite3.Connection, case_info: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO case_registry (
            case_id, case_number, title, folder_path,
            created_by, created_at, last_opened_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_info["case_id"],
            case_info["case_number"],
            case_info["title"],
            case_info["folder_path"],
            case_info["created_by"],
            case_info["created_at"],
            case_info.get("last_opened_at"),
            case_info.get("status", "OPEN"),
        ),
    )
    conn.commit()


def list_registered_cases(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM case_registry ORDER BY created_at DESC"
    ).fetchall()
    return _rows_to_dicts(rows)


def get_registered_case(conn: sqlite3.Connection, case_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM case_registry WHERE case_id = ? OR case_number = ?",
        (case_id, case_id),
    ).fetchone()
    return _row_to_dict(row)


def update_case_last_opened(conn: sqlite3.Connection, case_id: str, last_opened_at: str) -> None:
    conn.execute(
        "UPDATE case_registry SET last_opened_at = ? WHERE case_id = ? OR case_number = ?",
        (last_opened_at, case_id, case_id),
    )
    conn.commit()


# ============================================================
# 3. CASE DATABASE OPERATIONS (case.pramaan)
# ============================================================

def get_case(conn: sqlite3.Connection, case_id: Optional[str] = None) -> Optional[dict]:
    if case_id:
        row = conn.execute(
            "SELECT * FROM cases WHERE id = ? OR case_number = ?", (case_id, case_id)
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM cases LIMIT 1").fetchone()
    return _row_to_dict(row)


def update_case_integrity_status(
    conn: sqlite3.Connection,
    case_id: str,
    integrity_status: str,
    last_verified_at: str,
) -> None:
    conn.execute(
        """
        UPDATE cases
        SET integrity_status = ?, last_verified_at = ?
        WHERE id = ?
        """,
        (integrity_status, last_verified_at, case_id),
    )
    conn.commit()


# ============================================================
# 4. EVIDENCE FILES & MAPPINGS (case.pramaan)
# ============================================================

def insert_evidence_file(conn: sqlite3.Connection, evidence: dict) -> str:
    ev_id = evidence.get("id") or str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO evidence_files (
            id, case_id, original_filename, original_path, stored_path,
            sha256, md5, size_bytes, mime_type, detected_kind,
            detection_confidence, mapping_id, rows_total, rows_parsed,
            rows_rejected, parse_status, parse_notes, exclusion_reason,
            ingested_by_badge, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ev_id,
            evidence["case_id"],
            evidence["original_filename"],
            evidence.get("original_path"),
            evidence["stored_path"],
            evidence["sha256"],
            evidence.get("md5"),
            evidence["size_bytes"],
            evidence.get("mime_type"),
            evidence["detected_kind"],
            evidence.get("detection_confidence", 1.0),
            evidence.get("mapping_id"),
            evidence.get("rows_total", 0),
            evidence.get("rows_parsed", 0),
            evidence.get("rows_rejected", 0),
            evidence.get("parse_status", "PENDING"),
            evidence.get("parse_notes"),
            evidence.get("exclusion_reason"),
            evidence["ingested_by_badge"],
            evidence["ingested_at"],
        ),
    )
    conn.commit()
    return ev_id


def get_evidence_file_by_sha(conn: sqlite3.Connection, case_id: str, sha256: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM evidence_files WHERE case_id = ? AND sha256 = ?",
        (case_id, sha256),
    ).fetchone()
    return _row_to_dict(row)


def get_evidence_files(conn: sqlite3.Connection, case_id: str) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM evidence_files WHERE case_id = ? ORDER BY ingested_at ASC",
        (case_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


def update_evidence_parse_status(
    conn: sqlite3.Connection,
    evidence_id: str,
    parse_status: str,
    rows_total: int,
    rows_parsed: int,
    rows_rejected: int,
    parse_notes: Optional[str] = None,
) -> None:
    conn.execute(
        """
        UPDATE evidence_files
        SET parse_status = ?, rows_total = ?, rows_parsed = ?,
            rows_rejected = ?, parse_notes = ?
        WHERE id = ?
        """,
        (parse_status, rows_total, rows_parsed, rows_rejected, parse_notes, evidence_id),
    )
    conn.commit()


def save_column_mapping(conn: sqlite3.Connection, mapping: dict) -> str:
    map_id = mapping.get("id") or str(uuid.uuid4())
    conn.execute(
        """
        INSERT OR REPLACE INTO column_mappings (
            id, case_id, evidence_file_id, detected_kind,
            header_signature, mapping_json, confidence_json,
            datetime_format, auto_generated, confirmed_by_badge,
            confirmed_at, saved_as_plugin
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            map_id,
            mapping["case_id"],
            mapping.get("evidence_file_id"),
            mapping["detected_kind"],
            mapping["header_signature"],
            mapping["mapping_json"] if isinstance(mapping["mapping_json"], str) else json.dumps(mapping["mapping_json"]),
            mapping["confidence_json"] if isinstance(mapping["confidence_json"], str) else json.dumps(mapping["confidence_json"]),
            mapping.get("datetime_format"),
            mapping.get("auto_generated", 1),
            mapping.get("confirmed_by_badge"),
            mapping.get("confirmed_at"),
            mapping.get("saved_as_plugin", 0),
        ),
    )
    conn.commit()
    return map_id


# ============================================================
# 5. BULK INGESTION (ENTITIES, EVENTS, REJECTS)
# ============================================================

def bulk_insert_events_and_entities(
    conn: sqlite3.Connection,
    case_id: str,
    evidence_file_id: str,
    events: List[dict],
    entities: List[dict],
    rejects: List[dict],
) -> None:
    """
    High-throughput bulk ingestion inside a single atomic transaction.
    - Entities are inserted with ON CONFLICT resolution on (case_id, entity_type, normalized_value)
    - Events are inserted with provenance triple (evidence_file_id, source_row, source_sha256)
    - Rejects are recorded into parse_rejects for audit traceability.
    """
    cursor = conn.cursor()

    # 1. Upsert Entities
    entity_sql = """
        INSERT INTO entities (
            id, case_id, entity_type, raw_value, normalized_value,
            label, role, occurrences, first_seen_at, last_seen_at,
            attributes_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(case_id, entity_type, normalized_value) DO UPDATE SET
            occurrences = entities.occurrences + excluded.occurrences,
            last_seen_at = COALESCE(excluded.last_seen_at, entities.last_seen_at),
            role = CASE WHEN entities.role = 'UNKNOWN' THEN excluded.role ELSE entities.role END
    """
    entity_params = [
        (
            ent.get("id") or str(uuid.uuid4()),
            case_id,
            ent["entity_type"],
            ent["raw_value"],
            ent["normalized_value"],
            ent.get("label"),
            ent.get("role", "UNKNOWN"),
            ent.get("occurrences", 1),
            ent.get("first_seen_at"),
            ent.get("last_seen_at"),
            ent.get("attributes_json", "{}") if isinstance(ent.get("attributes_json"), str) else json.dumps(ent.get("attributes_json", {})),
            ent.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )
        for ent in entities
    ]
    cursor.executemany(entity_sql, entity_params)

    # 2. Insert Events
    event_sql = """
        INSERT INTO events (
            id, case_id, event_type, occurred_at, occurred_at_tz,
            src_entity_id, dst_entity_id, device_entity_id, sim_entity_id,
            ip_entity_id, amount, currency, direction, duration_sec,
            channel, reference_no, balance_after, raw_json,
            evidence_file_id, source_row, source_sha256, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    event_params = [
        (
            ev.get("id") or str(uuid.uuid4()),
            case_id,
            ev["event_type"],
            ev["occurred_at"],
            ev.get("occurred_at_tz", "Asia/Kolkata"),
            ev.get("src_entity_id"),
            ev.get("dst_entity_id"),
            ev.get("device_entity_id"),
            ev.get("sim_entity_id"),
            ev.get("ip_entity_id"),
            ev.get("amount"),
            ev.get("currency", "INR"),
            ev.get("direction"),
            ev.get("duration_sec"),
            ev.get("channel"),
            ev.get("reference_no"),
            ev.get("balance_after"),
            ev.get("raw_json") if isinstance(ev.get("raw_json"), str) else json.dumps(ev.get("raw_json", {})),
            evidence_file_id,
            ev["source_row"],
            ev["source_sha256"],
            ev.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )
        for ev in events
    ]
    cursor.executemany(event_sql, event_params)

    # 3. Insert Rejects
    if rejects:
        reject_sql = """
            INSERT INTO parse_rejects (
                id, case_id, evidence_file_id, source_row, raw_line, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        reject_params = [
            (
                rej.get("id") or str(uuid.uuid4()),
                case_id,
                evidence_file_id,
                rej["source_row"],
                rej.get("raw_line"),
                rej.get("reason", "Parse error"),
                rej.get("created_at", now_iso),
            )
            for rej in rejects
        ]
        cursor.executemany(reject_sql, reject_params)

    conn.commit()


def get_entities(conn: sqlite3.Connection, case_id: str, entity_type: Optional[str] = None) -> List[dict]:
    if entity_type:
        rows = conn.execute(
            "SELECT * FROM entities WHERE case_id = ? AND entity_type = ?",
            (case_id, entity_type),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM entities WHERE case_id = ?", (case_id,)
        ).fetchall()
    return _rows_to_dicts(rows)


def get_events(conn: sqlite3.Connection, case_id: str, limit: Optional[int] = None) -> List[dict]:
    query = "SELECT * FROM events WHERE case_id = ? ORDER BY occurred_at ASC"
    if limit:
        query += f" LIMIT {limit}"
    rows = conn.execute(query, (case_id,)).fetchall()
    return _rows_to_dicts(rows)


def get_parse_rejects(conn: sqlite3.Connection, evidence_file_id: str) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM parse_rejects WHERE evidence_file_id = ? ORDER BY source_row ASC",
        (evidence_file_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


# ============================================================
# 6. ENTITY LINKS & GRAPH SNAPSHOTS
# ============================================================

def save_entity_links(conn: sqlite3.Connection, links: List[dict]) -> None:
    """
    Bulk upsert entity links.
    Enforces entity_a_id < entity_b_id for symmetric links.
    """
    sql = """
        INSERT INTO entity_links (
            id, case_id, entity_a_id, entity_b_id, link_type,
            confidence, rationale, support_count, supporting_event_ids,
            total_amount, first_at, last_at, status, dismissed_by_badge,
            dismissal_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(case_id, entity_a_id, entity_b_id, link_type) DO UPDATE SET
            confidence = excluded.confidence,
            rationale = excluded.rationale,
            support_count = excluded.support_count,
            supporting_event_ids = excluded.supporting_event_ids,
            total_amount = excluded.total_amount,
            last_at = excluded.last_at,
            status = excluded.status
    """
    params = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for lk in links:
        a_id = lk["entity_a_id"]
        b_id = lk["entity_b_id"]
        link_type = lk["link_type"]

        # Symmetric ordering convention
        if link_type != "FUND_FLOW" and a_id > b_id:
            a_id, b_id = b_id, a_id

        sup_ids = lk.get("supporting_event_ids", "[]")
        if not isinstance(sup_ids, str):
            sup_ids = json.dumps(sup_ids)

        params.append((
            lk.get("id") or str(uuid.uuid4()),
            lk["case_id"],
            a_id,
            b_id,
            link_type,
            float(lk["confidence"]),
            lk["rationale"],
            lk.get("support_count", 1),
            sup_ids,
            lk.get("total_amount"),
            lk.get("first_at"),
            lk.get("last_at"),
            lk.get("status", "ACTIVE"),
            lk.get("dismissed_by_badge"),
            lk.get("dismissal_reason"),
            lk.get("created_at", now_iso),
        ))

    conn.executemany(sql, params)
    conn.commit()


def get_entity_links(conn: sqlite3.Connection, case_id: str, status: Optional[str] = "ACTIVE") -> List[dict]:
    if status:
        rows = conn.execute(
            "SELECT * FROM entity_links WHERE case_id = ? AND status = ?",
            (case_id, status),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM entity_links WHERE case_id = ?", (case_id,)
        ).fetchall()
    return _rows_to_dicts(rows)


def save_graph_snapshot(conn: sqlite3.Connection, snapshot: dict) -> str:
    snap_id = snapshot.get("id") or str(uuid.uuid4())
    case_id = snapshot["case_id"]

    # Mark old snapshots not current
    conn.execute(
        "UPDATE graph_snapshots SET is_current = 0 WHERE case_id = ?",
        (case_id,),
    )

    metrics_json = snapshot.get("metrics_json", "{}")
    if not isinstance(metrics_json, str):
        metrics_json = json.dumps(metrics_json)

    layout_json = snapshot.get("layout_json")
    if layout_json is not None and not isinstance(layout_json, str):
        layout_json = json.dumps(layout_json)

    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO graph_snapshots (
            id, case_id, node_count, edge_count, metrics_json,
            centrality_k, layout_json, graphml_path, png_path,
            built_at, is_current
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            snap_id,
            case_id,
            snapshot["node_count"],
            snapshot["edge_count"],
            metrics_json,
            snapshot.get("centrality_k"),
            layout_json,
            snapshot.get("graphml_path"),
            snapshot.get("png_path"),
            snapshot.get("built_at", now_iso),
        ),
    )
    conn.commit()
    return snap_id


def get_current_graph_snapshot(conn: sqlite3.Connection, case_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM graph_snapshots WHERE case_id = ? AND is_current = 1 LIMIT 1",
        (case_id,),
    ).fetchone()
    return _row_to_dict(row)


# ============================================================
# 7. RISK SCORES & REASONS
# ============================================================

def save_risk_scores(
    conn: sqlite3.Connection,
    case_id: str,
    scores: List[dict],
    reasons: List[dict],
    evidence_refs: Optional[List[dict]] = None,
) -> None:
    """
    Save risk scores with full reproducibility metadata.
    Sets is_current = 0 on earlier scores for this case.
    """
    conn.execute(
        "UPDATE risk_scores SET is_current = 0 WHERE case_id = ?",
        (case_id,),
    )

    score_sql = """
        INSERT INTO risk_scores (
            id, case_id, entity_id, score, band, rules_score,
            anomaly_score, anomaly_used, rank_in_case, features_json,
            model_version, weights_hash, random_seed, computed_by_badge,
            computed_at, is_current
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """
    score_params = [
        (
            s["id"],
            case_id,
            s["entity_id"],
            float(s["score"]),
            s["band"],
            float(s["rules_score"]),
            s.get("anomaly_score"),
            s.get("anomaly_used", 0),
            s.get("rank_in_case"),
            s["features_json"] if isinstance(s["features_json"], str) else json.dumps(s["features_json"]),
            s.get("model_version", "rules-1.0"),
            s["weights_hash"],
            s.get("random_seed", 42),
            s["computed_by_badge"],
            s.get("computed_at") or datetime.now(timezone.utc).isoformat(),
        )
        for s in scores
    ]
    conn.executemany(score_sql, score_params)

    reason_sql = """
        INSERT INTO risk_reasons (
            id, risk_score_id, rule_code, rule_name, triggered,
            raw_value, threshold, weight, points_contributed,
            plain_text, display_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    reason_params = [
        (
            r.get("id") or str(uuid.uuid4()),
            r["risk_score_id"],
            r["rule_code"],
            r["rule_name"],
            r.get("triggered", 1),
            r.get("raw_value"),
            r.get("threshold"),
            float(r["weight"]),
            float(r["points_contributed"]),
            r["plain_text"],
            r.get("display_order", 0),
        )
        for r in reasons
    ]
    conn.executemany(reason_sql, reason_params)

    if evidence_refs:
        ref_sql = """
            INSERT INTO reason_evidence_refs (
                id, risk_reason_id, event_id, evidence_file_id,
                source_row, source_sha256, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        ref_params = [
            (
                ref.get("id") or str(uuid.uuid4()),
                ref["risk_reason_id"],
                ref.get("event_id"),
                ref["evidence_file_id"],
                ref["source_row"],
                ref["source_sha256"],
                ref.get("note"),
            )
            for ref in evidence_refs
        ]
        conn.executemany(ref_sql, ref_params)

    conn.commit()


def get_current_risk_scores(conn: sqlite3.Connection, case_id: str) -> List[dict]:
    rows = conn.execute(
        """
        SELECT * FROM risk_scores
        WHERE case_id = ? AND is_current = 1
        ORDER BY score DESC
        """,
        (case_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


def get_reasons_for_score(conn: sqlite3.Connection, risk_score_id: str) -> List[dict]:
    rows = conn.execute(
        """
        SELECT * FROM risk_reasons
        WHERE risk_score_id = ?
        ORDER BY display_order ASC
        """,
        (risk_score_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


# ============================================================
# 8. AUDIT LOG & CHAIN INTEGRITY
# ============================================================

def get_audit_head(conn: sqlite3.Connection, case_id: str) -> Tuple[int, str]:
    """
    Returns (latest_seq, latest_entry_hash).
    If no entries exist, returns (-1, '0'*64).
    """
    row = conn.execute(
        """
        SELECT seq, entry_hash
        FROM audit_log
        WHERE case_id = ?
        ORDER BY seq DESC
        LIMIT 1
        """,
        (case_id,),
    ).fetchone()
    if row:
        return row["seq"], row["entry_hash"]
    return -1, "0" * 64


def append_audit_entry(
    conn: sqlite3.Connection,
    case_id: str,
    officer_badge: str,
    officer_name: str,
    action: str,
    target_type: Optional[str],
    target_id: Optional[str],
    payload: dict,
    occurred_at: Optional[str] = None,
) -> dict:
    """
    Append an entry to the hash-chained audit log inside an exclusive transaction.
    """
    latest_seq, prev_hash = get_audit_head(conn, case_id)
    next_seq = latest_seq + 1
    ts = occurred_at or datetime.now(timezone.utc).isoformat()

    p_hash = hash_payload(payload)
    p_json = canonical_json(payload)

    entry_hash = compute_entry_hash(
        prev_hash=prev_hash,
        seq=next_seq,
        occurred_at=ts,
        officer_badge=officer_badge,
        action=action,
        target_type=target_type or "",
        target_id=target_id or "",
        payload_hash=p_hash,
    )

    entry_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO audit_log (
            id, case_id, seq, occurred_at, officer_badge, officer_name,
            action, target_type, target_id, payload_json, payload_hash,
            prev_hash, entry_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry_id,
            case_id,
            next_seq,
            ts,
            officer_badge,
            officer_name,
            action,
            target_type,
            target_id,
            p_json,
            p_hash,
            prev_hash,
            entry_hash,
        ),
    )
    conn.commit()

    return {
        "id": entry_id,
        "case_id": case_id,
        "seq": next_seq,
        "occurred_at": ts,
        "officer_badge": officer_badge,
        "officer_name": officer_name,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "payload_json": p_json,
        "payload_hash": p_hash,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
    }


def get_audit_chain(conn: sqlite3.Connection, case_id: str) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE case_id = ? ORDER BY seq ASC",
        (case_id,),
    ).fetchall()
    return _rows_to_dicts(rows)


# ============================================================
# 9. REPORTS
# ============================================================

def save_report(conn: sqlite3.Connection, report: dict) -> str:
    rep_id = report.get("id") or str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO reports (
            id, case_id, kind, file_path, sha256,
            audit_head_hash, evidence_manifest_json, suspects_json,
            signature, generated_by_badge, generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rep_id,
            report["case_id"],
            report["kind"],
            report["file_path"],
            report["sha256"],
            report["audit_head_hash"],
            report["evidence_manifest_json"] if isinstance(report["evidence_manifest_json"], str) else json.dumps(report["evidence_manifest_json"]),
            report["suspects_json"] if isinstance(report["suspects_json"], str) else json.dumps(report["suspects_json"]),
            report.get("signature"),
            report["generated_by_badge"],
            report.get("generated_at", now_iso),
        ),
    )
    conn.commit()
    return rep_id


def get_reports(conn: sqlite3.Connection, case_id: str) -> List[dict]:
    rows = conn.execute(
        "SELECT * FROM reports WHERE case_id = ? ORDER BY generated_at DESC",
        (case_id,),
    ).fetchall()
    return _rows_to_dicts(rows)
