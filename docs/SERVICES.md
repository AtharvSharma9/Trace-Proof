# PRAMAAN Service API Reference

> **For:** Frontend (D), DB (teammate), ML (C) teammates  
> **Source of truth:** `02_TRD.md §5.2`, `05_Backend_Schema.md`  
> **Branch:** `backend/core`

All services are plain Python modules — no HTTP, no FastAPI. Call them directly in the Streamlit process. All functions are stateless and pure w.r.t. I/O: they accept dicts/lists and return domain models or raise typed exceptions from `domain.errors`.

---

## Error Types (`domain/errors.py`)

| Exception | When raised |
|---|---|
| `PramaanError` | Base class — catch this to handle all app errors generically |
| `AuthError` | Generic auth failure |
| `LockedOutError` | Badge locked after 5 failures; carries `.minutes_remaining` |
| `InvalidCredentialsError` | Wrong password; carries `.attempts_remaining` |
| `SessionExpiredError` | Token has expired or been revoked |
| `ReAuthRequired` | High-privilege action needs password re-entry |
| `ParseError` | File cannot be parsed at all (not rejected rows) |
| `PathTraversalError` | Path escapes case folder or is a symlink |
| `FileTooLargeError` | File > 500 MB (sniff) or > 1 GB (parse) |
| `PasswordProtectedError` | Encrypted XLSX; subclass of `ParseError` |
| `IntegrityError` | Audit chain or file hash broken |
| `DuplicateEvidenceError` | Same SHA-256 already in this case |

---

## `services/auth_service.py`

### `hash_password(plaintext: str) -> str`
Hash a plaintext password with argon2id (time_cost=3, memory_cost=65536, parallelism=4).  
Returns the full encoded string (includes salt + params). Falls back to bcrypt if argon2 unavailable.

### `verify_password(plaintext: str, stored_hash: str) -> bool`
Verify a plaintext password against a stored argon2id (or bcrypt fallback) hash.

### `login(badge_no, password, officer_record, workstation_id="WS-1") -> (Session, raw_token)`
Authenticate an officer.  
- **Input:** `officer_record` = dict from DB (`id`, `password_hash`, `is_active`, `failed_attempts`, `locked_until`). Mutates `failed_attempts` and `locked_until` in-place — caller must persist.  
- **Output:** `(Session model, raw_token_string)` — raw token goes into `st.session_state`, never into DB.  
- **Raises:** `LockedOutError`, `InvalidCredentialsError`, `AuthError`

### `logout(session_record: dict) -> dict`
Revoke a session. Sets `revoked_at` on the record — caller must persist.  
- **Raises:** `SessionExpiredError` if already revoked.

### `validate_session(raw_token, session_record) -> Session`
Validate a token and slide the 8-hour expiry window.  
- **Input:** `session_record` = dict from DB fetched by `token_hash = SHA256(raw_token)`.  
- **Output:** Updated Session (caller must persist `expires_at` + `last_seen_at`).  
- **Raises:** `SessionExpiredError`, `AuthError`

### `require_reauth(raw_token, password, session_record, officer_record, action) -> None`
Re-auth gate for `BRIEF_GENERATED` and `EVIDENCE_EXCLUDED`. No-op for all other actions.  
- **Raises:** `ReAuthRequired` on wrong password or invalid session; `LockedOutError` if locked.

---

## `services/ingest_service.py`

All file-touching functions accept an optional `progress_cb` for Streamlit live updates.

### `sniff(path: Path) -> DetectedFormat`
Detect file type by content (not extension). Reads first 5 rows, matches against YAML format plugins, falls back to regex (Luhn-valid 15-digit → IMEI → CDR; `@psp` → UPI).  
- **Raises:** `ParseError` (empty/missing), `FileTooLargeError` (> 500 MB), `PathTraversalError` (symlink)

### `hash_file(path, progress_cb=None) -> str`
Compute SHA-256 hex digest using 1 MiB chunks. `progress_cb(bytes_done, bytes_total)`.  
- **Raises:** `PathTraversalError`

### `propose_mapping(headers: list[str], fmt: DetectedFormat) -> MappingProposal`
Fuzzy-match headers to the canonical schema (< 50 ms). Returns per-field confidence scores.  
**No side effects.**

### `ingest_file(case_id, path, mapping: Mapping, officer_id, progress_cb=None) -> IngestResult`
Parse a file. Attaches provenance triple `(evidence_file_id, source_row, sha256)` to every event. Returns `IngestResult` with `.rows_total`, `.rows_parsed`, `.rows_rejected`. Also attaches `._entities` (list[dict]) and `._events` (list[dict]) for in-process consumers.  
- **Does NOT write to DB** — DB layer is responsible for bulk insert.  
- **Raises:** `ParseError`, `PathTraversalError`, `FileTooLargeError`, `PasswordProtectedError`, `DuplicateEvidenceError`

> **Caching hint (UI):**  
> ```python
> @st.cache_data(show_spinner=False)
> def cached_ingest(case_id, file_sha256, ...): ...
> ```
> Key on `(case_id, file_sha256)` — not on `path` which is mutable.

---

## `services/correlate_service.py`

### `extract_entities(entities_raw: list[dict]) -> list[Entity]`
Validate and coerce raw entity dicts into Pydantic Entity models. Idempotent.

### `resolve_links(entities, events, case_id, progress_cb=None) -> list[EntityLink]`
Detect all link types from entity and event lists.  

| Link type | Signal | Default confidence |
|---|---|---|
| `SHARED_IMEI` | Two phones share one IMEI in CDR events | 0.95 |
| `SHARED_IMSI` | Two phones share one IMSI | 0.95 |
| `RECURRING_BENEFICIARY` | Same credit account credited by ≥ 3 distinct sources | ≥ 0.80 |
| `FUND_FLOW` | Direct debit→credit transfer event | 1.00 |

Ordering convention: `entity_a_id < entity_b_id` for all symmetric links.  
**Does NOT write to DB** — caller handles persistence.

### `build_graph(entities, links, events=None, progress_cb=None) -> networkx.MultiDiGraph`
Bulk-construct graph. Computes PageRank, betweenness centrality (k=500 sample above 5 k nodes), in/out degree. Attaches all metrics to node attributes.  
- Returns a `networkx.MultiDiGraph` — do **not** cache this object with `@st.cache_data`; serialise to `metrics_json` dict first.

### `find_cashout_paths(G, victim_ids, cashout_ids, max_hops=6) -> list[list[str]]`
All simple paths from victim to cashout nodes, capped at `max_hops`.

---

## `services/risk_service.py`  *(stub — owned by C)*

### `compute_features(g: networkx.MultiDiGraph) -> polars.DataFrame`
Compute a feature frame per entity.

### `score(case_id: str, use_anomaly: bool = True) -> list[RiskScore]`
Score entities via rules R01–R12 + optional Isolation Forest.

---

## `services/integrity_service.py`  *(stub — owned by C)*

### `append_audit(case_id, officer_id, action, target_type, target_id, payload) -> AuditEntry`
Write a hash-chained entry. Uses `\x1f` field delimiter to prevent boundary ambiguity.

### `verify_chain(case_id) -> ChainVerification`
Re-compute every hash from genesis. Returns `intact=True` or `broken_at_seq`.

### `verify_evidence(case_id) -> list[FileVerification]`
Re-hash all evidence files vs manifest.

---

## `services/report_service.py`  *(stub — owned by D)*

### `build_brief(case_id, officer_id) -> BriefArtifacts`
Generate PDF + JSON brief. Requires re-auth (call `require_reauth()` first).

---

## `services/case_service.py`  *(stub)*

### `create_case(case_number, title, created_by) -> Case`
Create case folder + SQLite file. Writes genesis audit entry.

### `list_cases() -> list[Case]`
List all registered cases.

### `get_case(case_id) -> Case | None`
Fetch a single case by ID.

---

## Canonical Schema (`config/canonical_schema.yaml`)

| Field | Description |
|---|---|
| `caller` | A-Party / Calling number |
| `callee` | B-Party / Called number |
| `start_time` | Call start time |
| `duration_s` | Call duration in seconds |
| `imei` | IMEI of the handset |
| `imsi` | IMSI of the SIM |
| `cell_id` | Cell tower ID |
| `call_type` | Type of call (IN/OUT) |
| `debit_account` | Account debited |
| `credit_account` | Account credited |
| `amount` | Transaction amount |
| `txn_time` | Transaction time |
| `reference_no` | UTR/RRN |
| `balance_after` | Account balance after transaction |
| `sender_email` | Email sender |
| `receiver_email` | Email receiver |
| `ip_address` | IP address |
| `mac_address` | MAC address |

---

## Teammate Dependency Matrix

| Function | Needs from DB teammate | Needs from ML/C teammate |
|---|---|---|
| `ingest_file()` | `db/init.py` with `evidence_files` + `events` tables to do bulk insert | — |
| `resolve_links()` | `entity_links` table | — |
| `build_graph()` | `graph_snapshots` table to persist layout | — |
| `score()` | `risk_scores` + `risk_reasons` tables | R01–R12 rule implementations |
| `append_audit()` | `audit_log` table with append-only triggers | — |
| `build_brief()` | `reports` table | Risk scores populated |

---

## Doc Contradictions Worked Around

1. **README links** point to repo root (`./01_PRD.md`) but docs live in `docs/`. Resolved: used `docs/` as source of truth per user instruction.
2. **`DetectedFormat.IPDR`** appears in the schema `kind` CHECK constraint but was not listed in the original `DetectedFormat` enum in the Phase 0 stub — added.
3. **`SHARED_EMAIL_DOMAIN`** appears in `entity_links.link_type` CHECK but is not mentioned in §3.7's confidence table — treated as a future link type; not implemented in Phase 4, confidence set to 0.40.
4. **`ingest_service.sniff` signature** in TRD §5.2 returns `DetectedFormat`; the TRD §8 "header fuzzy match" target of < 50 ms is for `propose_mapping`, not `sniff`. Both functions now have separate performance targets.
