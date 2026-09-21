# Trace-Proof — PRAMAAN

> **PRAMAAN** — *Provenance-anchored Risk Analysis of Mule Account Networks*

**Submission for:** AI-Powered Unified Cyber Fraud Analysis & Digital Artifact Correlator  
**Team size:** 4 · **Round:** Screening  

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Offline](https://img.shields.io/badge/Runs-Fully%20Offline-green)](#non-functional-requirements)
[![License](https://img.shields.io/badge/Stack-Streamlit%20%2B%20SQLite-orange)](#tech-stack)

---

## What is Trace-Proof?

Trace-Proof is an **offline forensic triage workstation** for cyber-fraud investigations. It ingests fragmented evidence from multiple incompatible formats (CDRs, IPDRs, bank statements, emails, Android dumps), automatically links entities hiding inside them, ranks suspect accounts with plain-language reasons, and produces a one-page investigative brief where **every claim traces to a source file, a row number and a SHA-256 hash**.

> **The positioning in one sentence:**  
> Other tools tell an investigating officer *what* is suspicious.  
> Trace-Proof also proves *why* — and proves the evidence behind the *why* has not been altered since it was seized.

---

## The Problem It Solves

Law enforcement agencies receive hundreds of financial cyber-fraud complaints daily. Investigating officers triage evidence manually across files that don't share a format or schema:

| Evidence type | Format chaos |
|---|---|
| CDRs (Call Detail Records) | CSV/Excel — column names differ by telecom operator |
| IPDRs (IP Detail Records) | CSV — often hundreds of thousands of rows |
| Bank & UPI settlement sheets | Excel — column names differ by bank |
| Email headers | `.eml` files — spoofing evidence hides in `Received` chains |
| Android system / app dumps | `.txt` / `.json` — semi-structured |

**Four concrete failures follow:**

| Failure | Consequence |
|---|---|
| Manual cross-referencing across 5+ file formats | Hours lost during the "golden hour"; funds are gone |
| Shared identifiers (IMEI, IMSI, UPI, IP subnet) missed by eye | Entire arms of a fraud ring go undetected |
| Risk judgements live only in the officer's head | Cannot be defended in court or transferred |
| Evidence opened and re-saved in Excel | Integrity is compromised; admissibility challenged |

---

## Key Features

### F1 · Multi-Source Ingestion & Normalisation
Drop a folder of mixed evidence. The system detects each file type by content (not extension), fuzzy-matches unknown column headers to a canonical schema, and normalises everything into a single Entity/Event model.

### F2 · Evidence Integrity Layer *(always on)*
Every file is SHA-256 hashed at ingestion. Originals are opened read-only and never written back. Every analytic action is written to a **hash-chained audit log** where each entry embeds the hash of the previous — a deleted or edited entry breaks the chain visibly. One-click **Verify Integrity** re-hashes all evidence and flags any change.

### F3 · Entity Correlation Engine
Extracts and resolves entities — phone numbers, IMEI, IMSI, UPI handles, bank accounts, IFSC codes, IP addresses, MAC addresses, emails, APK signing certificates — and links them on shared attributes with confidence values and human-readable rationale.

### F4 · Mule Network Graph Visualiser
A directional graph mapping `victim → intermediary mule nodes → cash-out point`. Nodes are sized by risk, edges by amount. Betweenness and PageRank centrality surfaces the **coordinating node**, which is rarely the node holding the most money.

### F5 · Explainable Risk Scoring
A transparent weighted-rule engine produces a 0–100 score per endpoint. Isolation Forest refines ranking only (and can be disabled). Every score expands into plain-language reason codes an officer can paste into a report — e.g. *"forwarded 96% of credited funds within 11 minutes across 3 hops"* — and every reason links back to the exact evidence rows.

### F6 · Investigative Brief Generation
A one-page PDF (and matching JSON) containing: case header, fraud timeline, ranked prime suspects with reasons, linked phone/account clusters, network graph image, seizure recommendations, and a hash appendix.

### F7 · Case & Audit Management
Cases are created, listed and reopened. Each case is one portable `.pramaan` (SQLite) file. The audit log is browsable and exportable.

---

## Quickstart (3 commands)

```bash
# 1. Clone and set up
git clone https://github.com/AtharvSharma9/Trace-Proof.git
cd Trace-Proof
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 2. Generate the sample dataset (seed = 42, ~130k rows, 7 files)
python tools/mockgen/generate.py --seed 42

# 3. Launch the app
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Log in with your officer credentials, create a new case, and drop the generated `sample_data/` folder to begin.

> **No internet required at runtime.** All JS/CSS assets (vis-network, fonts) are vendored locally.

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| UI | **Streamlit 1.3x** | Python-native; no frontend member needed |
| Graph rendering | **PyVis** (vendored offline) + **NetworkX** | Interactive HTML graph; static PNG for PDF |
| DataFrame | **Polars** primary, Pandas fallback | 5–20× faster on bulk CDR/IPDR logs |
| Database | **SQLite** (one `.pramaan` file per case) | Zero-install, portable, seizable artifact |
| Domain models | **Pydantic v2** | Provenance triple structurally non-optional |
| Fuzzy matching | **RapidFuzz** | C++ speed; used for header resolution |
| ML anomaly | **scikit-learn IsolationForest** | Unsupervised, switchable off, `random_state=42` |
| PDF | **ReportLab** | No external binary; runs on locked-down workstations |
| Auth | **argon2-cffi** (argon2id) | Memory-hard KDF; attribution for chain of custody |
| Testing | **pytest** | Rules correctness is a scored criterion |

**Language:** Python 3.11 only — one language for all four team members.

---

## Repository Structure

```
Trace-Proof/
├── app.py                    # Streamlit entry point + router
├── views/                    # One module per screen (S00–S17)
├── services/                 # case, ingest, correlate, risk, integrity, report
├── domain/models.py          # Pydantic models: Entity, Event, EntityLink, RiskScore, AuditEntry
├── engine/
│   ├── parsers/              # cdr.py, bank.py, eml.py, android_dump.py + formats/*.yaml
│   ├── mapping/              # Content sniffing + fuzzy header resolution
│   ├── graph/                # Build, metrics, patterns (NetworkX)
│   ├── rules/                # R01–R12 weighted risk rules
│   ├── anomaly/              # IsolationForest
│   └── integrity/            # SHA-256 hashing, hash chain
├── db/                       # schema.sql, init.py
├── config/                   # canonical_schema.yaml, risk_weights.yaml, correlation.yaml
├── assets/                   # fonts/, vendor/ (vis-network), icons/
├── tools/mockgen/            # Synthetic data generator (generate.py)
├── benchmarks/               # run_benchmark.py — prints rows/sec table
├── tests/                    # pytest suite
└── docs/                     # The six design documents (read before coding)
    ├── 01_PRD.md
    ├── 02_TRD.md
    ├── 03_App_Flow.md
    ├── 04_UI_UX_Brief.md
    ├── 05_Backend_Schema.md
    └── 06_Implementation_Plan.md
```

---

## Design Documents

Read these **in order** before touching any code. They are the single source of truth.

| # | File | Answers |
|---|------|---------|
| 1 | [`01_PRD.md`](./01_PRD.md) | What we are building and for whom |
| 2 | [`02_TRD.md`](./02_TRD.md) | How it is built technically |
| 3 | [`03_App_Flow.md`](./03_App_Flow.md) | Every screen, action and state |
| 4 | [`04_UI_UX_Brief.md`](./04_UI_UX_Brief.md) | How it looks and feels |
| 5 | [`05_Backend_Schema.md`](./05_Backend_Schema.md) | How data is stored and connected |
| 6 | [`06_Implementation_Plan.md`](./06_Implementation_Plan.md) | The exact build order (phase by phase) |

### Using these with an AI coding tool

Load all six files into context, then send this prompt **before** asking for any code:

> Read all the documents carefully. Do not start coding yet. First summarize what you understood, identify missing details, and create a build plan. After that, we will build the app phase by phase.

Then build phase by phase using `06_Implementation_Plan.md`. **Do not ask for the whole app in one shot.**

---

## Build Phases

| Phase | What gets built | Owner | Hours |
|---|---|---|---|
| **0** — Setup & contracts | Repo structure, stubs, schema, domain models | All | 3 |
| **1** — Mock data generator | 7 synthetic evidence files, ~130k rows, 1 planted fraud ring | A | 5 |
| **2** — Integrity foundation | SHA-256 hashing, hash-chained audit log, tamper detection | C | 4 |
| **3** — Ingestion & mapping | Parsers, fuzzy header resolution, entity extraction | A | 10 |
| **4** — Correlation & graph | Entity resolution, NetworkX graph, centrality, path finding | B | 8 |
| **5** — Risk scoring | R01–R12 rules, features, IsolationForest, reason codes | C | 7 |
| **6** — Brief generation 🏁 | PDF + JSON report, hash appendix — **end-to-end path closes** | D | 6 |
| **7** — UI screens | All 17 Streamlit screens | D + B | 12 |
| **8** — Testing & benchmarks | pytest suite, accuracy table, benchmark ≥ 20k rows/sec | C + all | 6 |
| **9** — Screening deliverables | Proposal, PoC repo, 3-min demo video | D + all | 8 |
| **10** — Stretch *(if ahead)* | APK analysis, local LLM brief, PyInstaller build | — | — |

> **Governing rule:** reach the Phase 6 milestone (folder → PDF from command line) before building any UI. A complete crude pipeline beats a beautiful incomplete one on every criterion.

---

## Performance Targets

| Metric | Target |
|---|---|
| Folder drop → generated brief | < 5 minutes for a 5-file, 100k-row case |
| CSV parse throughput | ≥ 20,000 rows/second on a 4-core laptop |
| Column auto-mapping accuracy | ≥ 90% correct without officer correction |
| Entity extraction recall (planted ring) | ≥ 95% |
| **False link rate** | **< 2%** — the most important accuracy metric |
| Peak RAM | < 2 GB |
| Internet calls at runtime | **0** |

---

## Non-Functional Requirements

- **Offline:** zero network calls at runtime; tested with networking disabled.
- **Portable:** runs from a folder on a standard Windows 10/11 workstation, 8 GB RAM, no admin rights.
- **Non-destructive:** source evidence files are opened read-only; a working copy is stored inside the case folder.
- **Deterministic:** the same inputs + thresholds produce the same scores. Random seeds are fixed (`42`) and recorded in the report.
- **Auditable:** no analytic result exists without a corresponding audit log entry.
- **Legible:** the generated brief must be readable when printed in black and white.

---

## User Roles

| Role | Can do |
|---|---|
| **Investigating Officer** | Create cases, ingest evidence, confirm mappings, run correlation, generate briefs |
| **Forensic Analyst** | Everything above, plus verify integrity, export audit log, view parse diagnostics |
| **Supervisor** | Open any case read-only, view and export briefs |

> **No one can delete evidence.** Evidence can only be marked `EXCLUDED` with a mandatory reason — which is itself an audit entry.

---

## Screening Deliverables

| Required deliverable | Source |
|---|---|
| Technical Proposal (2–3 pages) | `02_TRD.md` §2, §3, §7 + `05_Backend_Schema.md` §1 |
| PoC / code prototype | Phases 0–4 of `06_Implementation_Plan.md` |
| Demo video (max 3 min) | Phase 9 storyboard in `06_Implementation_Plan.md` |

---

## Definition of Done (v1)

- [ ] Folder drop → PDF brief in under 5 minutes, under 5 clicks, no terminal use
- [ ] Every fact in the brief traces to a file, a row, and a SHA-256
- [ ] Tampering with any evidence file is detected and named
- [ ] The audit chain verifies from genesis and reports any break by sequence number
- [ ] The planted ring is recovered completely; decoys produce zero false links
- [ ] Every risk score carries at least one quotable, evidence-backed reason
- [ ] The full pipeline runs with networking disabled, graph screen included
- [ ] Benchmark ≥ 20,000 rows/sec; peak RAM < 2 GB
- [ ] `pytest` green; accuracy table generated from a real run
- [ ] Proposal, PoC repository and a rehearsed 3-minute video are complete

---

## Day-One Warnings

1. **Vendor `vis-network` locally** before anything else in Phase 7. The default PyVis template fetches it from a CDN — the graph renders blank on an air-gapped machine.
2. **Never let a date format be inferred.** `03/04/2026` parsed as April 3rd instead of March 4th silently destroys the entire timeline.
3. **Enforce `entity_a_id < entity_b_id` ordering on symmetric links from the first commit.** Retrofitting it later means recomputing every centrality score.
4. **Do not skip Phase 0.** Four people writing against four different implicit schemas is the normal way a four-person hackathon team fails.
5. **Verify the electronic-evidence certificate wording against a primary legal source.** Do not reproduce statutory text from memory or from these documents.

---

*Trace-Proof · PRAMAAN v1.0 · Hackathon Screening Round*
