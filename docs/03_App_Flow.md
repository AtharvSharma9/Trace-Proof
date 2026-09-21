# 3. App Flow Document

**Project:** PRAMAAN
**Version:** 1.0
**Purpose:** every screen, action, navigation path, success state, error state and empty state,
detailed enough for an AI coding agent to build without guessing.

---

## 1. Screen inventory

| ID | Screen | Route / key | Auth required |
|---|---|---|---|
| S00 | First-Run Setup | `?view=setup` | No (only when no officer exists) |
| S01 | Login | `?view=login` | No |
| S02 | Case List | `?view=cases` | Yes |
| S03 | New Case | `?view=case_new` | Yes |
| S04 | Case Dashboard | `?view=dashboard&case=<id>` | Yes |
| S05 | Ingest — Drop & Detect | `?view=ingest&case=<id>` | Yes |
| S06 | Ingest — Confirm Mapping | `?view=mapping&case=<id>&file=<id>` | Yes |
| S07 | Evidence Register | `?view=evidence&case=<id>` | Yes |
| S08 | Entities & Links | `?view=entities&case=<id>` | Yes |
| S09 | Network Graph | `?view=graph&case=<id>` | Yes |
| S10 | Risk Board | `?view=risk&case=<id>` | Yes |
| S11 | Entity Detail (drill-down) | `?view=entity&case=<id>&eid=<id>` | Yes |
| S12 | Timeline | `?view=timeline&case=<id>` | Yes |
| S13 | Integrity Verify | `?view=integrity&case=<id>` | Yes |
| S14 | Audit Log | `?view=audit&case=<id>` | Yes |
| S15 | Brief Builder & Export | `?view=brief&case=<id>` | Yes + re-auth |
| S16 | Settings & Thresholds | `?view=settings` | Yes |
| S17 | Mock Data Generator (dev/demo) | `?view=mockgen` | Yes |

Navigation shell: a persistent left sidebar visible on S04–S16, showing case number, officer
name and badge, an integrity status pill, and the section links. S00, S01 and S03 render
full-screen with no sidebar.

---

## 2. Primary user journey (the happy path, and the demo path)

```
Login
  → Case List → [+ New Case] → New Case form → Case Dashboard (empty state)
  → Ingest: drop folder → detection table → Confirm Mapping (per file) → Ingest complete
  → Case Dashboard (populated) → Run Correlation
  → Entities & Links → Network Graph
  → Run Risk Scoring → Risk Board → click top suspect → Entity Detail → click a reason
      → evidence rows with file hash
  → Integrity Verify (all green)
  → Brief Builder → re-auth → Generate → PDF + JSON in exports/
```

**Golden-hour target: under five minutes and under five decisions.**

---

## 3. Screen-by-screen specification

### S00 — First-Run Setup
**Shown when:** the credential store contains zero officers.

**Elements:** app name and tagline; fields for Full name, Badge number, Rank, Unit/Cyber cell,
Password, Confirm password; a checkbox "This is the supervisor account"; a **Create Account**
button.

**Validation:** badge number is required and unique; password minimum 10 characters; passwords
must match.

**Success:** account created with `role = SUPERVISOR` if the checkbox is ticked, otherwise
`ANALYST`; audit genesis entry written to the app-level store; redirect to S02 already logged in;
toast *"Account created. You are signed in."*

**Error states:** duplicate badge → inline *"Badge number already registered on this
workstation."*; weak password → inline *"Use at least 10 characters."*; DB not writable → full
screen block *"Cannot write to the data folder. Run PRAMAAN from a location you have write
access to."*

---

### S01 — Login
**Elements:** Badge number, Password, **Sign In**, and a footer line showing app version and
*"Offline · No data leaves this workstation."*

**Actions:**
- *Sign In* → validate against argon2 hash → create session row → set token in
  `st.session_state` → audit `LOGIN_SUCCESS` → navigate to S02.

**Error states:**
- Wrong credentials → *"Badge number or password is incorrect."* Do **not** reveal which one was
  wrong. Increment the failure counter; audit `LOGIN_FAILURE`.
- 5 failures → *"Locked for 15 minutes after 5 failed attempts."* Disable the button and show a
  countdown.
- Expired session redirect → banner *"Your session expired. Sign in again."*

**Empty state:** not applicable — S00 handles the zero-officer case.

---

### S02 — Case List
**Elements:** header *"Cases"*; a **+ New Case** primary button; a search box filtering by case
number, FIR number or title; a status filter (Open / Under review / Closed); a table with
columns Case number, Title, FIR, Created, Evidence files, Top risk, Integrity, Last opened.

**Row actions:** click anywhere → S04. An **Open folder** icon action reveals the case folder in
the OS file manager.

**Integrity column:** green *Verified* / amber *Not verified since last ingest* / red
*Tamper detected*.

**Empty state:** centred card, *"No cases yet."* subtext *"Create a case to start triaging
evidence."* and two buttons: **+ New Case** and **Generate sample case** (which runs the mock
generator and creates a fully populated demo case — this is the fastest path to a rehearsal and
should be built early).

**Error state:** a case file is present but unreadable/corrupt → the row renders greyed with a
red *Cannot open* badge and a tooltip carrying the exception; it must not crash the list.

---

### S03 — New Case
**Elements:** Case number (auto-suggested as `CASE_<YYYY>_<NNNN>`, editable), Case title, FIR
number (optional), Police station, Complaint date, Short description, and **Create Case** /
**Cancel**.

**Success:** creates the case folder and SQLite file, writes the audit genesis entry, audits
`CASE_CREATED`, navigates to S04 in its empty state.

**Errors:** duplicate case number → *"A case with this number already exists on this
workstation."*; folder creation failure → *"Could not create the case folder. Check disk space
and permissions."*

---

### S04 — Case Dashboard
The landing screen for an open case and the anchor for navigation.

**Elements:**
- Case header: number, title, FIR, created-by, created-on.
- Four status tiles: **Evidence** (n files, n rows), **Entities** (n), **Links** (n),
  **Top risk** (score and band).
- A pipeline progress strip with six steps — Ingest, Hash, Correlate, Graph, Score, Brief — each
  Pending / Running / Done / Failed.
- A primary action button whose label changes with state: *Ingest Evidence* → *Run Correlation*
  → *Run Risk Scoring* → *Generate Brief*.
- An integrity banner: green *"All 5 evidence files verified 4 minutes ago"* with a
  **Re-verify** link; amber if stale; red if any hash mismatches.
- A recent-activity list showing the last 5 audit entries.

**Empty state (no evidence yet):** tiles show zeros; the pipeline strip is all Pending; a
centred prompt *"No evidence ingested yet"* with **Ingest Evidence** and a secondary
**Generate sample data for this case**.

**Error state:** if the last pipeline run failed, an inline red card names the step, the reason
and offers **Retry** and **View details**.

---

### S05 — Ingest: Drop & Detect
**Elements:** a large drop zone — *"Drop files or a folder here"* — plus a **Browse** button and
a "Use a folder path" text input for large folders that the browser cannot upload.

**On drop, for each file, in order:**
1. Copy into `case/evidence/` and set read-only.
2. Compute SHA-256 (progress bar for files over 50 MB).
3. Sniff type by content, not extension.
4. Read headers and propose a column mapping with a confidence score.
5. Append an audit entry `EVIDENCE_INGESTED`.

**Detection table columns:** Filename · Size · SHA-256 (first 12 chars, monospace, click to
copy) · Detected type (CDR / IPDR / Bank statement / UPI settlement / Email · eml / Android dump
/ Unknown) · Mapping confidence (High ≥ 90% / Medium 70–89% / Low < 70%) · Status · Action.

**Row actions:** **Confirm mapping** → S06. **Change type** → a dropdown to override detection,
which reopens mapping. **Exclude** → requires a typed reason, audited as `EVIDENCE_EXCLUDED`;
the file is never deleted.

**Rules:**
- Files with **High** confidence are auto-confirmable in bulk via **Confirm all high-confidence**.
- Files with **Medium** or **Low** confidence **must** be opened in S06 before ingestion
  completes. The system must not silently guess on a low-confidence mapping — a wrong guess
  corrupts the analysis and that is precisely what the accuracy criterion punishes.

**Success state:** a green summary bar, *"5 files ingested · 128,430 rows · 0 rejected · 18,900
rows/sec"* with **Go to Correlation**. Show the rows/second figure — it is scored.

**Error states:**
- Unknown type → row marked *Unknown*, with **Map manually** and **Exclude**.
- Parse failure → row marked red with the reason and a **View rejected rows** link opening a
  sample of failing rows with line numbers.
- Duplicate file (identical SHA-256 already in the case) → *"Already ingested as <filename>.
  Skipped."* Not an error; audited as `EVIDENCE_DUPLICATE_SKIPPED`.
- Encrypted or password-protected file → *"File is protected and cannot be read. Supply a
  decrypted copy."*
- Zero-byte file → *"File is empty."*
- File larger than the configured limit → *"File exceeds the 2 GB ingest limit. Split it and
  retry."*

**Empty state:** the drop zone itself, with a line listing the supported formats and a
**Download sample evidence pack** link.

---

### S06 — Ingest: Confirm Mapping
**Purpose:** the officer approves how unknown columns were interpreted. This is the human
checkpoint that keeps the 30%-scalability automation honest against the 25%-accuracy criterion.

**Elements:**
- File header with name, detected type and SHA-256.
- A mapping table: Source column · Sample values (3 rows) · Mapped to (dropdown of canonical
  fields) · Confidence bar · Match reason (e.g. *"'A-PARTY NO' ≈ 'a-party' · 94%"*).
- Unmapped source columns collapsed under *"n columns ignored"*, expandable and individually
  mappable.
- A detected datetime format line with a sample parse and a **Change format** dropdown.
- A preview of the first 10 normalised rows.
- Buttons: **Confirm & Ingest**, **Save as reusable format** (writes a YAML plugin so the next
  file from this bank or operator maps automatically), **Back**.

**Validation:** required canonical fields per type must be mapped — a CDR needs at least
`caller`, `callee`, `start_time`; a bank sheet needs at least `debit_account`,
`credit_account`, `amount`, `txn_time`. The Confirm button stays disabled until they are, with
an inline list of what is missing.

**Success:** audit `MAPPING_CONFIRMED` with the mapping JSON; rows parsed; return to S05 with the
row marked green.

**Error states:** datetime parse failure on preview → amber inline *"3 of 10 sample rows failed
to parse as a date. Choose a different format."*; two source columns mapped to the same canonical
field → *"'MSISDN' and 'A-PARTY' are both mapped to caller. Pick one."*

---

### S07 — Evidence Register
A read-only, printable table of the case's evidence: Filename · Type · Size · Rows parsed · Rows
rejected · SHA-256 (full, monospace) · Ingested by · Ingested at · Status (Active / Excluded) ·
Verify status.

**Actions:** **Verify all now** (→ S13 results), **Export register as CSV**, **Copy hash**.

**Empty state:** *"No evidence in this case yet."* with **Ingest Evidence**.

---

### S08 — Entities & Links
**Elements:**
- Tab 1 **Entities**: filter chips by type (Phone · IMEI · IMSI · UPI · Account · IP · MAC ·
  Email · Device); a table of Value · Type · Occurrences · First seen · Last seen · Linked
  entities · Risk; a search box. Clicking a row → S11.
- Tab 2 **Links**: table of Entity A · Entity B · Link type · Confidence · Rationale ·
  Supporting rows. Link types: `SHARED_IMEI`, `SHARED_IMSI`, `SHARED_DEVICE`, `SHARED_IP_SUBNET`,
  `RECURRING_BENEFICIARY`, `SHARED_MAC`, `FUND_FLOW`, `SHARED_APK_CERT`.
- A confidence threshold slider (default 0.75) that filters displayed links live, with a caption
  *"Lowering this shows weaker links and increases the risk of false connections."*
- A **Dismiss link** action requiring a reason, audited as `LINK_DISMISSED`. Dismissed links are
  excluded from the graph and the score but retained in the record.

**Success state after correlation:** a green bar, *"Found 412 entities and 87 links across 5
files"*, with **View Graph**.

**Empty state:** *"Correlation has not been run yet."* with **Run Correlation**.

**Error state:** correlation failure → the failing stage is named, with **Retry** and a link to
technical details.

---

### S09 — Network Graph
**Elements:**
- The interactive PyVis canvas, filling the content area.
- Nodes coloured by risk band, sized by degree; shape by entity type (circle = phone,
  square = account, diamond = UPI handle, triangle = device/IMEI).
- Directed edges; thickness proportional to amount; labels showing amount and time delta.
- A left control panel: entity-type toggles; a link-confidence slider; a layout selector
  (force-directed / hierarchical); **Highlight victim → cash-out path**; **Show only the top-N
  risk subgraph** (default N = 50, to keep large cases legible).
- A legend, always visible.
- Buttons: **Fit to screen**, **Export PNG**, **Export GraphML**.

**Interactions:**
- Hover a node → tooltip with value, type, risk score and top reason.
- Click a node → right drawer with a summary and **Open full detail** (→ S11).
- Click an edge → drawer listing the underlying transactions with source file and row.
- Double-click a node → isolate its 2-hop neighbourhood; **Reset view** restores.

**Success state:** the victim → mule → cash-out chain is drawn with a highlighted path and a
caption naming the number of hops and the elapsed time, e.g. *"Victim → 3 mules → ATM cash-out ·
₹4,80,000 · 11 minutes"*. This is the demo's centrepiece frame.

**Empty state:** *"No graph yet. Run correlation first."* with a **Run Correlation** button.

**Error / degraded states:**
- Over 5,000 nodes → banner *"Large graph. Showing the top 500 nodes by risk. Adjust in
  controls."* Never attempt to render everything and freeze the UI.
- Graph component fails to load its local assets → red inline card *"Graph renderer assets not
  found. Check assets/vendor."* plus a static Matplotlib fallback image so the screen is never
  blank. **This fallback is mandatory — it is the demo's insurance policy.**

---

### S10 — Risk Board
The screen the IO actually acts on.

**Elements:**
- Ranked cards, highest score first. Each card: rank, entity value, entity type, a 0–100 score
  with its band colour, a band label (Low / Medium / High / Critical), the top three reason
  codes in plain language, and quick actions **View detail** and **Add to brief**.
- A header strip: score distribution histogram; an **Include anomaly model** toggle (on by
  default) with the caption *"Off = rules only. The rule score is fully explainable."*; a
  **Recompute** button.
- Filters by band, by entity type, and a checkbox *"Only entities appearing in the victim →
  cash-out path"*.
- A **Seizure recommendations** panel listing accounts sorted by *funds still likely
  recoverable*, each with the recommended action and a **Copy** button for pasting into a freeze
  request.

**Reason codes displayed as complete sentences**, for example:
- *"Forwarded 96% of credited funds within 11 minutes (R01 Rapid pass-through)"*
- *"Received funds from 14 distinct accounts in 40 minutes (R02 Fan-in)"*
- *"One handset (IMEI 35•••••••••1234) used with 4 different SIMs (R05 SIM-switch velocity)"*
- *"Account opened 6 days before receiving ₹12.4 lakh (R07 New account, high volume)"*
- *"Sits on 78% of all victim-to-cash-out paths (R12 Centrality)"*
- *"Sender domain fails SPF and From does not match Return-Path (R09 Spoofed header)"*

**Success state:** *"Scored 412 endpoints · 6 Critical · 14 High"* with **Generate Brief**.

**Empty state:** *"Risk scoring has not been run."* with **Run Risk Scoring**.

**Error states:** anomaly model fails to fit (too few samples) → amber banner *"Anomaly model
needs at least 30 endpoints. Showing rule-based scores only."* and the pipeline continues. The
rule score must always work alone; the ML must never be a hard dependency.

---

### S11 — Entity Detail
**Elements:**
- Header: entity value, type, risk score with band, and **Add to brief**.
- **Why this score** — every contributing reason listed with its rule code, its weight
  contribution in points, the plain-language sentence, and an expander showing the exact
  supporting evidence rows with source filename, row number and file SHA-256.
- **Linked entities** — table with link type, confidence and rationale.
- **Timeline** — the entity's events in chronological order: calls, transfers, logins, sessions.
- **Appearances** — which evidence files this entity was found in, with row counts.
- **Officer notes** — a free-text field saved to the case and audited as `NOTE_ADDED`.

This screen is the product's proof. Every number on it opens into the raw row that produced it.

**Empty state:** an entity with no links → *"No correlated links found for this entity."*

**Error state:** provenance missing for a fact — this should be structurally impossible; if it
occurs, render a red *Provenance missing* badge and log a `PROVENANCE_ERROR` audit entry rather
than hiding it.

---

### S12 — Timeline
A horizontal, zoomable chronological view of the whole case: complaint filed, first contact
call, APK install, victim debit, each mule hop, cash-out. Filterable by entity and event type.
**Export PNG** for inclusion in the brief.

**Empty state:** *"No events parsed yet."*

---

### S13 — Integrity Verify
The screen that wins the integrity criterion, and the most memorable 20 seconds of the demo.

**Elements:**
- A single large **Verify Now** button.
- **Evidence integrity** table: filename, hash at ingestion, hash now, status (✓ Unchanged /
  ✗ **Changed** / ⚠ Missing).
- **Audit chain** panel: total entries, chain status (✓ Intact / ✗ Broken at entry #n), genesis
  hash, current head hash.
- Last-verified timestamp and verifying officer.
- **Export verification certificate (PDF)**.

**Success state:** a full-width green panel — *"Integrity verified. 5 of 5 evidence files
unchanged. Audit chain intact across 218 entries."* with the head hash in monospace.

**Failure state:** a full-width red panel — *"TAMPER DETECTED. 1 file has changed since
ingestion."* The offending file is listed with both hashes shown for comparison, the case is
flagged `INTEGRITY_COMPROMISED`, brief generation is blocked until the officer either restores
the file or records an acknowledgement with a reason, and the event is audited as
`INTEGRITY_FAILURE`.

**Empty state:** *"No evidence to verify yet."*

---

### S14 — Audit Log
A chronological, filterable, read-only table: Seq · Timestamp · Officer (name + badge) · Action ·
Target · Entry hash (first 12 chars) · Previous hash (first 12 chars). Filters by officer, action
type and date range. **Export as CSV/JSON**. A **Verify chain** button reruns validation and
highlights any broken row in red.

There is no edit or delete control anywhere on this screen, by design.

**Empty state:** cannot occur — every case has a genesis entry.

---

### S15 — Brief Builder & Export
**Gate:** password re-authentication is required before generating. Generating a brief is a
formal act and must be attributable.

**Elements:**
- A live preview of the one-page brief.
- Section toggles: Case header · Timeline · Prime suspects (top N, default 5) · Linked clusters ·
  Network graph image · Seizure recommendations · Evidence hash appendix (**locked on, cannot be
  disabled**) · Certificate section.
- An editable Officer's Remarks box.
- **Generate PDF**, **Generate JSON**, **Generate both**.

**Pre-generation checks, all blocking:**
1. Integrity verified within the last 24 hours — otherwise *"Verify integrity before generating
   a brief."* with a **Verify now** link.
2. At least one suspect selected.
3. No unresolved low-confidence mappings.

**Success state:** *"Brief generated."* with the file path, its own SHA-256, a **Open folder**
button and **Print**. Audited as `BRIEF_GENERATED` including the report hash.

**Error states:** PDF write failure (file open in another program) → *"Could not write the PDF.
Close the file if it is open and retry."*; graph image missing → generate with a placeholder and
warn, rather than failing the whole export.

---

### S16 — Settings & Thresholds
Three tabs.
- **Risk weights** — a table of the 12 rules with editable weights and thresholds, a **Reset to
  defaults** button, and a note that changes are audited as `THRESHOLDS_CHANGED` and recorded in
  the next brief. Officers may adjust within a permitted band; the supervisor role can change
  anything.
- **Correlation** — link confidence thresholds per link type; IP subnet mask size (default /24);
  the time window for "rapid pass-through" (default 60 minutes).
- **Workstation** — data folder path, performance mode (streaming / in-memory), an **Offline
  check** button that confirms no outbound connections, and app/version/licence information.

---

### S17 — Mock Data Generator (demo and testing)
**Elements:** number of victims, number of mules, layering depth, time compression, noise-record
volume, a random seed, and **Generate**.

**Output:** writes synthetic CDR CSV, IPDR CSV, bank statement XLSX, UPI settlement XLSX and
`.eml` files into a chosen folder, containing exactly one planted, fully traceable fraud ring
plus realistic decoy noise. It also prints the ground truth so accuracy can be measured.

**Success:** *"Generated 5 files, 128,430 rows, 1 planted ring (seed 42)."* with **Ingest into
this case**.

This screen exists because every other screen depends on having believable input. It is built
first.

---

## 4. Navigation rules

- Sidebar order matches the pipeline: Dashboard → Ingest → Evidence → Entities → Graph → Risk →
  Timeline → Integrity → Audit → Brief. Order is meaning: it teaches the officer the workflow.
- Sidebar items for stages not yet reachable are visible but disabled, with a tooltip explaining
  the prerequisite. Never hide them — hidden navigation makes users think the feature is absent.
- The primary action button on S04 always points at the next incomplete stage.
- Breadcrumbs appear on drill-down screens: `Risk Board › 9876543210`.
- Browser back maps to the previous view via query parameters, so state survives a refresh.
- The active case is held in `st.session_state` and echoed in the sidebar header at all times,
  because opening the wrong case is a serious error in this domain.

---

## 5. Global button behaviour

| Button | Behaviour |
|---|---|
| Any long-running action | Disables immediately, shows a spinner with a stage label, streams progress, and cannot be double-fired |
| Any destructive-looking action (Exclude, Dismiss link, Reset thresholds) | Requires a typed reason and a confirmation; writes an audit entry |
| Generate Brief | Requires re-authentication |
| Copy hash | Copies the full hash, shows a *Copied* toast |
| Export | Writes into `case/exports/`, then offers a download and an **Open folder** action |

---

## 6. Global state definitions

**Loading:** skeleton rows for tables, a determinate progress bar with the current filename for
ingestion, an indeterminate spinner with a stage label elsewhere. Any operation expected to take
over 2 seconds must show which stage it is in — silence reads as a hang.

**Empty:** an icon, one sentence naming what is absent, one sentence saying what to do, and one
primary button that does it. Never an empty table with bare headers.

**Success:** a green inline bar at the top of the content area, stating what happened in numbers,
with a button pointing at the next stage. Toasts for minor confirmations only.

**Error:** a red inline card stating what failed, why, and what the officer can do, plus
**Retry** and a collapsible technical detail block for the analyst. Never a raw traceback in the
main flow and never a silent failure — a silently skipped file is a missed suspect.

**Offline indicator:** a persistent sidebar footer pill, *"Offline · 0 network calls"*. It is
reassurance for the user and a visible claim for the judges.

---

## 7. Login and session flow

```
App start
  └─ officers table empty? ── yes ──► S00 First-Run Setup ──► S02
                             └─ no ──► valid session token in state?
                                          ├─ yes ──► S02 Case List
                                          └─ no  ──► S01 Login
Session expiry (8h, sliding)
  └─ any action ──► token invalid ──► S01 with banner "Your session expired."
Sign out
  └─ audit LOGOUT ──► clear session row and state ──► S01
```

---

## 8. Payment / upgrade flow

**Not applicable.** PRAMAAN is a law-enforcement tool with no commercial tier, no billing and no
account upgrade path. This section is deliberately empty so that an AI coding agent does not
invent a pricing page.

---

## 9. Error-handling policy

| Class | Policy |
|---|---|
| Recoverable (one file fails to parse) | Continue the batch, mark that row, surface the count in the summary |
| Blocking (case DB unwritable) | Full-screen block with a clear instruction; do not proceed |
| Integrity (hash mismatch) | Never soft-fail. Flag loudly, block brief generation, audit |
| Analytical (model will not fit) | Degrade to the rule engine, warn, continue |
| Unexpected exception | Catch at the view boundary, show a friendly card, write the traceback to `app.log`, keep the app alive |

The governing principle: **the system may be wrong, but it must never be quietly wrong.** In a
forensic tool, an invisible failure is worse than a visible one.
