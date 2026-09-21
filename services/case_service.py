"""
services/case_service.py

Case management service.
Spec: 02_TRD.md §6, 03_App_Flow.md S02-S03, 05_Backend_Schema.md §2.3 & §3.1.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from domain.models import Case
from db.init import (
    get_app_connection,
    get_case_connection,
    initialize_case_database,
    PROJECT_ROOT,
)
from db.repository import (
    register_case,
    list_registered_cases,
    get_registered_case,
    get_case as repo_get_case,
    update_case_last_opened,
)

DEFAULT_CASES_ROOT = PROJECT_ROOT / "cases"


def create_case(
    case_number: str,
    title: str,
    created_by: str,
    fir_number: Optional[str] = None,
    police_station: Optional[str] = None,
    complaint_date: Optional[str] = None,
    description: Optional[str] = None,
    created_by_name: Optional[str] = None,
    cases_root: Optional[Path] = None,
) -> Case:
    """
    Creates a new case folder and case.pramaan SQLite database.
    Writes genesis audit log entry and registers the case in pramaan_app.db.
    """
    root = cases_root or DEFAULT_CASES_ROOT
    root.mkdir(parents=True, exist_ok=True)

    case_folder = root / case_number
    case_folder.mkdir(parents=True, exist_ok=True)

    case_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    officer_name = created_by_name or f"Officer ({created_by})"

    case_payload = {
        "id": case_id,
        "case_number": case_number,
        "title": title,
        "fir_number": fir_number,
        "police_station": police_station,
        "complaint_date": complaint_date,
        "description": description,
        "created_by_badge": created_by,
        "created_by_name": officer_name,
        "created_at": now_iso,
    }

    # 1. Initialize case folder & case.pramaan database (creates tables + genesis audit entry)
    case_conn = initialize_case_database(case_folder, case_payload)
    case_conn.close()

    # 2. Register case in pramaan_app.db:case_registry
    app_conn = get_app_connection()
    try:
        # Check if created_by exists in officers; if not, create a fallback officer row so foreign key succeeds
        off_row = app_conn.execute("SELECT id FROM officers WHERE id = ?", (created_by,)).fetchone()
        if not off_row:
            # Check by badge
            off_row = app_conn.execute("SELECT id FROM officers WHERE badge_no = ?", (created_by,)).fetchone()

        if off_row:
            officer_ref_id = off_row["id"]
        else:
            # Fallback stub officer for foreign key integrity in case_registry
            officer_ref_id = str(uuid.uuid4())
            app_conn.execute(
                """
                INSERT OR IGNORE INTO officers (
                    id, badge_no, full_name, role, password_hash, created_at
                ) VALUES (?, ?, ?, 'IO', 'system_generated', ?)
                """,
                (officer_ref_id, created_by, officer_name, now_iso),
            )
            app_conn.commit()

        register_case(
            app_conn,
            {
                "case_id": case_id,
                "case_number": case_number,
                "title": title,
                "folder_path": str(case_folder.resolve()),
                "created_by": officer_ref_id,
                "created_at": now_iso,
                "status": "OPEN",
            },
        )
    finally:
        app_conn.close()

    return Case(
        id=case_id,
        case_number=case_number,
        title=title,
        fir_number=fir_number,
        police_station=police_station,
        complaint_date=complaint_date,
        description=description,
        created_by_badge=created_by,
        created_by_name=officer_name,
        created_at=now_iso,
        status="OPEN",
        integrity_status="UNVERIFIED",
        schema_version=1,
    )


def list_cases() -> List[Case]:
    """
    Retrieves all registered cases for the Case List screen (S02).
    """
    app_conn = get_app_connection()
    cases: List[Case] = []
    try:
        registry_entries = list_registered_cases(app_conn)
        for entry in registry_entries:
            folder_path = Path(entry["folder_path"])
            db_path = folder_path / "case.pramaan"
            if db_path.exists():
                try:
                    case_conn = get_case_connection(db_path)
                    case_data = repo_get_case(case_conn, entry["case_id"])
                    case_conn.close()
                    if case_data:
                        cases.append(Case(**case_data))
                        continue
                except Exception:
                    pass

            # Fallback to registry data if case file cannot be opened
            cases.append(
                Case(
                    id=entry["case_id"],
                    case_number=entry["case_number"],
                    title=entry["title"],
                    created_by_badge=entry["created_by"],
                    created_by_name="Registered Officer",
                    created_at=entry["created_at"],
                    status=entry.get("status", "OPEN"),
                )
            )
    finally:
        app_conn.close()

    return cases


def get_case(case_id: str) -> Optional[Case]:
    """
    Retrieves a single case by its unique ID or case number.
    Updates last_opened_at in case_registry.
    """
    app_conn = get_app_connection()
    try:
        entry = get_registered_case(app_conn, case_id)
        if not entry:
            return None

        folder_path = Path(entry["folder_path"])
        db_path = folder_path / "case.pramaan"
        if not db_path.exists():
            return None

        case_conn = get_case_connection(db_path)
        case_data = repo_get_case(case_conn, entry["case_id"])
        case_conn.close()

        if case_data:
            now_iso = datetime.now(timezone.utc).isoformat()
            update_case_last_opened(app_conn, entry["case_id"], now_iso)
            return Case(**case_data)
        return None
    finally:
        app_conn.close()
