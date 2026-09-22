-- ============================================================
-- PRAMAAN - Case Database Schema (<case_folder>/case.pramaan)
-- Spec: 05_Backend_Schema.md §3
-- ============================================================

PRAGMA foreign_keys = ON;

-- 3.1 cases
CREATE TABLE IF NOT EXISTS cases (
    id               TEXT PRIMARY KEY,
    case_number      TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    fir_number       TEXT,
    police_station   TEXT,
    complaint_date   TEXT,
    description      TEXT,
    created_by_badge TEXT NOT NULL,      -- denormalised: case file must be readable standalone
    created_by_name  TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'OPEN'
                     CHECK (status IN ('OPEN','UNDER_REVIEW','CLOSED')),
    integrity_status TEXT NOT NULL DEFAULT 'UNVERIFIED'
                     CHECK (integrity_status IN ('UNVERIFIED','VERIFIED','COMPROMISED')),
    last_verified_at TEXT,
    schema_version   INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_cases_number ON cases(case_number);

-- 3.2 evidence_files
CREATE TABLE IF NOT EXISTS evidence_files (
    id                   TEXT PRIMARY KEY,
    case_id              TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    original_filename    TEXT NOT NULL,
    original_path        TEXT,
    stored_path          TEXT NOT NULL,        -- relative to the case folder
    sha256               TEXT NOT NULL,        -- 64 lowercase hex chars
    md5                  TEXT,                 -- legacy cross-check for older forensic workflows
    size_bytes           INTEGER NOT NULL CHECK (size_bytes >= 0),
    mime_type            TEXT,
    detected_kind        TEXT NOT NULL
                         CHECK (detected_kind IN ('CDR','IPDR','BANK','UPI','EML',
                                                  'ANDROID_DUMP','APK','UNKNOWN')),
    detection_confidence REAL CHECK (detection_confidence BETWEEN 0 AND 1),
    mapping_id           TEXT REFERENCES column_mappings(id),
    rows_total           INTEGER DEFAULT 0,
    rows_parsed          INTEGER DEFAULT 0,
    rows_rejected        INTEGER DEFAULT 0,
    parse_status         TEXT NOT NULL DEFAULT 'PENDING'
                         CHECK (parse_status IN ('PENDING','MAPPED','PARSED','FAILED','EXCLUDED')),
    parse_notes          TEXT,
    exclusion_reason     TEXT,
    ingested_by_badge    TEXT NOT NULL,
    ingested_at          TEXT NOT NULL,
    UNIQUE (case_id, sha256)               -- same file cannot be ingested twice into one case
);
CREATE INDEX IF NOT EXISTS idx_evidence_case   ON evidence_files(case_id);
CREATE INDEX IF NOT EXISTS idx_evidence_sha    ON evidence_files(sha256);
CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence_files(case_id, parse_status);

-- 3.3 column_mappings
CREATE TABLE IF NOT EXISTS column_mappings (
    id                 TEXT PRIMARY KEY,
    case_id            TEXT NOT NULL REFERENCES cases(id),
    evidence_file_id   TEXT REFERENCES evidence_files(id),
    detected_kind      TEXT NOT NULL,
    header_signature   TEXT NOT NULL,
    mapping_json       TEXT NOT NULL,   -- {"A-PARTY NO":"caller","B-PARTY NO":"callee",...}
    confidence_json    TEXT NOT NULL,   -- {"caller":0.94,"callee":0.91,...}
    datetime_format    TEXT,
    auto_generated     INTEGER NOT NULL DEFAULT 1,
    confirmed_by_badge TEXT,
    confirmed_at       TEXT,
    saved_as_plugin    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_mapping_case ON column_mappings(case_id);

-- 3.4 entities
CREATE TABLE IF NOT EXISTS entities (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    entity_type      TEXT NOT NULL
                     CHECK (entity_type IN ('PHONE','IMEI','IMSI','UPI_HANDLE','BANK_ACCOUNT',
                                            'IFSC','IP','MAC','EMAIL','DEVICE_ID','APK_CERT',
                                            'ATM_ID','MERCHANT_ID')),
    raw_value        TEXT NOT NULL,
    normalized_value TEXT NOT NULL,   -- E.164 for phones, lowercase for UPI/email, etc.
    label            TEXT,            -- optional officer-assigned label
    role             TEXT CHECK (role IN ('VICTIM','SUSPECT','MULE','CASHOUT','INTERMEDIARY',
                                          'UNKNOWN')) DEFAULT 'UNKNOWN',
    occurrences      INTEGER NOT NULL DEFAULT 0,
    first_seen_at    TEXT,
    last_seen_at     TEXT,
    attributes_json  TEXT DEFAULT '{}', -- bank name, operator, account-open date, device model
    created_at       TEXT NOT NULL,
    UNIQUE (case_id, entity_type, normalized_value)
);
CREATE INDEX IF NOT EXISTS idx_entities_case_type ON entities(case_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_norm      ON entities(normalized_value);
CREATE INDEX IF NOT EXISTS idx_entities_role      ON entities(case_id, role);

-- 3.5 events
CREATE TABLE IF NOT EXISTS events (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    event_type       TEXT NOT NULL
                     CHECK (event_type IN ('CALL','SMS','DATA_SESSION','TRANSFER','UPI_TXN',
                                           'ATM_WITHDRAWAL','LOGIN','EMAIL','APP_INSTALL',
                                           'DEVICE_EVENT')),
    occurred_at      TEXT NOT NULL,          -- ISO-8601 UTC
    occurred_at_tz   TEXT DEFAULT 'Asia/Kolkata',
    src_entity_id    TEXT REFERENCES entities(id),
    dst_entity_id    TEXT REFERENCES entities(id),
    device_entity_id TEXT REFERENCES entities(id),   -- IMEI / device used
    sim_entity_id    TEXT REFERENCES entities(id),   -- IMSI used
    ip_entity_id     TEXT REFERENCES entities(id),
    amount           REAL CHECK (amount IS NULL OR amount >= 0),
    currency         TEXT DEFAULT 'INR',
    direction        TEXT CHECK (direction IN ('IN','OUT','INTERNAL')),
    duration_sec     INTEGER CHECK (duration_sec IS NULL OR duration_sec >= 0),
    channel          TEXT,                   -- UPI, IMPS, NEFT, ATM, POS, VOICE, SMS
    reference_no     TEXT,                   -- UTR / RRN / transaction reference
    balance_after    REAL,
    raw_json         TEXT,                   -- the original row, verbatim
    -- provenance triple: NOT NULL, enforced in the domain model as well
    evidence_file_id TEXT NOT NULL REFERENCES evidence_files(id),
    source_row       INTEGER NOT NULL CHECK (source_row > 0),
    source_sha256    TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_case_time ON events(case_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_src       ON events(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_events_dst       ON events(dst_entity_id);
CREATE INDEX IF NOT EXISTS idx_events_type      ON events(case_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_device    ON events(device_entity_id);
CREATE INDEX IF NOT EXISTS idx_events_amount    ON events(case_id, amount) WHERE amount IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_evidence  ON events(evidence_file_id, source_row);

-- 3.6 parse_rejects
CREATE TABLE IF NOT EXISTS parse_rejects (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id),
    evidence_file_id TEXT NOT NULL REFERENCES evidence_files(id),
    source_row       INTEGER NOT NULL,
    raw_line         TEXT,
    reason           TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rejects_file ON parse_rejects(evidence_file_id);

-- 3.7 entity_links
CREATE TABLE IF NOT EXISTS entity_links (
    id                   TEXT PRIMARY KEY,
    case_id              TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    entity_a_id          TEXT NOT NULL REFERENCES entities(id),
    entity_b_id          TEXT NOT NULL REFERENCES entities(id),
    link_type            TEXT NOT NULL
                         CHECK (link_type IN ('SHARED_IMEI','SHARED_IMSI','SHARED_DEVICE',
                                              'SHARED_IP_SUBNET','SHARED_MAC','RECURRING_BENEFICIARY',
                                              'FUND_FLOW','SHARED_APK_CERT','TEMPORAL_PROXIMITY',
                                              'SHARED_EMAIL_DOMAIN')),
    confidence           REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    rationale            TEXT NOT NULL,        -- human-readable, goes straight into the brief
    support_count        INTEGER NOT NULL DEFAULT 1,
    supporting_event_ids TEXT,                 -- JSON array of event ids
    total_amount         REAL,                 -- for FUND_FLOW edges
    first_at             TEXT,
    last_at              TEXT,
    status               TEXT NOT NULL DEFAULT 'ACTIVE'
                         CHECK (status IN ('ACTIVE','DISMISSED')),
    dismissed_by_badge   TEXT,
    dismissal_reason     TEXT,
    created_at           TEXT NOT NULL,
    CHECK (entity_a_id <> entity_b_id),
    UNIQUE (case_id, entity_a_id, entity_b_id, link_type)
);
CREATE INDEX IF NOT EXISTS idx_links_case ON entity_links(case_id, status);
CREATE INDEX IF NOT EXISTS idx_links_a    ON entity_links(entity_a_id);
CREATE INDEX IF NOT EXISTS idx_links_b    ON entity_links(entity_b_id);

-- 3.8 risk_scores
CREATE TABLE IF NOT EXISTS risk_scores (
    id                TEXT PRIMARY KEY,
    case_id           TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    entity_id         TEXT NOT NULL REFERENCES entities(id),
    score             REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
    band              TEXT NOT NULL CHECK (band IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    rules_score       REAL NOT NULL CHECK (rules_score BETWEEN 0 AND 100),
    anomaly_score     REAL CHECK (anomaly_score BETWEEN 0 AND 1),
    anomaly_used      INTEGER NOT NULL DEFAULT 0 CHECK (anomaly_used IN (0,1)),
    rank_in_case      INTEGER,
    features_json     TEXT NOT NULL,        -- full feature vector, for reproducibility
    model_version     TEXT NOT NULL,        -- e.g. "rules-1.0+iforest-1.0"
    weights_hash      TEXT NOT NULL,        -- SHA-256 of the weights config in force
    random_seed       INTEGER,
    computed_by_badge TEXT NOT NULL,
    computed_at       TEXT NOT NULL,
    is_current        INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1))
);
CREATE INDEX IF NOT EXISTS idx_risk_case_current ON risk_scores(case_id, is_current, score DESC);
CREATE INDEX IF NOT EXISTS idx_risk_entity       ON risk_scores(entity_id, is_current);

-- 3.9 risk_reasons
CREATE TABLE IF NOT EXISTS risk_reasons (
    id                 TEXT PRIMARY KEY,
    risk_score_id      TEXT NOT NULL REFERENCES risk_scores(id) ON DELETE CASCADE,
    rule_code          TEXT NOT NULL,        -- R01 … R12
    rule_name          TEXT NOT NULL,
    triggered          INTEGER NOT NULL CHECK (triggered IN (0,1)),
    raw_value          REAL,                 -- the measured value, e.g. 0.96
    threshold          REAL,                 -- the threshold it crossed
    weight             REAL NOT NULL,
    points_contributed REAL NOT NULL,
    plain_text         TEXT NOT NULL,        -- "Forwarded 96% of credited funds within 11 minutes"
    display_order      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reasons_score ON risk_reasons(risk_score_id, display_order);

-- 3.10 reason_evidence_refs
CREATE TABLE IF NOT EXISTS reason_evidence_refs (
    id               TEXT PRIMARY KEY,
    risk_reason_id   TEXT NOT NULL REFERENCES risk_reasons(id) ON DELETE CASCADE,
    event_id         TEXT REFERENCES events(id),
    evidence_file_id TEXT NOT NULL REFERENCES evidence_files(id),
    source_row       INTEGER NOT NULL,
    source_sha256    TEXT NOT NULL,
    note             TEXT
);
CREATE INDEX IF NOT EXISTS idx_refs_reason ON reason_evidence_refs(risk_reason_id);

-- 3.11 graph_snapshots
CREATE TABLE IF NOT EXISTS graph_snapshots (
    id           TEXT PRIMARY KEY,
    case_id      TEXT NOT NULL REFERENCES cases(id),
    node_count   INTEGER NOT NULL,
    edge_count   INTEGER NOT NULL,
    metrics_json TEXT NOT NULL,   -- pagerank, betweenness, degree, per node id
    centrality_k INTEGER,         -- k used for approximate betweenness, NULL if exact
    layout_json  TEXT,            -- cached node positions, so the graph looks stable
    graphml_path TEXT,
    png_path     TEXT,
    built_at     TEXT NOT NULL,
    is_current   INTEGER NOT NULL DEFAULT 1
);

-- 3.12 audit_log (append-only, hash-chained)
CREATE TABLE IF NOT EXISTS audit_log (
    id            TEXT PRIMARY KEY,
    case_id       TEXT NOT NULL REFERENCES cases(id),
    seq           INTEGER NOT NULL,          -- 0 = genesis, strictly incrementing, no gaps
    occurred_at   TEXT NOT NULL,
    officer_badge TEXT NOT NULL,
    officer_name  TEXT NOT NULL,
    action        TEXT NOT NULL,
    target_type   TEXT,
    target_id     TEXT,
    payload_json  TEXT NOT NULL DEFAULT '{}',
    payload_hash  TEXT NOT NULL,             -- SHA-256 of canonical JSON (sorted keys, no spaces)
    prev_hash     TEXT NOT NULL,             -- 64 zeros for genesis
    entry_hash    TEXT NOT NULL UNIQUE,
    UNIQUE (case_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_audit_case_seq ON audit_log(case_id, seq);
CREATE INDEX IF NOT EXISTS idx_audit_action   ON audit_log(case_id, action);

-- Append-only enforcement triggers
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

-- 3.13 notes
CREATE TABLE IF NOT EXISTS notes (
    id           TEXT PRIMARY KEY,
    case_id      TEXT NOT NULL REFERENCES cases(id),
    entity_id    TEXT REFERENCES entities(id),
    body         TEXT NOT NULL,
    author_badge TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

-- 3.14 reports
CREATE TABLE IF NOT EXISTS reports (
    id                     TEXT PRIMARY KEY,
    case_id                TEXT NOT NULL REFERENCES cases(id),
    kind                   TEXT NOT NULL CHECK (kind IN ('BRIEF_PDF','BRIEF_JSON','VERIFY_CERT')),
    file_path              TEXT NOT NULL,
    sha256                 TEXT NOT NULL,
    audit_head_hash        TEXT NOT NULL,   -- chain head at generation time
    evidence_manifest_json TEXT NOT NULL,
    suspects_json          TEXT NOT NULL,
    signature              TEXT,            -- optional Ed25519 detached signature
    generated_by_badge     TEXT NOT NULL,
    generated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_case ON reports(case_id, generated_at DESC);
