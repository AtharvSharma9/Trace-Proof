# 5. Backend Schema Document

**Project:** PRAMAAN
**Engine:** SQLite 3 · one `.pramaan` file per case, plus one workstation-level `pramaan_app.db`
**Version:** 1.0 — **LOCK THIS ON DAY ONE.** It is the contract between all four team members.

---

## 1. Schema overview

Two databases, deliberately separated.

**A. `pramaan_app.db`** — workstation-level. Officers, sessions, case registry, saved format
plugins. Lives beside the application, not inside a case.

**B. `<case>/case.pramaan`** — one per case. All evidence, entities, events, links, scores,
reasons, audit chain and reports. Portable, hashable, seizable. A case can be copied to another
workstation and opened intact.

*Reason for the split:* credentials must not travel with evidence when a case file is shared,
and a case file must be self-contained without carrying the workstation's user table.

### Entity-relationship summary (case database)

```
cases ─┬─< evidence_files ─┬─< events >─┬─ entities
       │                   │            │      │
       │                   └─< parse_rejects   ├─< entity_links >─┘
       │                                       │
       ├─< entities ───────────────────────────┘
       ├─< risk_scores ─< risk_reasons ─< reason_evidence_refs
       ├─< graph_snapshots
       ├─< audit_log   (hash-chained, append-only)
       ├─< notes
       └─< reports
```

---

## 2. Application database — `pramaan_app.db`

### 2.1 `officers`
```sql
CREATE TABLE officers (
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
CREATE UNIQUE INDEX idx_officers_badge ON officers(badge_no);
```
`password_hash` stores the full argon2id encoded string, which embeds its own salt and
parameters. Never store a bare digest and never store a plaintext password anywhere, including
logs.

### 2.2 `sessions`
```sql
CREATE TABLE sessions (
    id             TEXT PRIMARY KEY,
    officer_id     TEXT NOT NULL REFERENCES officers(id) ON DELETE CASCADE,
    token_hash     TEXT NOT NULL UNIQUE,   -- SHA-256 of the session token, never the token
    issued_at      TEXT NOT NULL,
    expires_at     TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL,
    revoked_at     TEXT,
    workstation_id TEXT NOT NULL
);
CREATE INDEX idx_sessions_officer ON sessions(officer_id);
CREATE INDEX idx_sessions_expiry  ON sessions(expires_at);
```
The raw token lives only in `st.session_state`. The database stores its SHA-256, so a stolen
database file does not yield usable sessions.

### 2.3 `case_registry`
```sql
CREATE TABLE case_registry (
    case_id        TEXT PRIMARY KEY,
    case_number    TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    folder_path    TEXT NOT NULL,
    created_by      TEXT NOT NULL REFERENCES officers(id),
    created_at     TEXT NOT NULL,
    last_opened_at TEXT,
    status         TEXT NOT NULL DEFAULT 'OPEN'
                   CHECK (status IN ('OPEN','UNDER_REVIEW','CLOSED'))
);
```
A pointer table only. The authoritative case data lives in the case file.

### 2.4 `format_plugins`
```sql
CREATE TABLE format_plugins (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    kind           TEXT NOT NULL
                   CHECK (kind IN ('CDR','IPDR','BANK','UPI','EML','ANDROID_DUMP','APK','OTHER')),
    header_signature TEXT NOT NULL,   -- sorted, normalised header list, joined — the fingerprint
    mapping_yaml   TEXT NOT NULL,
    times_used     INTEGER NOT NULL DEFAULT 0,
    created_by     TEXT REFERENCES officers(id),
    created_at     TEXT NOT NULL,
    is_builtin     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_format_signature ON format_plugins(header_signature);
```
This table is what makes ingestion schema-agnostic *and* improving. When an officer confirms a
mapping for an unfamiliar bank, it is saved here and the next file from that bank maps
automatically at 100% confidence.

---

## 3. Case database — `case.pramaan`

### 3.1 `cases`
```sql
CREATE TABLE cases (
    id              TEXT PRIMARY KEY,
    case_number     TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    fir_number      TEXT,
    police_station  TEXT,
    complaint_date  TEXT,
    description     TEXT,
    created_by_badge TEXT NOT NULL,      -- denormalised: case file must be readable standalone
    created_by_name  TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN','UNDER_REVIEW','CLOSED')),
    integrity_status TEXT NOT NULL DEFAULT 'UNVERIFIED'
                    CHECK (integrity_status IN ('UNVERIFIED','VERIFIED','COMPROMISED')),
    last_verified_at TEXT,
    schema_version  INTEGER NOT NULL DEFAULT 1
);
```
Officer identity is denormalised into the case file on purpose: the file must be self-describing
when detached from the workstation that created it.

### 3.2 `evidence_files`
```sql
CREATE TABLE evidence_files (
    id                TEXT PRIMARY KEY,
    case_id           TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    original_filename TEXT NOT NULL,
    original_path     TEXT,
    stored_path       TEXT NOT NULL,        -- relative to the case folder
    sha256            TEXT NOT NULL,        -- 64 lowercase hex chars
    md5               TEXT,                 -- legacy cross-check for older forensic workflows
    size_bytes        INTEGER NOT NULL CHECK (size_bytes >= 0),
    mime_type         TEXT,
    detected_kind     TEXT NOT NULL
                      CHECK (detected_kind IN ('CDR','IPDR','BANK','UPI','EML',
                                               'ANDROID_DUMP','APK','UNKNOWN')),
    detection_confidence REAL CHECK (detection_confidence BETWEEN 0 AND 1),
    mapping_id        TEXT REFERENCES column_mappings(id),
    rows_total        INTEGER DEFAULT 0,
    rows_parsed       INTEGER DEFAULT 0,
    rows_rejected     INTEGER DEFAULT 0,
    parse_status      TEXT NOT NULL DEFAULT 'PENDING'
                      CHECK (parse_status IN ('PENDING','MAPPED','PARSED','FAILED','EXCLUDED')),
    parse_notes       TEXT,
    exclusion_reason  TEXT,
    ingested_by_badge TEXT NOT NULL,
    ingested_at       TEXT NOT NULL,
    UNIQUE (case_id, sha256)               -- same file cannot be ingested twice into one case
);
CREATE INDEX idx_evidence_case   ON evidence_files(case_id);
CREATE INDEX idx_evidence_sha    ON evidence_files(sha256);
CREATE INDEX idx_evidence_status ON evidence_files(case_id, parse_status);
```
`UNIQUE (case_id, sha256)` gives free deduplication and is itself a small forensic feature: the
same file submitted twice under different names is detected automatically.

Rows are never deleted. Exclusion is a status change plus a mandatory reason.

### 3.3 `column_mappings`
```sql
CREATE TABLE column_mappings (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id),
    evidence_file_id TEXT REFERENCES evidence_files(id),
    detected_kind    TEXT NOT NULL,
    header_signature TEXT NOT NULL,
    mapping_json     TEXT NOT NULL,   -- {"A-PARTY NO":"caller","B-PARTY NO":"callee",...}
    confidence_json  TEXT NOT NULL,   -- {"caller":0.94,"callee":0.91,...}
    datetime_format  TEXT,
    auto_generated   INTEGER NOT NULL DEFAULT 1,
    confirmed_by_badge TEXT,
    confirmed_at     TEXT,
    saved_as_plugin  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_mapping_case ON column_mappings(case_id);
```

### 3.4 `entities`
The canonical identifier table.
```sql
CREATE TABLE entities (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    entity_type      TEXT NOT NULL
                     CHECK (entity_type IN ('PHONE','IMEI','IMSI','UPI_HANDLE','BANK_ACCOUNT',
                                            'IFSC','IP','MAC','EMAIL','DEVICE_ID','APK_CERT',
                                            'ATM_ID','MERCHANT_ID')),
    raw_value        TEXT NOT NULL,
    normalized_value TEXT NOT NULL,   -- E.164 for phones, lowercase for UPI/email, etc.
    label            TEXT,            -- optional officer-assigned label, e.g. "Victim — complainant"
    role             TEXT CHECK (role IN ('VICTIM','SUSPECT','MULE','CASHOUT','INTERMEDIARY',
                                          'UNKNOWN')) DEFAULT 'UNKNOWN',
    occurrences      INTEGER NOT NULL DEFAULT 0,
    first_seen_at    TEXT,
    last_seen_at     TEXT,
    attributes_json  TEXT DEFAULT '{}', -- bank name, operator, account-open date, device model
    created_at       TEXT NOT NULL,
    UNIQUE (case_id, entity_type, normalized_value)
);
CREATE INDEX idx_entities_case_type ON entities(case_id, entity_type);
CREATE INDEX idx_entities_norm      ON entities(normalized_value);
CREATE INDEX idx_entities_role      ON entities(case_id, role);
```
**Normalisation rules (must be applied before insert, or the UNIQUE constraint is worthless):**
| Type | Rule |
|---|---|
| PHONE | Strip spaces, dashes, brackets; drop leading `0`; add `+91` if 10 digits; store E.164 |
| IMEI | Digits only; validate 15 digits with the Luhn check digit; store 14-digit TAC+serial as `imei_base` in attributes so IMEI/IMEISV variants of one handset still match |
| IMSI | Digits only, 15 digits |
| UPI_HANDLE | Lowercase, trim; preserve the `@psp` suffix exactly |
| BANK_ACCOUNT | Digits only; strip leading zeros **only** when the IFSC is also known, and record the original in `raw_value` |
| IP | Normalise IPv6; store the `/24` (v4) or `/64` (v6) prefix in attributes for subnet linking |
| MAC | Lowercase, colon-separated |
| EMAIL | Lowercase domain; preserve the local part's case in `raw_value` |

The `UNIQUE (case_id, entity_type, normalized_value)` constraint **is** the entity-resolution
mechanism. Getting normalisation right is therefore the highest-leverage correctness work in the
project, and directly determines the false-link rate that the 25% accuracy criterion measures.

### 3.5 `events`
Every atomic fact extracted from evidence. The provenance columns are `NOT NULL` by design.
```sql
CREATE TABLE events (
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
CREATE INDEX idx_events_case_time ON events(case_id, occurred_at);
CREATE INDEX idx_events_src       ON events(src_entity_id);
CREATE INDEX idx_events_dst       ON events(dst_entity_id);
CREATE INDEX idx_events_type      ON events(case_id, event_type);
CREATE INDEX idx_events_device    ON events(device_entity_id);
CREATE INDEX idx_events_amount    ON events(case_id, amount) WHERE amount IS NOT NULL;
CREATE INDEX idx_events_evidence  ON events(evidence_file_id, source_row);
```

**This table is the heart of the design.** `evidence_file_id`, `source_row` and `source_sha256`
being `NOT NULL` is what makes the product's central promise structurally enforceable rather
than merely intended: it is not possible to insert a fact whose origin is unknown.

`idx_events_evidence` is what makes the drill-down from a reason code back to the raw row fast.

### 3.6 `parse_rejects`
```sql
CREATE TABLE parse_rejects (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id),
    evidence_file_id TEXT NOT NULL REFERENCES evidence_files(id),
    source_row       INTEGER NOT NULL,
    raw_line         TEXT,
    reason           TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX idx_rejects_file ON parse_rejects(evidence_file_id);
```
Rejected rows are kept, not discarded. An officer must be able to see what the system could not
read — a silently dropped row could be the one that mattered.

### 3.7 `entity_links`
```sql
CREATE TABLE entity_links (
    id              TEXT PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    entity_a_id     TEXT NOT NULL REFERENCES entities(id),
    entity_b_id     TEXT NOT NULL REFERENCES entities(id),
    link_type       TEXT NOT NULL
                    CHECK (link_type IN ('SHARED_IMEI','SHARED_IMSI','SHARED_DEVICE',
                                         'SHARED_IP_SUBNET','SHARED_MAC','RECURRING_BENEFICIARY',
                                         'FUND_FLOW','SHARED_APK_CERT','TEMPORAL_PROXIMITY',
                                         'SHARED_EMAIL_DOMAIN')),
    confidence      REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    rationale       TEXT NOT NULL,        -- human-readable, goes straight into the brief
    support_count   INTEGER NOT NULL DEFAULT 1,
    supporting_event_ids TEXT,            -- JSON array of event ids
    total_amount    REAL,                 -- for FUND_FLOW edges
    first_at        TEXT,
    last_at         TEXT,
    status          TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE','DISMISSED')),
    dismissed_by_badge TEXT,
    dismissal_reason TEXT,
    created_at      TEXT NOT NULL,
    CHECK (entity_a_id <> entity_b_id),
    UNIQUE (case_id, entity_a_id, entity_b_id, link_type)
);
CREATE INDEX idx_links_case ON entity_links(case_id, status);
CREATE INDEX idx_links_a    ON entity_links(entity_a_id);
CREATE INDEX idx_links_b    ON entity_links(entity_b_id);
```
**Ordering convention:** for symmetric link types, always store with
`entity_a_id < entity_b_id` lexicographically. Without this convention the UNIQUE constraint
silently permits duplicate links in both directions, which inflates degree counts and corrupts
centrality scores. For `FUND_FLOW`, direction is meaningful, so `a → b` is source → destination.

**Default confidence by link type** (tune on synthetic data, record in the brief):
| Link type | Default | Note |
|---|---|---|
| `SHARED_IMEI` | 0.95 | Very strong — one physical handset |
| `SHARED_IMSI` | 0.95 | One SIM |
| `SHARED_MAC` | 0.90 | Strong unless randomised MAC |
| `SHARED_APK_CERT` | 0.90 | Same developer key — one campaign |
| `RECURRING_BENEFICIARY` | 0.80 | Scales with occurrence count |
| `FUND_FLOW` | 1.00 | Directly observed in the statement |
| `SHARED_IP_SUBNET` | 0.45 | **Weak.** CGNAT means thousands share a /24. Below the 0.75 default threshold, so it never links on its own — it may only corroborate. |
| `TEMPORAL_PROXIMITY` | 0.35 | Weak, corroborating only |

The low weighting of IP-subnet links is a deliberate accuracy decision and should be stated in
the technical proposal. It is exactly the kind of naive correlation that produces false links.

### 3.8 `risk_scores`
```sql
CREATE TABLE risk_scores (
    id             TEXT PRIMARY KEY,
    case_id        TEXT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    entity_id      TEXT NOT NULL REFERENCES entities(id),
    score          REAL NOT NULL CHECK (score BETWEEN 0 AND 100),
    band           TEXT NOT NULL CHECK (band IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    rules_score    REAL NOT NULL CHECK (rules_score BETWEEN 0 AND 100),
    anomaly_score  REAL CHECK (anomaly_score BETWEEN 0 AND 1),
    anomaly_used   INTEGER NOT NULL DEFAULT 0 CHECK (anomaly_used IN (0,1)),
    rank_in_case   INTEGER,
    features_json  TEXT NOT NULL,        -- full feature vector, for reproducibility
    model_version  TEXT NOT NULL,        -- e.g. "rules-1.0+iforest-1.0"
    weights_hash   TEXT NOT NULL,        -- SHA-256 of the weights config in force
    random_seed    INTEGER,
    computed_by_badge TEXT NOT NULL,
    computed_at    TEXT NOT NULL,
    is_current     INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1))
);
CREATE INDEX idx_risk_case_current ON risk_scores(case_id, is_current, score DESC);
CREATE INDEX idx_risk_entity       ON risk_scores(entity_id, is_current);
```
Scores are **versioned, not overwritten.** A re-run sets `is_current = 0` on the previous rows
and inserts new ones. An investigation must be able to show what the score was at the time a
decision was made. `weights_hash` and `random_seed` make any historical score exactly
reproducible.

### 3.9 `risk_reasons`
```sql
CREATE TABLE risk_reasons (
    id             TEXT PRIMARY KEY,
    risk_score_id  TEXT NOT NULL REFERENCES risk_scores(id) ON DELETE CASCADE,
    rule_code      TEXT NOT NULL,        -- R01 … R12
    rule_name      TEXT NOT NULL,
    triggered      INTEGER NOT NULL CHECK (triggered IN (0,1)),
    raw_value      REAL,                 -- the measured value, e.g. 0.96
    threshold      REAL,                 -- the threshold it crossed
    weight         REAL NOT NULL,
    points_contributed REAL NOT NULL,
    plain_text     TEXT NOT NULL,        -- "Forwarded 96% of credited funds within 11 minutes"
    display_order  INTEGER NOT NULL
);
CREATE INDEX idx_reasons_score ON risk_reasons(risk_score_id, display_order);
```
Non-triggered rules are stored too (`triggered = 0`, `points_contributed = 0`). Being able to
show what was checked and did *not* fire is as defensible as showing what did.

### 3.10 `reason_evidence_refs`
The join that closes the loop from a score back to a raw row.
```sql
CREATE TABLE reason_evidence_refs (
    id               TEXT PRIMARY KEY,
    risk_reason_id   TEXT NOT NULL REFERENCES risk_reasons(id) ON DELETE CASCADE,
    event_id         TEXT REFERENCES events(id),
    evidence_file_id TEXT NOT NULL REFERENCES evidence_files(id),
    source_row       INTEGER NOT NULL,
    source_sha256    TEXT NOT NULL,
    note             TEXT
);
CREATE INDEX idx_refs_reason ON reason_evidence_refs(risk_reason_id);
```

### 3.11 `graph_snapshots`
```sql
CREATE TABLE graph_snapshots (
    id             TEXT PRIMARY KEY,
    case_id        TEXT NOT NULL REFERENCES cases(id),
    node_count     INTEGER NOT NULL,
    edge_count     INTEGER NOT NULL,
    metrics_json   TEXT NOT NULL,   -- pagerank, betweenness, degree, per node id
    centrality_k   INTEGER,         -- k used for approximate betweenness, NULL if exact
    layout_json    TEXT,            -- cached node positions, so the graph looks stable
    graphml_path   TEXT,
    png_path       TEXT,
    built_at       TEXT NOT NULL,
    is_current     INTEGER NOT NULL DEFAULT 1
);
```
Caching the layout matters for usability: an officer who returns to the graph should see the same
picture, not a re-shuffled one.

### 3.12 `audit_log` — append-only, hash-chained
```sql
CREATE TABLE audit_log (
    id           TEXT PRIMARY KEY,
    case_id      TEXT NOT NULL REFERENCES cases(id),
    seq          INTEGER NOT NULL,          -- 0 = genesis, strictly incrementing, no gaps
    occurred_at  TEXT NOT NULL,
    officer_badge TEXT NOT NULL,
    officer_name TEXT NOT NULL,
    action       TEXT NOT NULL,
    target_type  TEXT,
    target_id    TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    payload_hash TEXT NOT NULL,             -- SHA-256 of canonical JSON (sorted keys, no spaces)
    prev_hash    TEXT NOT NULL,             -- 64 zeros for genesis
    entry_hash   TEXT NOT NULL UNIQUE,
    UNIQUE (case_id, seq)
);
CREATE INDEX idx_audit_case_seq ON audit_log(case_id, seq);
CREATE INDEX idx_audit_action   ON audit_log(case_id, action);
```

**Chain construction:**
```
payload_hash = SHA256( canonical_json(payload) )
entry_hash   = SHA256( prev_hash || seq || occurred_at || officer_badge ||
                       action || (target_type or '') || (target_id or '') || payload_hash )
```
Concatenate with a delimiter that cannot occur in any field (use `\x1f`), or the chain is
vulnerable to field-boundary ambiguity. Canonical JSON means sorted keys, no whitespace, UTF-8 —
otherwise the same payload hashes differently on a re-verify and produces a false tamper alert.

**Enforcement:**
```sql
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;

CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
```
These triggers are not security against a determined attacker with direct file access — they
cannot be. They are a guarantee against the application itself, and against accident. The hash
chain is what provides tamper *evidence*; the triggers provide tamper *resistance*. State this
distinction plainly in the proposal rather than overclaiming.

**Actions to log:** `CASE_CREATED`, `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`,
`EVIDENCE_INGESTED`, `EVIDENCE_DUPLICATE_SKIPPED`, `EVIDENCE_EXCLUDED`, `MAPPING_PROPOSED`,
`MAPPING_CONFIRMED`, `MAPPING_OVERRIDDEN`, `PARSE_COMPLETED`, `PARSE_FAILED`,
`CORRELATION_RUN`, `LINK_DISMISSED`, `GRAPH_BUILT`, `THRESHOLDS_CHANGED`, `SCORING_RUN`,
`ANOMALY_DISABLED`, `NOTE_ADDED`, `BRIEF_GENERATED`, `INTEGRITY_VERIFIED`, `INTEGRITY_FAILURE`,
`PROVENANCE_ERROR`, `CASE_STATUS_CHANGED`.

### 3.13 `notes`
```sql
CREATE TABLE notes (
    id            TEXT PRIMARY KEY,
    case_id       TEXT NOT NULL REFERENCES cases(id),
    entity_id     TEXT REFERENCES entities(id),
    body          TEXT NOT NULL,
    author_badge  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
```
Append-only in practice: edits create a new row and mark the old one superseded, rather than
overwriting an officer's recorded observation.

### 3.14 `reports`
```sql
CREATE TABLE reports (
    id               TEXT PRIMARY KEY,
    case_id          TEXT NOT NULL REFERENCES cases(id),
    kind             TEXT NOT NULL CHECK (kind IN ('BRIEF_PDF','BRIEF_JSON','VERIFY_CERT')),
    file_path        TEXT NOT NULL,
    sha256           TEXT NOT NULL,
    audit_head_hash  TEXT NOT NULL,   -- chain head at generation time
    evidence_manifest_json TEXT NOT NULL,
    suspects_json    TEXT NOT NULL,
    signature        TEXT,            -- optional Ed25519 detached signature
    generated_by_badge TEXT NOT NULL,
    generated_at     TEXT NOT NULL
);
CREATE INDEX idx_reports_case ON reports(case_id, generated_at DESC);
```
Embedding `audit_head_hash` in the report ties the document to a precise state of the
investigation. If the case is later altered, the old brief remains verifiable against the state
it described.

---

## 4. Authentication and session handling (summary)

| Concern | Rule |
|---|---|
| Hashing | argon2id (`time_cost=3`, `memory_cost=65536`, `parallelism=4`); bcrypt fallback only if argon2 will not install |
| Token | `secrets.token_urlsafe(32)`; only its SHA-256 is persisted |
| Expiry | 8 hours, sliding on activity; hard cap 24 hours |
| Lockout | 5 failures → 15-minute lock on `badge_no`; each failure audited |
| Re-auth | Required for `BRIEF_GENERATED` and `EVIDENCE_EXCLUDED` |
| Logout | Sets `revoked_at`; the session row is never deleted |
| No recovery path | There is no email reset. A supervisor resets locally, and the reset is audited. |

---

## 5. Permissions matrix

| Action | IO | ANALYST | SUPERVISOR |
|---|:--:|:--:|:--:|
| Create case | ✓ | ✓ | ✓ |
| Ingest evidence | ✓ | ✓ | — |
| Confirm / override mapping | ✓ | ✓ | — |
| Run correlation | ✓ | ✓ | — |
| Dismiss a link | ✓ | ✓ | — |
| Run risk scoring | ✓ | ✓ | — |
| Change risk weights | within permitted band | ✓ | ✓ |
| Generate brief | ✓ | ✓ | — |
| Verify integrity | ✓ | ✓ | ✓ |
| View audit log | ✓ | ✓ | ✓ |
| Export audit log | — | ✓ | ✓ |
| View rejected rows / parse diagnostics | — | ✓ | ✓ |
| Mark evidence excluded | ✓ (reason required) | ✓ | ✓ |
| **Delete anything** | ✗ | ✗ | ✗ |
| Reset an officer password | — | — | ✓ |
| Close a case | — | — | ✓ |

**Delete is held by no role.** This is the schema's most important permission decision. It is
enforced by `ON DELETE RESTRICT` on every foreign key into `cases`, `evidence_files` and
`entities`, and by the audit triggers.

---

## 6. Data ownership rules

1. **The case owns its data.** Every table in the case database carries `case_id` and every
   query filters on it. There is no cross-case query in v1 — cross-case correlation is a v2
   feature requiring an explicit legal basis, and building it accidentally would be worse than
   not building it.
2. **Evidence belongs to the case, not to the officer.** An officer who ingested a file cannot
   remove it. Another officer opening the case sees the full record including who ingested what.
3. **The audit log belongs to nobody.** No role can edit or delete it. It is the one table with
   no owner by design.
4. **Derived data is disposable; source data is not.** Entities, links, scores and graphs can be
   recomputed from scratch at any time. Evidence files and audit entries cannot be regenerated
   and therefore cannot be removed.
5. **Personal data minimisation.** `app.log` records hashes, counts and durations only. Account
   numbers, phone numbers and names never appear in technical logs, only in the case database
   and the brief.
6. **Portability.** A case folder is self-contained. Copying it to another workstation and
   opening it must reproduce every screen and re-verify the chain without contacting the
   original machine.
7. **Retention.** Case files persist until a supervisor closes and archives them; the application
   never auto-deletes anything.

---

## 7. Index strategy rationale

| Index | Serves |
|---|---|
| `idx_events_case_time` | Timeline screen; every rapid-pass-through window query |
| `idx_events_src` / `idx_events_dst` | Graph edge construction, the hottest query in the app |
| `idx_events_evidence` | Reason-code drill-down to the raw row — the product's core interaction |
| `idx_entities_norm` | Entity resolution during ingestion; called once per parsed row |
| `idx_risk_case_current` | Risk Board ordering, `is_current = 1 ORDER BY score DESC` |
| `idx_links_a` / `idx_links_b` | Neighbourhood expansion on graph node click |
| `idx_audit_case_seq` | Chain verification walk |
| `idx_evidence_sha` | Duplicate detection at ingest |

**Bulk-load note:** drop the `events` indexes before a large parse, insert with
`executemany` inside a single transaction, then recreate them. Inserting 100,000 rows with
indexes live is roughly an order of magnitude slower, and throughput is the 30%-weighted
criterion.

---

## 8. Migration and versioning

`cases.schema_version` carries an integer. On open, if the file's version is lower than the
application's, run ordered migration scripts from `migrations/NNN_description.sql` inside a
transaction, and write a `SCHEMA_MIGRATED` audit entry. If the file's version is *higher* than
the application's, refuse to open it and say so plainly — a newer case file opened by older
code is a silent corruption risk.

---

## 9. Risk rule reference (codes used in `risk_reasons.rule_code`)

| Code | Name | Signal | Default weight |
|---|---|---|---|
| R01 | Rapid pass-through | ≥ 85% of credited funds debited within 60 min | 18 |
| R02 | Fan-in | ≥ 8 distinct sources crediting within 2 h | 12 |
| R03 | Fan-out | ≥ 8 distinct destinations debited within 2 h | 12 |
| R04 | Layering depth | Sits on a chain of ≥ 3 hops completed in < 30 min | 12 |
| R05 | SIM-switch velocity | One IMEI paired with ≥ 3 IMSIs in 7 days | 10 |
| R06 | Device sharing | One IMEI used by ≥ 3 distinct phone numbers | 8 |
| R07 | New account, high volume | Account age < 30 days and turnover > ₹5,00,000 | 10 |
| R08 | Cash-out terminal | ATM/wallet withdrawal at a chain endpoint | 14 |
| R09 | Spoofed header | SPF or DKIM fail, or `From` ≠ `Return-Path` | 8 |
| R10 | Odd-hour burst | ≥ 5 transactions between 00:00 and 05:00 IST | 5 |
| R11 | Call-then-transfer | Inbound call from an unknown number < 15 min before a victim debit | 12 |
| R12 | Centrality | Betweenness in the case's top 5th percentile | 10 |

Weights sum above 100 deliberately; the final score is `min(100, sum(points))`. All weights and
thresholds live in `config/risk_weights.yaml`, are hashed into `risk_scores.weights_hash`, and
are printed in the brief so that any score can be reproduced and challenged.
