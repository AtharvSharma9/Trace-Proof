-- ============================================================
-- PRAMAAN - SQLite Database Schema
-- Version: 1.0 MVP
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- 1. USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    role            TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1,

    CHECK (role IN (
        'IO',
        'FORENSIC_ANALYST',
        'SUPERVISOR'
    )),

    CHECK (is_active IN (0, 1))
);


-- ============================================================
-- 2. CASES
-- ============================================================

CREATE TABLE IF NOT EXISTS cases (
    id              TEXT PRIMARY KEY,
    case_number     TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'OPEN',
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,

    CHECK (status IN (
        'OPEN',
        'CLOSED',
        'ARCHIVED'
    )),

    FOREIGN KEY (created_by)
        REFERENCES users(id)
);


-- ============================================================
-- 3. EVIDENCE FILES
-- ============================================================

CREATE TABLE IF NOT EXISTS evidence_files (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL,
    original_filename   TEXT NOT NULL,
    stored_path         TEXT NOT NULL,
    file_type           TEXT NOT NULL,
    mime_type           TEXT,
    file_size           INTEGER NOT NULL,
    sha256              TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'ACTIVE',
    ingested_by         TEXT NOT NULL,
    ingested_at         TEXT NOT NULL,
    excluded_reason     TEXT,

    CHECK (status IN (
        'ACTIVE',
        'EXCLUDED',
        'PARSE_FAILED'
    )),

    CHECK (
        status != 'EXCLUDED'
        OR excluded_reason IS NOT NULL
    ),

    FOREIGN KEY (case_id)
        REFERENCES cases(id),

    FOREIGN KEY (ingested_by)
        REFERENCES users(id)
);


-- ============================================================
-- 4. EVIDENCE ROWS
-- ============================================================

CREATE TABLE IF NOT EXISTS evidence_rows (
    id                  TEXT PRIMARY KEY,
    evidence_file_id    TEXT NOT NULL,
    row_number          INTEGER NOT NULL,
    raw_data            TEXT,
    row_hash            TEXT,
    created_at          TEXT NOT NULL,

    UNIQUE (
        evidence_file_id,
        row_number
    ),

    FOREIGN KEY (evidence_file_id)
        REFERENCES evidence_files(id)
);


-- ============================================================
-- 5. ENTITIES
-- ============================================================

CREATE TABLE IF NOT EXISTS entities (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL,
    entity_type         TEXT NOT NULL,
    value               TEXT NOT NULL,
    normalized_value    TEXT NOT NULL,
    first_seen          TEXT,
    last_seen           TEXT,
    created_at          TEXT NOT NULL,

    CHECK (entity_type IN (
        'PHONE',
        'IMEI',
        'IMSI',
        'UPI',
        'BANK_ACCOUNT',
        'IFSC',
        'IP',
        'MAC',
        'EMAIL',
        'APK_CERT'
    )),

    FOREIGN KEY (case_id)
        REFERENCES cases(id)
);


-- ============================================================
-- 6. EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS events (
    id                      TEXT PRIMARY KEY,
    case_id                 TEXT NOT NULL,
    event_type              TEXT NOT NULL,
    event_time              TEXT,
    source_evidence_row_id  TEXT,
    description             TEXT,
    amount                  REAL,
    currency                TEXT,
    created_at              TEXT NOT NULL,

    CHECK (event_type IN (
        'CALL',
        'TRANSACTION',
        'IP_ACTIVITY',
        'EMAIL',
        'LOGIN',
        'WITHDRAWAL'
    )),

    FOREIGN KEY (case_id)
        REFERENCES cases(id),

    FOREIGN KEY (source_evidence_row_id)
        REFERENCES evidence_rows(id)
);


-- ============================================================
-- 7. EVENT ↔ ENTITY
-- ============================================================

CREATE TABLE IF NOT EXISTS event_entities (
    event_id        TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    role            TEXT NOT NULL,

    PRIMARY KEY (
        event_id,
        entity_id,
        role
    ),

    FOREIGN KEY (event_id)
        REFERENCES events(id),

    FOREIGN KEY (entity_id)
        REFERENCES entities(id)
);


-- ============================================================
-- 8. ENTITY LINKS
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_links (
    id                  TEXT PRIMARY KEY,
    case_id             TEXT NOT NULL,
    entity_a_id         TEXT NOT NULL,
    entity_b_id         TEXT NOT NULL,
    link_type           TEXT NOT NULL,
    confidence          REAL NOT NULL,
    rationale           TEXT NOT NULL,
    created_by_run_id   TEXT,
    created_at          TEXT NOT NULL,

    CHECK (
        confidence >= 0
        AND confidence <= 1
    ),

    CHECK (
        entity_a_id != entity_b_id
    ),

    FOREIGN KEY (case_id)
        REFERENCES cases(id),

    FOREIGN KEY (entity_a_id)
        REFERENCES entities(id),

    FOREIGN KEY (entity_b_id)
        REFERENCES entities(id),

    FOREIGN KEY (created_by_run_id)
        REFERENCES analysis_runs(id)
);


-- ============================================================
-- 9. LINK ↔ EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS link_evidence (
    link_id             TEXT NOT NULL,
    evidence_row_id     TEXT NOT NULL,

    PRIMARY KEY (
        link_id,
        evidence_row_id
    ),

    FOREIGN KEY (link_id)
        REFERENCES entity_links(id),

    FOREIGN KEY (evidence_row_id)
        REFERENCES evidence_rows(id)
);


-- ============================================================
-- 10. ANALYSIS RUNS
-- ============================================================

CREATE TABLE IF NOT EXISTS analysis_runs (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL,
    run_type        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT NOT NULL,
    parameters_json TEXT,
    created_by      TEXT NOT NULL,

    CHECK (run_type IN (
        'INGESTION',
        'CORRELATION',
        'RISK_SCORING',
        'INTEGRITY_CHECK',
        'REPORT_GENERATION'
    )),

    CHECK (status IN (
        'RUNNING',
        'COMPLETED',
        'FAILED',
        'CANCELLED'
    )),

    FOREIGN KEY (case_id)
        REFERENCES cases(id),

    FOREIGN KEY (created_by)
        REFERENCES users(id)
);


-- ============================================================
-- 11. RISK SCORES
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_scores (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL,
    entity_id       TEXT NOT NULL,
    score           REAL NOT NULL,
    rule_score      REAL,
    ml_score        REAL,
    ml_enabled      INTEGER NOT NULL,
    analysis_run_id TEXT NOT NULL,
    calculated_at   TEXT NOT NULL,

    CHECK (
        score >= 0
        AND score <= 100
    ),

    CHECK (ml_enabled IN (0, 1)),

    FOREIGN KEY (case_id)
        REFERENCES cases(id),

    FOREIGN KEY (entity_id)
        REFERENCES entities(id),

    FOREIGN KEY (analysis_run_id)
        REFERENCES analysis_runs(id)
);


-- ============================================================
-- 12. RISK REASONS
-- ============================================================

CREATE TABLE IF NOT EXISTS risk_reasons (
    id              TEXT PRIMARY KEY,
    risk_score_id   TEXT NOT NULL,
    rule_code       TEXT NOT NULL,
    reason_text     TEXT NOT NULL,
    weight          REAL NOT NULL,
    created_at      TEXT NOT NULL,

    FOREIGN KEY (risk_score_id)
        REFERENCES risk_scores(id)
);


-- ============================================================
-- 13. REASON ↔ EVIDENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS reason_evidence (
    reason_id       TEXT NOT NULL,
    evidence_row_id TEXT NOT NULL,

    PRIMARY KEY (
        reason_id,
        evidence_row_id
    ),

    FOREIGN KEY (reason_id)
        REFERENCES risk_reasons(id),

    FOREIGN KEY (evidence_row_id)
        REFERENCES evidence_rows(id)
);


-- ============================================================
-- 14. AUDIT LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    sequence        INTEGER PRIMARY KEY,
    case_id         TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    action          TEXT NOT NULL,
    object_type     TEXT,
    object_id       TEXT,
    timestamp       TEXT NOT NULL,
    details_json    TEXT,
    previous_hash   TEXT NOT NULL,
    entry_hash      TEXT NOT NULL,

    FOREIGN KEY (case_id)
        REFERENCES cases(id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
);


-- ============================================================
-- INDEXES
-- ============================================================

-- Evidence
CREATE INDEX IF NOT EXISTS idx_evidence_case
    ON evidence_files(case_id);

CREATE INDEX IF NOT EXISTS idx_evidence_sha256
    ON evidence_files(sha256);

-- Evidence rows
CREATE INDEX IF NOT EXISTS idx_evidence_rows_file
    ON evidence_rows(evidence_file_id);

CREATE INDEX IF NOT EXISTS idx_evidence_rows_hash
    ON evidence_rows(row_hash);

-- Entities
CREATE INDEX IF NOT EXISTS idx_entities_case
    ON entities(case_id);

CREATE INDEX IF NOT EXISTS idx_entities_type
    ON entities(case_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_entities_normalized
    ON entities(case_id, normalized_value);

-- Events
CREATE INDEX IF NOT EXISTS idx_events_case
    ON events(case_id);

CREATE INDEX IF NOT EXISTS idx_events_time
    ON events(case_id, event_time);

CREATE INDEX IF NOT EXISTS idx_events_type
    ON events(case_id, event_type);

-- Entity links
CREATE INDEX IF NOT EXISTS idx_links_case
    ON entity_links(case_id);

CREATE INDEX IF NOT EXISTS idx_links_entity_a
    ON entity_links(entity_a_id);

CREATE INDEX IF NOT EXISTS idx_links_entity_b
    ON entity_links(entity_b_id);

-- Risk
CREATE INDEX IF NOT EXISTS idx_risk_entity
    ON risk_scores(entity_id);

CREATE INDEX IF NOT EXISTS idx_risk_score
    ON risk_scores(case_id, score DESC);

-- Audit
CREATE INDEX IF NOT EXISTS idx_audit_case
    ON audit_log(case_id);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON audit_log(case_id, timestamp);
