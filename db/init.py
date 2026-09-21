from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from engine.integrity.hashing import (
    canonical_json,
    compute_entry_hash,
    hash_payload,
)


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

DB_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DB_DIR.parent
SCHEMA_APP_PATH = DB_DIR / "schema_app.sql"
SCHEMA_CASE_PATH = DB_DIR / "schema_case.sql"
DEFAULT_APP_DB_PATH = PROJECT_ROOT / "pramaan_app.db"


# ------------------------------------------------------------
# SQLite configuration
# ------------------------------------------------------------

def configure_connection(connection: sqlite3.Connection) -> None:
    """
    Configure a SQLite connection for PRAMAAN.
    Enforces foreign keys, WAL concurrency mode, synchronous FULL durability,
    busy timeout of 5000ms, and Row factory.
    """
    # Enforce foreign-key relationships.
    connection.execute("PRAGMA foreign_keys = ON;")

    # WAL improves read/write concurrency.
    connection.execute("PRAGMA journal_mode = WAL;")

    # synchronous = FULL guarantees crash durability for forensic logs.
    connection.execute("PRAGMA synchronous = FULL;")

    # Wait up to 5000ms when the database is locked.
    connection.execute("PRAGMA busy_timeout = 5000;")

    # Return rows that can be accessed by column name.
    connection.row_factory = sqlite3.Row


# ------------------------------------------------------------
# Application database (pramaan_app.db)
# ------------------------------------------------------------

def get_app_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Open or create the workstation-level pramaan_app.db connection.
    If the database is new or empty, it initializes the schema.
    """
    path = Path(db_path) if db_path else DEFAULT_APP_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    is_new = not path.exists() or path.stat().st_size == 0
    connection = sqlite3.connect(path, timeout=5.0)
    configure_connection(connection)

    if is_new:
        if SCHEMA_APP_PATH.exists():
            schema = SCHEMA_APP_PATH.read_text(encoding="utf-8")
            connection.executescript(schema)
            connection.commit()

    return connection


def initialize_app_database(db_path: str | Path | None = None) -> sqlite3.Connection:
    """
    Explicitly initialize or migrate the pramaan_app.db database schema.
    """
    if not SCHEMA_APP_PATH.exists():
        raise FileNotFoundError(f"App database schema not found: {SCHEMA_APP_PATH}")

    path = Path(db_path) if db_path else DEFAULT_APP_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=5.0)
    configure_connection(connection)

    try:
        schema = SCHEMA_APP_PATH.read_text(encoding="utf-8")
        connection.executescript(schema)
        connection.commit()
        return connection
    except Exception:
        connection.rollback()
        connection.close()
        raise


def verify_app_database(connection: sqlite3.Connection) -> bool:
    """
    Verify that all required tables for pramaan_app.db exist.
    """
    required_tables = {
        "officers",
        "sessions",
        "case_registry",
        "format_plugins",
    }
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    existing = {row["name"] for row in rows}
    return required_tables.issubset(existing)


# ------------------------------------------------------------
# Case database (<case_folder>/case.pramaan)
# ------------------------------------------------------------

def get_case_connection(db_path: str | Path) -> sqlite3.Connection:
    """
    Open an existing case SQLite database.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=5.0)
    configure_connection(connection)
    return connection


def initialize_case_database(
    case_target: str | Path,
    case_data: Optional[dict] = None,
) -> sqlite3.Connection:
    """
    Create and initialize a PRAMAAN case directory and case.pramaan database.

    Args:
        case_target: Path to either the case folder or directly to case.pramaan.
        case_data: Dict containing case metadata:
            {
                "id": str,
                "case_number": str,
                "title": str,
                "fir_number": Optional[str],
                "police_station": Optional[str],
                "complaint_date": Optional[str],
                "description": Optional[str],
                "created_by_badge": str,
                "created_by_name": str,
                "created_at": Optional[str],
            }
    """
    if not SCHEMA_CASE_PATH.exists():
        raise FileNotFoundError(f"Case schema not found: {SCHEMA_CASE_PATH}")

    target = Path(case_target)
    if target.suffix == ".pramaan":
        case_db_path = target
        case_dir = target.parent
    else:
        case_dir = target
        case_db_path = case_dir / "case.pramaan"

    # 1. Create standard case folder structure per 02_TRD.md §6
    (case_dir / "evidence").mkdir(parents=True, exist_ok=True)
    (case_dir / "staging").mkdir(parents=True, exist_ok=True)
    (case_dir / "exports").mkdir(parents=True, exist_ok=True)

    log_path = case_dir / "app.log"
    if not log_path.exists():
        log_path.touch()

    # 2. Open DB and apply schema
    connection = sqlite3.connect(case_db_path, timeout=5.0)
    configure_connection(connection)

    try:
        schema = SCHEMA_CASE_PATH.read_text(encoding="utf-8")
        connection.executescript(schema)

        now_iso = datetime.now(timezone.utc).isoformat()

        # 3. Insert case record if provided
        if case_data:
            case_id = case_data.get("id") or str(uuid.uuid4())
            case_number = case_data["case_number"]
            title = case_data.get("title", case_number)
            badge = case_data.get("created_by_badge", "UNKNOWN")
            officer_name = case_data.get("created_by_name", "Investigating Officer")
            created_at = case_data.get("created_at", now_iso)

            connection.execute(
                """
                INSERT OR REPLACE INTO cases (
                    id, case_number, title, fir_number, police_station,
                    complaint_date, description, created_by_badge,
                    created_by_name, created_at, status, integrity_status,
                    schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 'UNVERIFIED', 1)
                """,
                (
                    case_id,
                    case_number,
                    title,
                    case_data.get("fir_number"),
                    case_data.get("police_station"),
                    case_data.get("complaint_date"),
                    case_data.get("description"),
                    badge,
                    officer_name,
                    created_at,
                ),
            )

            # 4. Insert Genesis Audit Log Entry if not present
            has_genesis = connection.execute(
                "SELECT 1 FROM audit_log WHERE case_id = ? AND seq = 0", (case_id,)
            ).fetchone()

            entry_hash = "0" * 64
            if not has_genesis:
                genesis_prev_hash = "0" * 64
                genesis_payload = {
                    "case_id": case_id,
                    "case_number": case_number,
                    "title": title,
                    "created_by": badge,
                }
                p_hash = hash_payload(genesis_payload)
                entry_hash = compute_entry_hash(
                    prev_hash=genesis_prev_hash,
                    seq=0,
                    occurred_at=created_at,
                    officer_badge=badge,
                    action="CASE_CREATED",
                    target_type="CASE",
                    target_id=case_id,
                    payload_hash=p_hash,
                )

                connection.execute(
                    """
                    INSERT INTO audit_log (
                        id, case_id, seq, occurred_at, officer_badge, officer_name,
                        action, target_type, target_id, payload_json, payload_hash,
                        prev_hash, entry_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        case_id,
                        0,
                        created_at,
                        badge,
                        officer_name,
                        "CASE_CREATED",
                        "CASE",
                        case_id,
                        canonical_json(genesis_payload),
                        p_hash,
                        genesis_prev_hash,
                        entry_hash,
                    ),
                )
            else:
                head_row = connection.execute(
                    "SELECT entry_hash FROM audit_log WHERE case_id = ? ORDER BY seq DESC LIMIT 1",
                    (case_id,),
                ).fetchone()
                if head_row:
                    entry_hash = head_row["entry_hash"]

            # 5. Initialize manifest.json
            manifest_path = case_dir / "manifest.json"
            manifest_content = {
                "case_id": case_id,
                "case_number": case_number,
                "created_at": created_at,
                "audit_head_hash": entry_hash,
                "files": {},
            }
            manifest_path.write_text(json.dumps(manifest_content, indent=2), encoding="utf-8")

        connection.commit()
        return connection

    except Exception:
        connection.rollback()
        connection.close()
        raise


def verify_case_database(connection: sqlite3.Connection) -> bool:
    """
    Verify that all 14 essential tables for case.pramaan exist.
    """
    required_tables = {
        "cases",
        "evidence_files",
        "column_mappings",
        "entities",
        "events",
        "parse_rejects",
        "entity_links",
        "risk_scores",
        "risk_reasons",
        "reason_evidence_refs",
        "graph_snapshots",
        "audit_log",
        "notes",
        "reports",
    }
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    existing = {row["name"] for row in rows}
    return required_tables.issubset(existing)


# ------------------------------------------------------------
# Backwards Compatibility Aliases
# ------------------------------------------------------------

def get_connection(db_path: str | Path) -> sqlite3.Connection:
    return get_case_connection(db_path)


def initialize_database(db_path: str | Path) -> sqlite3.Connection:
    return initialize_case_database(db_path)


def verify_database(connection: sqlite3.Connection) -> bool:
    return verify_case_database(connection)


def close_connection(connection: sqlite3.Connection) -> None:
    """
    Safely close a database connection.
    """
    if connection:
        try:
            connection.close()
        except Exception:
            pass
