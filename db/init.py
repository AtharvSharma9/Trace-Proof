from __future__ import annotations

import sqlite3
from pathlib import Path


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

DB_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DB_DIR / "schema.sql"


# ------------------------------------------------------------
# SQLite configuration
# ------------------------------------------------------------

def configure_connection(connection: sqlite3.Connection) -> None:
    """
    Configure a SQLite connection for PRAMAAN.

    This function is called every time a connection is opened.
    """

    # Enforce foreign-key relationships.
    connection.execute("PRAGMA foreign_keys = ON")

    # WAL improves read/write concurrency.
    connection.execute("PRAGMA journal_mode = WAL")

    # Wait briefly when the database is temporarily locked.
    connection.execute("PRAGMA busy_timeout = 5000")

    # Return rows that can be accessed by column name.
    connection.row_factory = sqlite3.Row


# ------------------------------------------------------------
# Open database
# ------------------------------------------------------------

def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """
    Open an existing PRAMAAN SQLite database.

    If the database does not exist, SQLite creates the file.
    """

    path = Path(db_path)

    # Make sure the parent directory exists.
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        path,
        timeout=5.0,
    )

    configure_connection(connection)

    return connection


# ------------------------------------------------------------
# Initialize database
# ------------------------------------------------------------

def initialize_database(
    db_path: str | Path,
) -> sqlite3.Connection:
    """
    Create and initialize a PRAMAAN case database.

    The schema is loaded from db/schema.sql.
    """

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Database schema not found: {SCHEMA_PATH}"
        )

    connection = get_connection(db_path)

    try:
        schema = SCHEMA_PATH.read_text(
            encoding="utf-8"
        )

        connection.executescript(schema)

        connection.commit()

        return connection

    except Exception:
        connection.rollback()
        connection.close()
        raise


# ------------------------------------------------------------
# Verify database
# ------------------------------------------------------------

def verify_database(
    connection: sqlite3.Connection,
) -> bool:
    """
    Verify that the essential PRAMAAN tables exist.
    """

    required_tables = {
        "users",
        "cases",
        "evidence_files",
        "evidence_rows",
        "entities",
        "events",
        "event_entities",
        "analysis_runs",
        "entity_links",
        "link_evidence",
        "risk_scores",
        "risk_reasons",
        "reason_evidence",
        "audit_log",
    }

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    existing_tables = {
        row["name"]
        for row in rows
    }

    return required_tables.issubset(existing_tables)


# ------------------------------------------------------------
# Close database
# ------------------------------------------------------------

def close_connection(
    connection: sqlite3.Connection,
) -> None:
    """
    Safely close a PRAMAAN database connection.
    """

    connection.close()
