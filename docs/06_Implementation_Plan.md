# 6. Implementation Plan

**Project:** PRAMAAN
**Team:** 4 members (A, B, C, D)
**Prerequisites:** `01_PRD.md` → `05_Backend_Schema.md`

---

## 0. How to read this plan

Phases are ordered by **dependency**, not by importance. Each phase names its deliverable, its
owner, its exit criteria and its demo value. Do not start a phase until its predecessor's exit
criteria are met.

**The governing rule: build the thin end-to-end path first.** By the end of Phase 6 the system
must go from a dropped folder to a generated PDF, even if every stage is crude. Depth is added
afterwards. A deep ingestion engine with no graph scores far worse than a shallow complete
pipeline, because the rubric rewards the whole path.

### Role assignment

| Member | Owns | Primary skills |
|---|---|---|
| **A** | Ingestion, parsers, mapping engine, mock data generator | Python, Polars, regex, data engineering |
| **B** | Entity resolution, correlation, graph model, graph UI | Graph theory, NetworkX, PyVis |
| **C** | Risk rules, features, anomaly model, integrity layer, tests | scikit-learn, cryptography basics, pytest |
| **D** | Streamlit shell, all screens, PDF/JSON brief, proposal, demo video | UI, ReportLab, technical writing |

---

## PHASE 0 — Setup and contracts
**Duration:** 2–3 hours · **Everyone, together, in one room**

This phase is non-negotiable and is where most four-person hackathon teams lose a day by
skipping it.

**Steps**
1. Create the repository with the agreed structure (below). Push immediately.
2. `python -m venv` / `uv venv`, pin `requirements.txt`, everyone installs and confirms imports.
3. Implement `05_Backend_Schema.md` as `db/schema.sql` **verbatim** and a `db/init.py` that
   creates both databases.
4. Implement the pydantic domain models in `domain/models.py` — `Entity`, `Event`, `EntityLink`,
   `RiskScore`, `RiskReason`, `AuditEntry`. **Make the provenance triple required on `Event`.**
5. Write empty stub functions for every service signature in `02_TRD.md` §5.2, each returning
   typed fake data. Commit. Now all four members can build against real signatures immediately
   instead of waiting on each other.
6. Agree the canonical field vocabulary (`caller`, `callee`, `start_time`, `debit_account`, …)
   and write it into `config/canonical_schema.yaml`.
7. Set up `pytest` with one passing smoke test and a `make check` / `run_checks.bat`.

**Deliverable:** a repo that runs, creates a case file, and exposes stub services.
**Exit criteria:** all four members can run `streamlit run app.py` and see a login screen, and
`pytest` passes.

**Repository structure**
```
pramaan/
├── app.py                  # Streamlit entry point + router
├── views/                  # one module per screen S00–S17
├── services/               # case, ingest, correlate, risk, integrity, report
├── domain/models.py        # pydantic models
├── engine/
│   ├── parsers/            # cdr.py bank.py eml.py android_dump.py + formats/*.yaml
│   ├── mapping/            # sniffing + fuzzy header resolution
│   ├── graph/              # build, metrics, patterns
│   ├── rules/              # R01–R12
│   ├── anomaly/            # isolation forest
│   └── integrity/          # hashing, hash chain
├── db/                     # schema.sql, init.py, migrations/
├── config/                 # canonical_schema.yaml, risk_weights.yaml, correlation.yaml
├── assets/                 # fonts/, vendor/ (vis-network), icons/, emblem placeholder
├── tools/mockgen/          # synthetic data generator
├── benchmarks/
├── tests/
└── docs/                   # these six documents
```

---

## PHASE 1 — Mock data generator
**Duration:** 4–5 hours · **Owner: A** (C assists on the ground-truth file)

Built first because every other phase needs believable input, and because the PoC deliverable
explicitly requires demonstration on a mock dataset.

**Steps**
1. Generate a population: 200 innocent phone numbers, 150 bank accounts, 80 UPI handles, 60
   devices with IMEI/IMSI, background call and transaction noise.
2. Plant **one coherent fraud ring**: 1 victim → 1 fraudster contact number → 3 layer-1 mules →
   2 layer-2 mules → 1 ATM cash-out. Funds move in 11 minutes across 3 hops, with 96%
   pass-through at each node.
3. Plant the correlation hooks deliberately, so each rule has something to find: two mules
   sharing one IMEI; one IMEI paired with four IMSIs; one beneficiary UPI handle recurring
   across three "unrelated" victims; a phishing `.eml` with a failing SPF and a mismatched
   `Return-Path`; an inbound spoofed call 9 minutes before the victim's first debit.
4. Add realistic **decoys** — a legitimate business account with high fan-in, a family sharing
   one handset, two unrelated people on the same CGNAT /24. Decoys are what prove the system
   avoids false links, and they are worth more to the accuracy score than more mules.
5. Write out: `cdr_operator_a.csv`, `cdr_operator_b.csv` (deliberately different headers),
   `ipdr_sample.csv`, `bank_statement_hdfc.xlsx`, `upi_settlement.xlsx`, `phishing_mail.eml`,
   `android_dump.json`.
6. Write `ground_truth.json` listing the planted ring, expected entities and expected links.
7. Make the seed a parameter, default 42.

**Deliverable:** `tools/mockgen/generate.py` producing 7 files, ~130k rows, plus ground truth.
**Exit criteria:** an officer-plausible dataset a teammate can open in Excel and believe.
**Demo value:** high — a convincing dataset is the difference between a demo and a toy.

---

## PHASE 2 — Integrity foundation
**Duration:** 3–4 hours · **Owner: C**

Built before ingestion because every ingestion step must write an audit entry. Bolting integrity
on afterwards means retrofitting every call site.

**Steps**
1. `hash_file()` — SHA-256, 1 MiB chunked, with a progress callback.
2. `canonical_json()` — sorted keys, no whitespace, UTF-8.
3. `append_audit()` — computes `payload_hash`, reads the previous head, computes `entry_hash`
   with `\x1f` field delimiters, inserts inside a transaction. Must be safe under concurrent
   calls (take a write lock on the case DB).
4. Genesis entry on case creation, `prev_hash` = 64 zeros.
5. `verify_chain()` — walk from genesis, recompute every hash, return the first broken `seq`.
6. `verify_evidence()` — re-hash every file, diff against `evidence_files.sha256`.
7. `manifest.json` writer and reader.
8. Install the append-only triggers.
9. **Tests, and these matter most:** tamper with one byte of an evidence file → detected; edit an
   audit payload directly via SQL → the trigger blocks it; bypass the trigger by rebuilding the
   table → `verify_chain()` reports the exact broken sequence number.

**Deliverable:** `engine/integrity/` and `services/integrity_service.py`, fully tested.
**Exit criteria:** the tamper tests pass and name the correct file and sequence number.
**Demo value:** very high — this is the 20-second moment that wins the 25% integrity criterion.

---

## PHASE 3 — Ingestion and mapping
**Duration:** 8–10 hours · **Owner: A**

**Steps**
1. `sniff()` — detect kind by content: read the first 5 rows, normalise headers, match against
   format plugin signatures, fall back to regex content sniffing (a 15-digit Luhn-valid number
   suggests IMEI; `\w+@\w+` without a dot suggests a UPI handle; `Received:` chains indicate
   `.eml`).
2. Fuzzy header mapping with RapidFuzz against `canonical_schema.yaml`; produce a per-field
   confidence score.
3. Parsers: `cdr.py`, `bank.py`, `upi.py`, `eml.py`, `android_dump.py`. Use Polars `scan_csv`
   for CSV, `openpyxl(read_only=True, data_only=True)` for Excel, stdlib `email` for `.eml`.
4. Multi-format datetime parsing with an explicit list of accepted formats and an IST→UTC
   conversion. **Do not let pandas infer** — inferred date formats silently flip day and month
   on `03/04/2026` and quietly destroy the entire timeline.
5. Row-level provenance: every parsed row carries `evidence_file_id`, `source_row`,
   `source_sha256`. Rows that fail go to `parse_rejects` with a reason.
6. Entity extraction with pre-compiled regex and Polars vectorised string operations. Apply the
   normalisation rules from `05_Backend_Schema.md` §3.4 — this is where false-link prevention
   actually happens.
7. Bulk insert: drop indexes, `executemany` in one transaction, recreate indexes.
8. Save a confirmed mapping as a YAML format plugin.
9. Audit entries at every step.

**Deliverable:** drop the Phase 1 folder, get populated `entities` and `events` tables.
**Exit criteria:** all 7 mock files ingest; ≥ 95% of ground-truth entities recovered;
< 1% rejected rows; ≥ 20,000 rows/sec measured.
**Demo value:** high — this is the 30% scalability criterion, and the rows/second figure is
the evidence for it.

---

## PHASE 4 — Correlation and graph
**Duration:** 6–8 hours · **Owner: B**

**Steps**
1. `resolve_links()` — implement each link type from `05_Backend_Schema.md` §3.7 as a separate,
   individually testable function.
2. Enforce the `entity_a_id < entity_b_id` ordering convention for symmetric links. Skipping
   this produces duplicate reciprocal edges and silently corrupts every centrality score
   downstream.
3. Assign confidence per link type; keep `SHARED_IP_SUBNET` below the default threshold so it
   corroborates but never links alone.
4. Generate a human-readable `rationale` for every link at creation time — *"IMEI
   35xxxxxxxx1234 appears with both 98xxxxxx10 and 97xxxxxx55 on 14 occasions"*. Writing it
   later means writing it twice.
5. `build_graph()` — a NetworkX `MultiDiGraph`. Nodes are entities; edges are `FUND_FLOW`,
   `CALL` and correlation links. Bulk-add edges; never add them one at a time in a loop.
6. Pattern detection: fan-in, fan-out, layering chains, cycles, pass-through nodes (credit then
   debit of ≥ 85% within the window).
7. Centrality: PageRank and betweenness, with `k`-sampling above 5,000 nodes, and record `k`.
8. `find_cashout_paths()` — all simple paths from victim-role nodes to cash-out-role nodes, with
   a hop cap to avoid combinatorial explosion.
9. Persist to `graph_snapshots` including the cached layout.

**Deliverable:** `services/correlate_service.py` and `engine/graph/`.
**Exit criteria:** the planted ring is recovered end to end; every ground-truth link is found;
**the decoys produce no false links**; the false-link rate is measured and recorded.
**Demo value:** very high — the graph is explicitly named in the 25% usability criterion.

---

## PHASE 5 — Risk scoring and explanation
**Duration:** 6–7 hours · **Owner: C**

**Steps**
1. `compute_features()` — build one Polars feature frame per entity: pass-through ratio, in/out
   degree, distinct counterparties, time deltas, account age, IMSI count per IMEI, SPF/DKIM
   results, centrality values.
2. Implement R01–R12 as pure functions with the signature
   `(features_row, config) -> (triggered, raw_value, points, plain_text, evidence_refs)`. Pure
   functions are individually testable, which is the whole reason the rules are defensible.
3. Load weights and thresholds from `config/risk_weights.yaml`; hash the config into
   `weights_hash`.
4. `score = min(100, sum(points))`; band by the thresholds in `04_UI_UX_Brief.md`.
5. Persist reasons **including non-triggered rules**, with `triggered = 0`.
6. Populate `reason_evidence_refs` for every triggered rule. A reason with no evidence reference
   is a bug, and should fail a test.
7. Isolation Forest on the feature frame, `random_state=42`, used only to adjust rank order
   within a band, never to change the band itself. Guard for fewer than 30 samples and degrade
   gracefully with a warning.
8. Versioning: set `is_current = 0` on prior scores and insert new rows on each run.

**Deliverable:** `services/risk_service.py`, `engine/rules/`, `engine/anomaly/`.
**Exit criteria:** planted mules score Critical; decoys (the legitimate high-fan-in business, the
shared family handset) score Medium or below; every score carries at least one reason with a
working evidence reference; turning the ML off changes ranking but not correctness.
**Demo value:** very high — reason codes are what make the tool quotable in a report.

---

## PHASE 6 — Brief generation (end-to-end path closes here)
**Duration:** 5–6 hours · **Owner: D**

**Steps**
1. JSON brief first — it is the data contract, and the PDF is a rendering of it.
2. ReportLab one-page A4 layout per `04_UI_UX_Brief.md` §11.
3. Static graph image via NetworkX + Matplotlib at 300 DPI, with a legend.
4. Timeline strip.
5. Prime suspects table, seizure recommendations, evidence hash appendix (not disableable).
6. Footer on every page: case number, page n of m, audit head hash, the report's own SHA-256.
7. Certificate section — **verify the statutory wording against a primary legal source.**
8. Write to `case/exports/`, insert a `reports` row, audit `BRIEF_GENERATED`.
9. Pre-generation blocking checks: integrity verified within 24 h, at least one suspect, no
   unresolved low-confidence mappings.

**Deliverable:** `services/report_service.py`.
**Exit criteria:** **folder → PDF works end to end from the command line.**
**🏁 This is the milestone that matters. If the hackathon ended here, you would have a complete,
scoreable submission. Everything after this is improvement, not completion.**

---

## PHASE 7 — UI screens
**Duration:** 10–12 hours · **Owner: D**, with B on the graph screen

Built after the pipeline works headlessly, so the UI wraps something real rather than driving
development.

**Build order** (by demo value, so that an incomplete UI is still demonstrable):
1. Shell: sidebar, router, session state, theme, local fonts.
2. S01 Login + S00 First-Run Setup.
3. S02 Case List + S03 New Case (including **Generate sample case**, which is the team's own
   fastest rehearsal loop).
4. S04 Case Dashboard with the pipeline strip.
5. S05 Ingest with the detection table and live rows/second.
6. S06 Confirm Mapping.
7. S09 Network Graph — **vendor `vis-network` locally and test offline on day one of this
   phase**, and implement the static Matplotlib fallback at the same time.
8. S10 Risk Board with reason cards.
9. S11 Entity Detail with the evidence drill-down.
10. S13 Integrity Verify.
11. S15 Brief Builder.
12. S07 Evidence Register, S08 Entities & Links, S14 Audit Log, S12 Timeline, S16 Settings.

**Throughout:** `@st.cache_data` on parse, graph build and scoring, keyed on case id plus
manifest hash. Without caching, Streamlit re-runs everything on every widget interaction and the
demo will look broken.

**Exit criteria:** five clicks from folder to brief, with no terminal use anywhere.
**Demo value:** this is the entire 25% usability criterion.

---

## PHASE 8 — Testing, benchmarking and hardening
**Duration:** 5–6 hours · **Owner: C leads, everyone contributes**

**Steps**
1. Unit tests: each parser, each normalisation rule, each of R01–R12, each link type.
2. Integrity tests: byte tamper, chain break, trigger block, duplicate ingest.
3. Accuracy test against `ground_truth.json` — entity recall, link precision, **false-link
   rate**, planted-ring recovery. Print these as a table; they go in the proposal.
4. Integration test: full pipeline on the mock folder, asserting the top suspect is the planted
   layer-1 mule.
5. **Offline test: disable networking and run the whole pipeline including the graph screen.**
   This catches the CDN problem, which is the single most likely cause of a failed demo.
6. Benchmark: `benchmarks/run_benchmark.py` printing rows/second, peak RAM and wall clock at
   10k / 100k / 500k rows.
7. Error-path hardening: corrupt file, empty file, password-protected Excel, missing column, a
   1 GB CSV. None may crash the app.
8. A cold-start run on a second machine from a clean clone, following the README only.

**Deliverable:** a green test suite and a benchmark table.
**Exit criteria:** the accuracy table and the benchmark table are ready to paste into the
proposal.

---

## PHASE 9 — Screening deliverables
**Duration:** 6–8 hours · **Owner: D leads, all contribute content**

### 9.1 Technical proposal (2–3 pages)
Source the content from the documents you already have:
- Architecture diagram — `02_TRD.md` §2.2 and §2.4
- Ingestion pipeline — `02_TRD.md` §2.4 and `06` Phase 3
- Graph modelling approach — `05_Backend_Schema.md` §3.7 and `06` Phase 4
- Evidentiary integrity — `02_TRD.md` §7 and `05_Backend_Schema.md` §3.12
- **Include the measured accuracy and benchmark tables.** Numbers from a real run beat adjectives.
- Include the technical-decisions table from `02_TRD.md` §10. Showing what you rejected and why
  is what distinguishes an engineering proposal from a feature list.

### 9.2 Proof of concept
The repository itself, plus a `README.md` with a three-command quickstart and the sample dataset
committed so an evaluator can run it without generating data.

### 9.3 Demo video (max 3 minutes)

| Time | Shot | Point being made |
|---|---|---|
| 0:00–0:20 | The problem: a victim, ₹4.8 lakh gone in 11 minutes, evidence in 7 incompatible files | Stakes and context |
| 0:20–1:00 | Drop the folder. File types detected, hashes computed, **rows/second visible on screen** | Scalability (30%) |
| 1:00–1:40 | Correlation runs. Shared IMEI across 4 SIMs and a recurring UPI handle surface automatically | Entity correlation |
| 1:40–2:20 | The graph. Victim → 3 mules → ATM cash-out, highlighted path, centrality-ranked kingpin | Usability (25%) |
| 2:20–2:45 | Risk Board. Click the top suspect, click a reason, land on the raw bank row with its file hash | Explainability + the core promise |
| 2:45–3:00 | Tamper one byte, click Verify, the screen goes red and names the file | Integrity (25%) — the closing image |

**Recording notes:** fixed resolution, slow mouse, no dead air, one clear narrative with one
planted ring. Rehearse against the 3-minute cap; run out of time and the tamper moment — your
strongest 15 seconds — is what gets cut.

---

## PHASE 10 — Stretch goals (only if Phases 0–9 are complete)
**Owner: whoever is free**

Gated deliberately. Neither of these should be started while any part of the core path is
unfinished.

1. **APK static analysis** (Androguard) — package name, risky permissions (SMS, accessibility,
   overlay), signing certificate, embedded URLs; link victims whose APKs share a signing
   certificate into one campaign as a `SHARED_APK_CERT` link.
2. **Local LLM brief narrative** (Ollama, small model, fully offline) — strictly
   template-plus-citation, grounded only in extracted facts, clearly labelled as
   machine-generated, and always shown beside the deterministic version. If it cannot be made
   verifiably grounded, ship without it.
3. Ed25519 detached signature on the report.
4. PyInstaller one-folder build so the officer does not need Python.
5. Cross-case correlation — **design only, not built.** It needs an explicit legal basis.

---

## Timeline summary

| Phase | Hours | Owner | Cumulative |
|---|---|---|---|
| 0 Setup & contracts | 3 | All | 3 |
| 1 Mock data | 5 | A | 8 |
| 2 Integrity | 4 | C | 8 (parallel) |
| 3 Ingestion | 10 | A | 18 |
| 4 Correlation & graph | 8 | B | 18 (parallel) |
| 5 Risk scoring | 7 | C | 18 (parallel) |
| 6 Brief generation | 6 | D | 24 🏁 **end-to-end path closes** |
| 7 UI screens | 12 | D + B | 36 |
| 8 Testing & benchmarks | 6 | C + all | 42 |
| 9 Deliverables | 8 | D + all | 50 |
| 10 Stretch | — | — | only if ahead |

Phases 2–5 run in parallel against the Phase 0 stubs, which is the entire reason Phase 0 exists.

---

## Definition of done (v1)

- [ ] Folder drop → PDF brief in under 5 minutes, under 5 clicks, with no terminal use
- [ ] Every fact in the brief traces to a file, a row and a SHA-256
- [ ] Tampering with any evidence file is detected and named
- [ ] The audit chain verifies from genesis and reports any break by sequence number
- [ ] The planted ring is recovered completely; the decoys produce zero false links
- [ ] Every risk score carries at least one quotable, evidence-backed reason
- [ ] The full pipeline runs with networking disabled, graph screen included
- [ ] Benchmark ≥ 20,000 rows/sec, peak RAM < 2 GB
- [ ] `pytest` green; accuracy table generated from a real run
- [ ] Proposal, PoC repository and a rehearsed 3-minute video are complete

---

## Day-one warnings

1. **Vendor `vis-network` locally before anything else in Phase 7.** The default PyVis template
   fetches it from a CDN, and the graph renders blank on an air-gapped machine.
2. **Never let a date format be inferred.** `03/04/2026` parsed as April 3rd instead of March 4th
   silently destroys the timeline and every time-window rule that depends on it.
3. **Enforce the `entity_a_id < entity_b_id` ordering on symmetric links from the first commit.**
   Retrofitting it after the graph exists means recomputing every centrality score.
4. **Do not skip Phase 0.** Four people writing against four different implicit schemas is the
   normal way a four-person hackathon team fails.
5. **Reach the Phase 6 milestone before building any UI.** A complete crude pipeline beats a
   beautiful incomplete one on every criterion in this rubric.
6. **Verify the electronic-evidence certificate wording against a primary legal source.** Do not
   reproduce statutory text from memory, from the slide deck, or from these documents.
