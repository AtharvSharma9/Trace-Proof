# Trace-Proof — Project Documentation Set

**PRAMAAN** — *Provenance-anchored Risk Analysis of Mule Account Networks*

Submission for: **AI-Powered Unified Cyber Fraud Analysis \& Digital Artifact Correlator**
Team size: 4 · Round: Screening

\---

## What this folder is

Six documents that give an AI coding agent (Cursor, Claude Code, Bolt, Lovable, Replit) enough
context to build this app without guessing. Read them in order.

|#|File|Answers|
|-|-|-|
|1|`01\_PRD.md`|What we are building and for whom|
|2|`02\_TRD.md`|How it is built technically|
|3|`03\_App\_Flow.md`|Every screen, action and state|
|4|`04\_UI\_UX\_Brief.md`|How it looks and feels|
|5|`05\_Backend\_Schema.md`|How data is stored and connected|
|6|`06\_Implementation\_Plan.md`|The exact build order|

\---

## Assumptions made (stated, not hidden)

These were not specified in the problem statement. They were chosen deliberately and are
carried consistently through all six documents. Change them here first if you disagree, then
re-run the affected docs.

1. **Fully offline desktop app.** No cloud, no internet at runtime. A police workstation may be
air-gapped. This directly serves the "offline capability or low-resource overhead" clause in
the Innovation criterion.
2. **One case = one SQLite file.** Portable, seizable, hashable, attachable to a case diary.
3. **Local officer login, not a cloud identity provider.** Chain of custody requires knowing
*which officer* did *what*, so authentication exists for attribution, not for access control
against the internet.
4. **Rules are the primary risk score; ML is a secondary refinement that can be switched off.**
The Forensic Accuracy criterion (25%) explicitly penalises false links. An unexplainable
score is a liability in court.
5. **Nothing appears in the final brief without a source file, row number and SHA-256.** This is
the product's core promise and the single idea that unifies Idea 04 and Idea 05.
6. **Mock/synthetic data only.** No real CDR, IPDR or bank data is used at any point. One
planted fraud ring is generated for the demo.
7. **Tech stack is Python-only** so that all four team members work in one language under
hackathon time pressure.

\---

## How to use these with your AI coding tool

Load all six files into the tool's context, then send this prompt **before** asking for any code:

> Read all the documents carefully. Do not start coding yet. First summarize what you
> understood, identify missing details, and create a build plan. After that, we will build the
> app phase by phase.

Then build phase by phase using `06\_Implementation\_Plan.md`. Do not ask for the whole app in one
shot.

\---

## Mapping to the screening deliverables

|Required deliverable|Source|
|-|-|
|Technical Proposal (2–3 pages)|`02\_TRD.md` §2, §3, §7 + `05\_Backend\_Schema.md` §1|
|PoC / code prototype|Phases 0–4 of `06\_Implementation\_Plan.md`|
|Demo video (max 3 min)|Phase 9 storyboard in `06\_Implementation\_Plan.md`|



