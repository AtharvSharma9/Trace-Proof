# 1. Product Requirements Document (PRD)

**Project:** PRAMAAN
**Version:** 1.0 (MVP / hackathon screening round)
**Owner:** Team of 4

---

## 1. App overview

### App name
**PRAMAAN** — *Provenance-anchored Risk Analysis of Mule Account Networks*

### One-line app idea
An offline forensic triage workstation that ingests fragmented cyber-fraud evidence, links the
entities hiding inside it, ranks suspect accounts with plain-language reasons, and produces a
one-page investigative brief in which **every single claim is traceable to a source file, a row
number and a SHA-256 hash**.

### The positioning in one sentence
Other tools tell an investigating officer *what* is suspicious. PRAMAAN also proves *why*, and
proves the evidence behind the *why* has not been altered since it was seized.

---

## 2. Target users

### Primary user — Investigating Officer (IO), cyber cell
Sub-inspector to inspector rank. Handles 10–40 financial fraud complaints a day. Comfortable
with Excel, not with Python or Cypher. Works on a standard Windows workstation, often without
internet access. Under acute time pressure during the "golden hour" after a complaint is filed,
because funds move out of reach within minutes.

**What they need:** to know which account to freeze first, and to be able to justify that
decision in writing.

### Secondary user — Cyber Forensics Analyst / Technical Support Unit
Prepares evidence for court. Cares about hash preservation, non-modification of originals, and
whether the report will survive a challenge under the Bharatiya Sakshya Adhiniyam.

**What they need:** an unbroken, verifiable chain of custody and an audit log.

### Tertiary user — Supervisory Officer (DSP / SP, Cyber)
Reviews and signs off. Needs a one-page summary, not a dashboard.

**What they need:** a printable brief with prioritised seizure recommendations.

---

## 3. Problem statement

Law enforcement agencies receive a high volume of financial cyber fraud complaints daily — mule
account operations, APK-based phishing, call spoofing and UPI fraud. Investigating officers
currently triage evidence manually across artifacts that do not share a format or a schema:

- **CDRs** (Call Detail Records) — CSV/Excel, and the column names differ by telecom operator
- **IPDRs** (IP Detail Records) — CSV, large, often hundreds of thousands of rows
- **Bank and UPI settlement sheets** — Excel, and the column names differ by bank
- **Email headers** — `.eml` files, where spoofing evidence hides in `Received` chains
- **Android system and app dumps** — `.txt` / `.json`, semi-structured
- **APK metadata** — package names, permissions, signing certificates

Four concrete failures follow from this:

| Failure | Consequence |
|---|---|
| Manual cross-referencing across 5+ file formats | Hours lost during the golden hour; funds are gone |
| Shared identifiers (IMEI, IMSI, UPI handle, IP subnet, MAC) are missed by eye | Whole arms of a fraud ring go undetected |
| Risk judgements live in the officer's head | Cannot be defended in court or transferred to another officer |
| Evidence gets opened, re-saved and edited in Excel | Integrity is compromised; admissibility is challenged |

**The gap PRAMAAN closes:** there is no lightweight, offline pipeline that does automated
correlation *and* preserves forensic integrity. Existing commercial forensic suites are
expensive, heavy, and rarely deployed below the state cyber-cell level.

---

## 4. Core features

### F1 — Multi-source ingestion and normalisation
Drop a folder of mixed evidence. The system detects each file's type by content rather than by
extension, fuzzy-matches unknown column headers to a canonical schema ("Calling No", "A-Party"
and "MSISDN" all resolve to `caller`), shows the officer a confidence score per mapping for
confirmation, and normalises everything into a single Entity/Event model.

### F2 — Evidence integrity layer (always-on, not a feature toggle)
Every file is SHA-256 hashed at the moment of ingestion and recorded in a manifest. Originals
are opened read-only and never written back. Every analytic action is written to a hash-chained
audit log where each entry embeds the hash of the previous entry, so a deleted or edited entry
breaks the chain visibly. A one-click **Verify Integrity** re-hashes all evidence and flags any
change.

### F3 — Entity correlation engine
Extracts and resolves entities — phone numbers, IMEI, IMSI, UPI handles, bank accounts, IFSC
codes, IP addresses, MAC addresses, emails, APK signing certificates — and links them on shared
attributes: one IMEI seen with three different SIMs, a beneficiary UPI handle recurring across
unrelated complaints, endpoints sharing an IP /24 subnet, APKs sharing a signing certificate.
Each link carries a confidence value and a human-readable rationale.

### F4 — Mule network graph visualiser
A directional graph mapping victim → intermediary mule nodes → cash-out point. Nodes sized by
risk, edges by transferred amount. Supports fan-in, fan-out, layering (3+ hops in minutes),
cycle and pass-through pattern highlighting. Betweenness and PageRank centrality surface the
coordinating node, which is rarely the node holding the most money.

### F5 — Explainable risk scoring
A transparent weighted-rule engine produces a 0–100 score per endpoint. An Isolation Forest
refines the *ranking* only, and can be disabled. Every score expands into plain-language reason
codes an officer can paste into a report — for example, *"forwarded 96% of credited funds within
11 minutes across 3 hops"* — and every reason links back to the exact evidence rows that
triggered it.

### F6 — Investigative brief generation
A one-page PDF (and matching JSON) containing: case header, timeline of the fraud, ranked prime
suspects with reasons, linked phone/account clusters, the network graph image, immediate seizure
recommendations, and an appendix listing every source file with its SHA-256 and the audit-chain
head hash.

### F7 — Case and audit management
Cases are created, listed and reopened. Each case is one portable file. The audit log is
browsable and exportable.

---

## 5. User roles

| Role | Can do | Cannot do |
|---|---|---|
| **Investigating Officer (IO)** | Create cases, ingest evidence, confirm column mappings, run correlation, adjust risk thresholds within a permitted band, generate briefs | Delete evidence, edit the audit log, alter a generated brief |
| **Forensic Analyst** | Everything an IO can do, plus verify integrity, export the audit log, view raw parse diagnostics and rejected rows | Delete evidence or edit the audit log |
| **Supervisor** | Open any case on the workstation read-only, view briefs, export briefs | Ingest, modify or score |

Deletion is not a permission held by anyone. Evidence can only be marked `EXCLUDED` with a
mandatory reason, and that exclusion is itself an audit entry.

---

## 6. User stories

**Ingestion**
- As an IO, I want to drop a folder of mixed evidence files and have the system tell me what it
  found, so that I do not have to open each file in Excel.
- As an IO, I want to see and correct how the system mapped an unfamiliar bank's column headers,
  so that a wrong guess does not silently corrupt my analysis.
- As an IO, I want files that fail to parse to be listed with a reason rather than skipped
  silently, so that I know what is missing from my picture.

**Integrity**
- As a Forensic Analyst, I want every input file hashed on arrival and that hash printed in the
  final report, so that the defence cannot claim the evidence was altered.
- As a Forensic Analyst, I want to press one button and be told whether any evidence file has
  changed since ingestion, so that I can certify integrity before filing.
- As a Supervisor, I want to see who ran which analysis and when, so that accountability is
  clear.

**Correlation and graph**
- As an IO, I want the system to tell me that these four phone numbers ran on the same handset,
  so that I can connect complaints I would otherwise have filed separately.
- As an IO, I want to see the money move from the victim to the final withdrawal on one screen,
  so that I know where to send a freeze request first.
- As an IO, I want to click any node and see the evidence rows behind it, so that I trust what I
  am looking at.

**Risk**
- As an IO, I want a ranked list of accounts to act on, so that I spend the golden hour on the
  right target.
- As an IO, I want each score to come with a sentence I can quote in my report, so that I do not
  have to explain a black box to a magistrate.
- As a Forensic Analyst, I want to turn the ML component off and see the pure rule score, so
  that I can defend the methodology.

**Output**
- As an IO, I want a one-page PDF with seizure recommendations, so that I can hand it to my
  supervisor immediately.
- As an IO, I want a JSON version of the same brief, so that it can be fed into an existing case
  management system later.

---

## 7. Success metrics

### Product metrics (measured on synthetic benchmark data)
| Metric | Target |
|---|---|
| Time from folder drop to generated brief | < 5 minutes for a 5-file, 100k-row case |
| Ingestion throughput | ≥ 20,000 rows/second on a 4-core laptop CPU |
| Column auto-mapping accuracy on unseen operator/bank layouts | ≥ 90% correct without officer correction |
| Entity extraction recall on the planted ring | ≥ 95% |
| **False link rate** (incorrect entity merges) | **< 2%** — the most important accuracy metric |
| Planted mule chain fully recovered end to end | 100% on the benchmark dataset |
| Peak RAM | < 2 GB |
| Internet calls made at runtime | 0 |

### Hackathon metrics
| Criterion (weight) | How we intend to win it |
|---|---|
| Technical feasibility & scalability (30%) | A measured rows/second number shown on screen in the demo video |
| Forensic accuracy & integrity (25%) | Live tamper-detection demo; documented false-link rate |
| Usability for field officers (25%) | Folder-drop to brief in under five clicks; no terminal use |
| Innovation & practicality (20%) | Provenance-linked reason codes; runs fully offline |

---

## 8. MVP scope (version 1)

**In scope:**
- Local officer login with attribution
- Case create / open / list
- Ingestion of CSV, XLSX, `.eml`, `.txt`, `.json` with content-based type detection
- Fuzzy header mapping with a confirmation screen and per-mapping confidence
- SHA-256 manifest and hash-chained audit log
- Entity extraction for phone, IMEI, IMSI, UPI handle, bank account, IFSC, IP, MAC, email
- Correlation rules: shared IMEI, shared IMSI, shared device, shared IP /24, recurring
  beneficiary, fund-flow edges
- Interactive network graph with risk-coloured nodes and highlighted victim → mule → cash-out path
- 12 weighted risk rules plus optional Isolation Forest re-ranking
- Reason codes with evidence drill-down
- One-page PDF and JSON brief with hash appendix
- One-click integrity verification
- Synthetic data generator producing one planted fraud ring

**Explicitly out of scope for version 1** (listed so the AI agent does not build them):
- Multi-user, networked or cloud deployment
- Real telecom or bank API integrations
- Live bank freeze request submission (NCRP / CFCFRMS integration)
- APK static analysis via Androguard — *deferred, Phase 10 stretch only*
- Local LLM narrative generation — *deferred, Phase 10 stretch only*
- Chat export (WhatsApp/Telegram) parsing
- Geospatial tower-location mapping
- OCR of scanned bank statements
- Face/voice biometrics
- Role-based UI hiding (roles are recorded and enforced on actions, but not used to hide screens)
- Mobile app
- Any form of automated action against a suspect account

---

## 9. Features to avoid in version 1 (and why)

| Tempting feature | Why it is a trap here |
|---|---|
| A generative LLM writing the investigative brief | A hallucinated sentence in a forensic document is worse than no document. If added later, it must be strictly template-plus-citations, grounded only in extracted facts. |
| A heavyweight graph database server (Neo4j) | Needs a running server; disqualifies the offline/low-resource claim. Use NetworkX in memory, serialise to SQLite. |
| Deep-learning fraud classification | Unexplainable, needs training data we do not have, and directly conflicts with the 25% accuracy-and-integrity criterion. |
| Aggressive fuzzy name matching on account holder names | Generates false links, which is the single most penalised failure mode. |
| A beautiful but dense analytics dashboard | The user is a field officer under time pressure, not an analyst. Ranked list beats chart grid. |
| Supporting every possible file format | Three formats parsed perfectly beats nine parsed badly. Add formats as YAML plugins after the core path works. |

---

## 10. Non-functional requirements

- **Offline:** zero network calls at runtime; must pass a test run with networking disabled.
- **Portable:** runs from a folder on a standard Windows 10/11 police workstation, 8 GB RAM, no
  admin rights required.
- **Non-destructive:** source evidence files are opened read-only; a working copy is stored
  inside the case folder.
- **Deterministic:** the same inputs and the same thresholds produce the same scores. Random
  seeds are fixed and recorded in the report.
- **Auditable:** no analytic result exists without a corresponding audit entry.
- **Legible:** the generated brief must be readable when printed in black and white.
