-- ============================================================
-- PRAMAAN - Workstation Application Database Schema (pramaan_app.db)
-- Spec: 05_Backend_Schema.md §2
-- ============================================================

PRAGMA foreign_keys = ON;

-- 2.1 officers
CREATE TABLE IF NOT EXISTS officers (
    id              TEXT PRIMARY KEY,              -- UUIDv4
    badge_no        TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    rank            TEXT,
    unit            TEXT,
    role            TEXT NOT NULL DEFAULT 'IO'
                    CHECK (role IN ('IO','ANALYST','SUPERVISOR')),
    password_hash   TEXT NOT NULL,                 -- argon2id encoded string
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,                          -- ISO-8601 UTC, NULL if not locked
    created_at      TEXT NOT NULL,
    last_login_at   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_officers_badge ON officers(badge_no);

-- 2.2 sessions
CREATE TABLE IF NOT EXISTS sessions (
    id             TEXT PRIMARY KEY,
    officer_id     TEXT NOT NULL REFERENCES officers(id) ON DELETE CASCADE,
    token_hash     TEXT NOT NULL UNIQUE,   -- SHA-256 of the session token, never the token
    issued_at      TEXT NOT NULL,
    expires_at     TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL,
    revoked_at     TEXT,
    workstation_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_officer ON sessions(officer_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry  ON sessions(expires_at);

-- 2.3 case_registry
CREATE TABLE IF NOT EXISTS case_registry (
    case_id        TEXT PRIMARY KEY,
    case_number    TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    folder_path    TEXT NOT NULL,
    created_by     TEXT NOT NULL REFERENCES officers(id),
    created_at     TEXT NOT NULL,
    last_opened_at TEXT,
    status         TEXT NOT NULL DEFAULT 'OPEN'
                   CHECK (status IN ('OPEN','UNDER_REVIEW','CLOSED'))
);
CREATE INDEX IF NOT EXISTS idx_case_registry_number ON case_registry(case_number);

-- 2.4 format_plugins
CREATE TABLE IF NOT EXISTS format_plugins (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    kind             TEXT NOT NULL
                     CHECK (kind IN ('CDR','IPDR','BANK','UPI','EML','ANDROID_DUMP','APK','OTHER')),
    header_signature TEXT NOT NULL,   -- sorted, normalised header list, joined — the fingerprint
    mapping_yaml     TEXT NOT NULL,
    times_used       INTEGER NOT NULL DEFAULT 0,
    created_by       TEXT REFERENCES officers(id),
    created_at       TEXT NOT NULL,
    is_builtin       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_format_signature ON format_plugins(header_signature);
