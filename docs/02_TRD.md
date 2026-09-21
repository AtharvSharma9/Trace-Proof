# 2. Technical Requirements Document (TRD)

**Project:** PRAMAAN
**Version:** 1.0
**Prerequisite:** `01_PRD.md`

---

## 1. Guiding technical constraints

Every decision below follows from four hard constraints set by the problem statement:

1. **Must run offline** on a standard police workstation — no server, no container runtime, no
   internet at runtime.
2. **Must not modify source evidence** — integrity is 25% of the score.
3. **Must be finishable by four people under hackathon time pressure** — therefore one language,
   minimal moving parts.
4. **Must handle bulk log data quickly** — scalability is the highest-weighted criterion at 30%.

---

## 2. Architecture

### 2.1 Architecture style
**Single-process, layered monolith with a local file-backed store.** No microservices, no
message queue, no external database server. The UI, the analysis engine and the datastore all
live in one Python process.

*Reason:* a distributed architecture would be unrunnable on an air-gapped workstation and
unfinishable in a hackathon window. Monolith is the correct answer here, not a compromise.

### 2.2 Layers

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION      Streamlit UI  ·  PyVis graph component   │
├─────────────────────────────────────────────────────────────┤
│  SERVICE           case_service · ingest_service            │
│                    correlate_service · risk_service         │
│                    report_service · integrity_service       │
├─────────────────────────────────────────────────────────────┤
│  DOMAIN            Entity · Event · Link · RiskScore         │
│                    Reason · AuditEntry   (pydantic models)  │
├─────────────────────────────────────────────────────────────┤
│  ENGINE            parsers/   (format plugins, YAML-driven) │
│                    mapping/   (fuzzy header resolution)     │
│                    graph/     (NetworkX model + algorithms) │
│                    rules/     (weighted risk rules)         │
│                    anomaly/   (IsolationForest, optional)   │
│                    integrity/ (hashing, hash chain)         │
├─────────────────────────────────────────────────────────────┤
│  PERSISTENCE       SQLite (one .pramaan file per case)      │
│                    case_folder/evidence/  (read-only copies)│
└─────────────────────────────────────────────────────────────┘
```

### 2.3 The one rule the whole architecture enforces

> **No fact may exist in the system without a `(evidence_file_id, source_row, sha256)` triple.**

This triple is attached at parse time, carried through normalisation, correlation and scoring,
and printed in the final report. It is enforced at the domain layer: the `Event` pydantic model
makes these fields required, so an unsourced event cannot be constructed. This is the single
technical decision that merges Idea 04 (explainability) with Idea 05 (integrity) into one
product rather than two features bolted together.

### 2.4 Data flow

```
Evidence folder
   │
   ▼
[1] Sniff type by content  ──►  SHA-256 hash  ──►  copy into case/evidence/ (read-only)
   │                                │
   │                                └──► evidence_files row + AUDIT entry
   ▼
[2] Parse via format plugin  ──►  raw rows (each tagged with source_row)
   │
   ▼
[3] Fuzzy-map headers to canonical schema  ──►  officer confirmation  ──► AUDIT entry
   │
   ▼
[4] Normalise → Entities + Events (provenance triple attached)
   │
   ▼
[5] Correlate → entity_links (shared IMEI / IMSI / IP-subnet / UPI / MAC / cert)
   │
   ▼
[6] Build NetworkX graph → centrality, fan-in/out, layering, cycles, pass-through
   │
   ├──► [7a] Rule engine → rules_score + reason codes (each with evidence refs)
   │           │
   │           └──► [7b] IsolationForest → anomaly_score (optional re-ranking only)
   │                        │
   │                        ▼
   │                   final 0–100 score + band  ──► AUDIT entry
   ▼
[8] Report service → one-page PDF + JSON + hash appendix + audit chain head
```

---

## 3. Technology stack

### 3.1 Language and runtime
| Item | Choice | Reason |
|---|---|---|
| Language | **Python 3.11** | One language for all four members; strongest forensic/data library ecosystem; 3.11 for speed and `tomllib` |
| Packaging | **`uv` or `venv` + `requirements.txt`** | Reproducible; no admin rights needed |
| Distribution | Folder + `run.bat` launcher; **PyInstaller one-folder build** as a stretch goal | Officer double-clicks; no Python install required in the stretch build |

### 3.2 Frontend stack
| Item | Choice | Reason |
|---|---|---|
| UI framework | **Streamlit 1.3x** | Python-native, so no context switch and no separate frontend member; renders a usable dashboard in hours, not days |
| Graph rendering | **PyVis** (vis-network under the hood), embedded via `streamlit.components.v1.html` | Interactive, drag-and-zoom, renders to a self-contained HTML string — no CDN, so it works offline once assets are vendored locally |
| Static graph for PDF | **NetworkX + Matplotlib** | PyVis is HTML-only; the PDF needs a raster image |
| Tables | `st.dataframe` with column config | Sortable, searchable, zero build cost |
| Theming | `.streamlit/config.toml` + injected CSS | See `04_UI_UX_Brief.md` |

**Rejected:** React + FastAPI. It is the better long-term architecture and the wrong hackathon
choice — it costs one full team member for two days and adds a build step, a CORS surface and a
second language for zero judge-visible benefit.

**Offline note:** PyVis by default pulls `vis-network` from a CDN. Vendor the JS/CSS into
`assets/vendor/` and patch the template at build time, or the graph will render blank on an
air-gapped machine. **This is the single most likely cause of a failed demo — test it with
networking disabled before the video is recorded.**

### 3.3 Backend stack
| Item | Choice | Reason |
|---|---|---|
| Service layer | Plain Python modules, no framework | No HTTP layer needed in a single process |
| Data models | **pydantic v2** | Validation at the boundary; makes the provenance triple structurally non-optional |
| Tabular processing | **Polars** primary, **Pandas** fallback | Polars is 5–20× faster on large CSVs and streams via `scan_csv`; Pandas kept for `.xlsx` via `openpyxl` and for any library that demands it |
| Analytical queries | **DuckDB** (optional, in-process) | Fast joins/aggregations over Parquet staging for very large IPDRs; optional so it can be dropped if time runs short |
| Excel | `openpyxl` (read-only mode) | `read_only=True` prevents accidental write-back |
| Email | stdlib `email` + `email.policy.default` | Parses `.eml` headers, `Received` chains, SPF/DKIM result headers |
| Fuzzy matching | **RapidFuzz** | C++ speed; used for header resolution |
| Graph | **NetworkX 3.x** | Pure Python, embedded, no server; has PageRank, betweenness, simple-cycles, ancestors/descendants out of the box |
| ML | **scikit-learn** `IsolationForest` | Unsupervised, needs no labels, fast, and switchable off |
| PDF | **ReportLab** (platypus) | Precise control, no external binary (unlike wkhtmltopdf/WeasyPrint) |
| Templating | **Jinja2** | Reason-code sentences and the JSON brief |
| Synthetic data | **Faker** + custom ring generator | The PoC needs mock data anyway |
| Config | **YAML** (`PyYAML`) | Format plugins and risk weights are data, not code |
| Testing | **pytest** | Correctness of rules is a scored criterion |
| Logging | stdlib `logging` to a rotating file inside the case folder | Distinct from the forensic audit log |

### 3.4 Graph database decision — recorded explicitly
**Decision:** use **NetworkX in memory, persisted to SQLite tables**, not Neo4j.

**Reasons:** Neo4j Community requires a running JVM server process and a port — incompatible
with "runs on a police workstation, offline, no admin rights". Kùzu was evaluated as the
embedded alternative and is a reasonable v2 upgrade path, but NetworkX needs zero new concepts
from the team and case-sized graphs (10³–10⁵ nodes) fit in memory comfortably.

**Trade-off accepted:** NetworkX will not scale to a state-wide multi-million-node graph. That
is explicitly out of scope for v1 and is named as the v2 migration path in the proposal.

### 3.5 AI models and tools
| Use | Tool | Status |
|---|---|---|
| Anomaly detection | scikit-learn `IsolationForest`, `n_estimators=100`, `contamination` tuned on synthetic data, `random_state=42` | **In v1** |
| Feature attribution | Native rule weights; `shap` only if time permits | Rule weights in v1, SHAP optional |
| Semantic header matching | Small local sentence-embedding model | **Deferred** — RapidFuzz plus regex sniffing covers the benchmark formats |
| Narrative brief writing | Local LLM via Ollama | **Deferred to Phase 10 stretch.** If built, output must be template-plus-citation only, grounded strictly in extracted facts, and clearly labelled as machine-generated. A hallucination in a forensic brief is a liability. |
| APK static analysis | Androguard | **Deferred to Phase 10 stretch** |

**No model is called over a network at any point.**

---

## 4. Authentication

**Method:** local, single-workstation credential store. No OAuth, no JWT service, no cloud IdP —
there is no server to authenticate against.

**Purpose:** attribution for chain of custody, not perimeter security. Every audit entry must
name an officer.

| Aspect | Implementation |
|---|---|
| Credential storage | `argon2-cffi` (`argon2id`) password hash in the `officers` table; **never** plaintext or unsalted SHA |
| Fallback | `bcrypt` if argon2 fails to install on the target machine |
| Identity | Badge number + name + rank, entered at first run |
| Session | Server-side row in `sessions` with a 128-bit `secrets.token_urlsafe(32)` token, 8-hour expiry, sliding refresh on activity |
| Session state | Streamlit `st.session_state` holds only the token; all validation hits the DB |
| Lockout | 5 failed attempts → 15-minute lock on that badge number; each failure is an audit entry |
| Re-auth | Required before **Generate Brief** and before **Mark Evidence Excluded** |
| Password reset | Local supervisor account only; reset is an audit entry |

**Explicit non-goal:** this does not protect against an attacker with physical disk access. It
is not claimed to. Disk-level protection is the workstation's BitLocker/LUKS responsibility, and
this is stated in the proposal rather than papered over.

---

## 5. APIs

### 5.1 External APIs
**None.** Zero outbound calls by design. This is a functional requirement, not an omission, and
is verified by a test that runs the full pipeline with networking disabled.

Future integration points are documented but not built: NCRP/CFCFRMS complaint pull, bank freeze
request submission, telecom operator CDR request. Each is named in the v2 roadmap.

### 5.2 Internal service interfaces
Python function contracts, not HTTP. Stable signatures so members can work in parallel against
them from hour one:

```python
# ingest_service.py
def sniff(path: Path) -> DetectedFormat
def hash_file(path: Path) -> str                       # SHA-256, 1 MiB chunked
def propose_mapping(headers: list[str], fmt: DetectedFormat) -> MappingProposal
def ingest_file(case_id: str, path: Path, mapping: Mapping, officer_id: str) -> IngestResult

# correlate_service.py
def extract_entities(case_id: str) -> list[Entity]
def resolve_links(case_id: str) -> list[EntityLink]
def build_graph(case_id: str) -> networkx.MultiDiGraph

# risk_service.py
def compute_features(g: networkx.MultiDiGraph) -> pl.DataFrame
def score(case_id: str, use_anomaly: bool = True) -> list[RiskScore]   # each carries Reasons

# integrity_service.py
def append_audit(case_id, officer_id, action, target, payload) -> AuditEntry
def verify_chain(case_id: str) -> ChainVerification
def verify_evidence(case_id: str) -> list[FileVerification]

# report_service.py
def build_brief(case_id: str, officer_id: str) -> BriefArtifacts   # -> .pdf + .json
```

### 5.3 Format plugin contract
New telecom or bank formats are added as YAML, not Python, so a non-coder can extend the system:

```yaml
# parsers/formats/operator_generic_cdr.yaml
name: generic_cdr
kind: cdr
detect:
  any_header_matches: ["msisdn", "a-party", "calling", "imei", "cell id"]
  min_matches: 2
columns:
  caller:     ["calling no", "a-party", "a party", "msisdn", "caller", "from number"]
  callee:     ["called no", "b-party", "b party", "callee", "to number"]
  start_time: ["call date", "date time", "start time", "call_start"]
  duration_s: ["duration", "dur(s)", "call duration"]
  imei:       ["imei", "equipment id"]
  imsi:       ["imsi", "sim id"]
  cell_id:    ["cell id", "first cgi", "lac-ci"]
  call_type:  ["type", "call type", "in/out"]
datetime_formats: ["%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%b-%y %I:%M %p"]
```

---

## 6. Database

**Engine:** SQLite 3 (Python stdlib `sqlite3`), one file per case, extension `.pramaan`.

**Reasons:** zero-install, single-file portability (a case file can be copied to a pen drive and
attached to a case diary), ACID transactions, and no server process.

**Settings applied at open:**
```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = FULL;   -- integrity over speed; audit writes must survive a crash
```

**Case folder layout:**
```
CASE_2026_0142/
├── case.pramaan            # SQLite database
├── evidence/               # read-only copies of originals, named <sha256[:12]>_<original>
├── staging/                # Parquet intermediates (regenerable, excluded from hashing)
├── exports/                # generated PDF and JSON briefs
├── manifest.json           # SHA-256 of every evidence file + audit chain head
└── app.log                 # technical log (NOT the forensic audit log)
```

Full table definitions are in `05_Backend_Schema.md`.

---

## 7. Security requirements

| # | Requirement | Implementation |
|---|---|---|
| S1 | Source evidence must never be modified | Originals copied in, then `chmod 0444` / read-only attribute; all reads via `open(..., 'rb')` and `openpyxl(read_only=True)`; a startup self-test asserts the copy hash equals the original hash |
| S2 | Tamper evidence must be detectable | SHA-256 per file in `manifest.json`; `verify_evidence()` re-hashes and diffs |
| S3 | The audit log must be tamper-evident | Hash chain: `entry_hash = SHA256(prev_hash ‖ seq ‖ officer_id ‖ ts ‖ action ‖ payload_hash)`; genesis entry uses 64 zeros; `verify_chain()` walks and reports the first break by sequence number |
| S4 | Attribution | Every mutating action records `officer_id`; unauthenticated writes are impossible at the service layer |
| S5 | Credentials at rest | argon2id, unique salt per user; no password ever logged |
| S6 | Path traversal on ingest | Resolve and validate every path stays within the case folder; reject symlinks |
| S7 | Zip/archive bombs | Reject archives over a configured size and nesting depth; do not auto-extract nested archives |
| S8 | Malicious spreadsheet content | Never evaluate formulas (`data_only=True`); never execute macros; `.xlsm` macro streams are ignored and the file is flagged |
| S9 | Untrusted content in evidence is data, never instruction | Text pulled from chats, emails or dumps is never interpreted as a command by any component, including any future LLM stage |
| S10 | PII minimisation in logs | `app.log` records file hashes and row counts, never account numbers or personal data |
| S11 | No outbound network | Enforced by design; verified by an offline integration test |
| S12 | Report authenticity | Report footer carries the audit chain head hash and the report's own SHA-256; optional Ed25519 detached signature via `cryptography` (stretch) |

**Legal note for the team:** the report includes a certificate section for electronic evidence.
Verify the exact required wording and the current statutory reference against a primary legal
source before submission. Do not rely on wording reproduced from memory, including from this
document.

---

## 8. Performance requirements

| Operation | Target | Technique |
|---|---|---|
| CSV parse | ≥ 20,000 rows/sec, 4 cores | Polars `scan_csv` lazy frames, projection pushdown |
| SHA-256 hashing | ≥ 500 MB/s | `hashlib` with 1 MiB chunked reads |
| Entity extraction | ≥ 50,000 rows/sec | Pre-compiled regex, vectorised Polars string ops, no per-row Python loops |
| Header fuzzy match | < 50 ms per file | RapidFuzz `process.extractOne` over a small canonical set |
| Graph build | < 3 s for 50,000 edges | Bulk `add_edges_from`, not per-edge calls |
| Betweenness centrality | < 5 s for 10,000 nodes | `k`-sample approximation (`k=500`) above 5,000 nodes; record `k` in the report for reproducibility |
| Risk scoring | < 2 s for 10,000 endpoints | Vectorised feature frame; rules as column expressions |
| PDF generation | < 3 s | ReportLab, pre-rendered graph PNG |
| Full pipeline, 5 files / 100k rows | **< 5 min wall clock** | End-to-end benchmark, run in CI, number shown in the demo |
| Peak RAM | < 2 GB | Streaming reads; Parquet staging; never `read_csv` a whole IPDR |

A benchmark script (`benchmarks/run_benchmark.py`) prints a rows/second table. **Put that number
on screen in the demo video** — it is the most direct evidence for the 30% scalability
criterion.

---

## 9. Third-party integrations

**Runtime integrations: none.** All dependencies are libraries, vendored at install time.

| Package | Purpose | Licence class |
|---|---|---|
| streamlit | UI | Apache-2.0 |
| polars, pandas, openpyxl, pyarrow | Tabular IO | MIT / BSD / Apache-2.0 |
| duckdb | Optional analytical queries | MIT |
| networkx, pyvis, matplotlib | Graph model and rendering | BSD / BSD / PSF-like |
| scikit-learn, numpy | Anomaly detection | BSD |
| rapidfuzz | Header matching | MIT |
| pydantic | Domain models | MIT |
| reportlab | PDF | BSD |
| jinja2 | Templating | BSD |
| argon2-cffi, cryptography | Auth and signing | MIT / Apache-2.0 |
| faker | Synthetic data | MIT |
| pyyaml | Config and format plugins | MIT |
| pytest | Tests | MIT |

All permissive. Record the resolved versions in `requirements.lock` and include the list in the
proposal — evaluators for a law-enforcement tool do look at licence provenance.

---

## 10. Technical decisions with reasons (summary table)

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Deployment model | Offline desktop monolith | Web app / cloud | Air-gapped workstation requirement; 20% innovation criterion names offline capability |
| UI | Streamlit | React + FastAPI | Saves a full team-member's time for zero judge-visible gain |
| Database | SQLite, one file per case | Postgres / Neo4j server | Portability, zero install, a case file is a seizable artifact |
| Graph | NetworkX in memory | Neo4j, Kùzu | No server; team already knows it; Kùzu named as the v2 path |
| DataFrame | Polars first | Pandas only | 5–20× faster on the bulk logs the 30% criterion measures |
| Risk model | Weighted rules primary, ML secondary and disableable | End-to-end ML classifier | Explainability is required; false links are penalised; we have no labelled data |
| Explainability | Native rule weights and reason codes | SHAP-only | Rule contributions are exact and quotable; SHAP is an optional extra |
| PDF | ReportLab | WeasyPrint / wkhtmltopdf | No external binary, no install friction on a locked-down workstation |
| Password hashing | argon2id | SHA-256, bcrypt-only | Modern memory-hard KDF; bcrypt retained only as an install fallback |
| Audit integrity | SHA-256 hash chain in SQLite | Blockchain / external ledger | Achieves tamper evidence offline with no network, no consensus, no theatre |
| LLM brief writing | Deferred to stretch | Core feature | Hallucination risk in a court document outweighs the demo appeal |
| Format support | 3 formats parsed perfectly + YAML plugin contract | 9 formats parsed loosely | Accuracy is scored; breadth is not |

---

## 11. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| PyVis pulls `vis-network` from a CDN and the graph is blank offline | **Demo fails** | Vendor JS/CSS locally in Phase 1; test with networking off before recording |
| Isolation Forest produces noise on small synthetic data | Hurts the 25% accuracy criterion | Rules are primary; ML only re-ranks; provide a toggle and document thresholds |
| Over-aggressive correlation creates false links | Directly penalised | Confidence thresholds per link type; name matching excluded; false-link rate measured and published |
| Streamlit re-runs the whole script on every widget interaction | Slow, janky demo | `@st.cache_data` / `@st.cache_resource` on parse, graph build and scoring; keyed on case id plus manifest hash |
| Mock data is unrealistic and the demo is unconvincing | Judge scepticism | Build the generator first, plant one coherent ring, include realistic noise and decoys |
| Scope creep into APK analysis and LLM | Nothing finishes | Both are Phase 10, gated on a complete end-to-end path |
| Four people editing one schema | Merge chaos | Lock `05_Backend_Schema.md` on day one; schema changes require all four to agree |
