# Trace-Proof Front-End Data Contracts (`views/CONTRACTS.md`)

This document records the exact interface signatures between the Streamlit front-end views and the data layer (`views/api.py`).

Functions tagged **`CONTRACT-NEEDED`** represent front-end features that require backend service implementation when `TRACEPROOF_USE_REAL=1`.

---

## Complete CONTRACT-NEEDED Function Matrix

| Function Name | Arguments | Return Type | Real Service Exists? | Screens Used In | Tag |
|---|---|---|:---:|---|---|
| `get_officer_count` | `()` | `int` | No (mock) | S00, S01 | `CONTRACT-NEEDED` |
| `authenticate_officer` | `badge_no: str, password: str` | `tuple[bool, Optional[Officer], str]` | No (mock) | S01, S15 | `CONTRACT-NEEDED` |
| `create_officer` | `badge_no, full_name, rank, unit, role, password` | `tuple[bool, str, Optional[Officer]]` | No (mock) | S00 | `CONTRACT-NEEDED` |
| `list_cases` | `search_query: str, status_filter: str` | `List[Case]` | No (mock) | S02 | `CONTRACT-NEEDED` |
| `get_case_by_id` | `case_id: str` | `Optional[Case]` | No (mock) | S04 - S15 | `CONTRACT-NEEDED` |
| `create_case` | `case_number, title, fir_number, police_station, complaint_date, description, created_by_badge, created_by_name` | `Case` | No (mock) | S03 | `CONTRACT-NEEDED` |
| `create_sample_case` | `()` | `Case` | No (mock) | S02, S04, S17 | `CONTRACT-NEEDED` |
| `get_case_dashboard_counts` | `case_id: str` | `Dict[str, Any]` | No (mock) | S04 | `CONTRACT-NEEDED` |
| `get_pipeline_status` | `case_id: str` | `Dict[str, str]` | No (mock) | S04 | `CONTRACT-NEEDED` |
| `list_evidence_files` | `case_id: str` | `List[EvidenceFile]` | No (mock) | S05, S07, S13 | `CONTRACT-NEEDED` |
| `confirm_file_mapping` | `evidence_file_id: str, mapping_json: dict, datetime_format: str` | `bool` | No (mock) | S06 | `CONTRACT-NEEDED` |
| `exclude_evidence_file` | `evidence_file_id: str, reason: str` | `bool` | No (mock) | S05, S07 | `CONTRACT-NEEDED` |
| `list_entities` | `case_id: str, entity_type: Optional[str], search: str` | `List[Entity]` | No (mock) | S08, S09, S11 | `CONTRACT-NEEDED` |
| `get_entity_by_id` | `case_id: str, entity_id: str` | `Optional[Entity]` | No (mock) | S11 | `CONTRACT-NEEDED` |
| `list_entity_links` | `case_id: str, min_confidence: float` | `List[EntityLink]` | No (mock) | S08, S09 | `CONTRACT-NEEDED` |
| `dismiss_link` | `link_id: str, reason: str` | `bool` | No (mock) | S08 | `CONTRACT-NEEDED` |
| `get_graph_data` | `case_id: str, min_confidence: float, top_n: int` | `Dict[str, Any]` | No (mock) | S09 | `CONTRACT-NEEDED` |
| `list_risk_scores` | `case_id: str, band_filter: str, entity_type: str, only_path: bool, ml_enabled: bool` | `List[RiskScore]` | No (mock) | S10 | `CONTRACT-NEEDED` |
| `get_risk_score_for_entity` | `case_id: str, entity_id: str` | `Optional[RiskScore]` | No (mock) | S11 | `CONTRACT-NEEDED` |
| `get_seizure_recommendations` | `case_id: str` | `List[SeizureRecommendation]` | No (mock) | S10 | `CONTRACT-NEEDED` |
| `list_timeline_events` | `case_id: str, entity_id: Optional[str]` | `List[Event]` | No (mock) | S12 | `CONTRACT-NEEDED` |
| `verify_case_integrity` | `case_id: str` | `Dict[str, Any]` | No (mock) | S04, S13, S15 | `CONTRACT-NEEDED` |
| `simulate_tampering` | `enabled: bool` | `None` | No (demo helper) | S17 | `CONTRACT-NEEDED` |
| `list_audit_entries` | `case_id: str, action_filter: Optional[str]` | `List[AuditEntry]` | No (mock) | S14 | `CONTRACT-NEEDED` |
| `generate_brief` | `case_id: str, officer_badge: str, password: str, sections: dict, remarks: str` | `Dict[str, Any]` | No (mock) | S15 | `CONTRACT-NEEDED` |
| `get_risk_weights` | `()` | `List[Dict[str, Any]]` | No (mock) | S16 | `CONTRACT-NEEDED` |
| `get_workstation_info` | `()` | `Dict[str, Any]` | No (mock) | S16 | `CONTRACT-NEEDED` |

---

## Detailed Backend Contract Specifications

### 1. Officer Authentication & First-Run Setup (S00, S01, S15)
- `get_officer_count() -> int`
  - Returns total registered officer accounts. Used by `determine_active_route` to redirect to S00 on first run.
- `authenticate_officer(badge_no: str, password: str) -> tuple[bool, Optional[Officer], str]`
  - Validates officer credentials. Returns `(success, Officer, error_message)`. Used in S01 login and S15 brief re-authentication gate.
- `create_officer(badge_no, full_name, rank, unit, role, password) -> tuple[bool, str, Optional[Officer]]`
  - Creates the primary investigating officer account during first-run setup (S00).

### 2. Case Management & Pipeline Dashboard (S02, S03, S04)
- `list_cases(search_query: str = "", status_filter: str = "ALL") -> List[Case]`
  - Returns list of case records matching search filter.
- `get_case_by_id(case_id: str) -> Optional[Case]`
  - Returns metadata for specified case.
- `create_case(...) -> Case`
  - Creates new case directory structure and sqlite entry.
- `create_sample_case() -> Case`
  - Loads Seed 42 fixture case for instant demo rehearsal.
- `get_case_dashboard_counts(case_id: str) -> Dict[str, Any]`
  - Computes counts: `files_count`, `rows_count`, `entities_count`, `links_count`, `top_risk_score`, `top_risk_band`, `top_suspect_name`.
- `get_pipeline_status(case_id: str) -> Dict[str, str]`
  - Returns step status map for 6-stage pipeline strip (`Done`, `In Progress`, `Pending`, `Failed`).

### 3. Ingestion & Column Mapping (S05, S06, S07)
- `list_evidence_files(case_id: str) -> List[EvidenceFile]`
  - Returns evidence records including raw file size, SHA-256 digest, parsed/rejected row counts, and ingestion officer badge.
- `confirm_file_mapping(evidence_file_id: str, mapping_json: dict, datetime_format: str) -> bool`
  - Approves column detection and schema mapping.
- `exclude_evidence_file(evidence_file_id: str, reason: str) -> bool`
  - Excludes corrupt or irrelevant file from correlation with audited reason.

### 4. Correlation, Entities & Links (S08, S09, S11)
- `list_entities(case_id: str, entity_type: Optional[str], search: str) -> List[Entity]`
  - Filters entities by type (`BANK_ACCOUNT`, `PHONE_NUMBER`, `IMEI`, `IP_ADDRESS`, `NAME`, `ATM_LOCATION`) and search string.
- `get_entity_by_id(case_id: str, entity_id: str) -> Optional[Entity]`
  - Retrieves single entity record for S11 drill-down.
- `list_entity_links(case_id: str, min_confidence: float) -> List[EntityLink]`
  - Returns correlated links meeting confidence threshold. Excludes dismissed links unless requested.
- `dismiss_link(link_id: str, reason: str) -> bool`
  - Marks link dismissed, logs audit event `LINK_DISMISSED`.

### 5. Network Graph Visualization (S09)
- `get_graph_data(case_id: str, min_confidence: float, top_n: int) -> Dict[str, Any]`
  - Returns nodes dict array, edges dict array, highlighted victim-to-cashout path array, and summary caption string.

### 6. Risk Engine & Explainability (S10, S11)
- `list_risk_scores(case_id: str, band_filter: str, entity_type: str, only_path: bool, ml_enabled: bool) -> List[RiskScore]`
  - Computes or retrieves ranked risk scores with top 3 plain sentence reasons.
- `get_risk_score_for_entity(case_id: str, entity_id: str) -> Optional[RiskScore]`
  - Detailed breakdown of rule codes, score contributions, and exact raw file row provenance.
- `get_seizure_recommendations(case_id: str) -> List[SeizureRecommendation]`
  - Actionable account freeze recommendations for banks / IO notice.

### 7. Timeline & Temporal Analysis (S12)
- `list_timeline_events(case_id: str, entity_id: Optional[str]) -> List[Event]`
  - Unified chronological events list with raw file, row number, and SHA-256 hash.

### 8. Cryptographic Integrity & Audit Log (S13, S14, S17)
- `verify_case_integrity(case_id: str) -> Dict[str, Any]`
  - Performs live hash verification of disk evidence files and SHA-256 sequence hash chain of audit log.
- `simulate_tampering(enabled: bool) -> None`
  - Toggles mock tampering flag for demo testing S13 red TAMPER DETECTED banner.
- `list_audit_entries(case_id: str, action_filter: Optional[str]) -> List[AuditEntry]`
  - Read-only, append-only audit trail entries with sequence hash.

### 9. Court Brief Builder & Settings (S15, S16)
- `generate_brief(case_id: str, officer_badge: str, password: str, sections: dict, remarks: str) -> Dict[str, Any]`
  - Generates 1-page court brief PDF with SHA-256 digest after re-authenticating officer.
- `get_risk_weights() -> List[Dict[str, Any]]`
  - Returns editable rule weights R01–R12.
- `get_workstation_info() -> Dict[str, Any]`
  - Returns offline workstation metadata and network probe status.
