# 4. UI/UX Design Brief

**Project:** PRAMAAN
**Version:** 1.0
**Purpose:** clear enough that an AI app builder can produce the interface without inventing its
own visual language.

---

## 1. Design style

### The one-line direction
**A forensic instrument, not a fintech dashboard.** Calm, dense, high-contrast, evidential.
Everything on screen should look like it could be printed and attached to a case file.

### Design principles, in priority order

1. **Evidence over ornament.** No decorative gradients, no glassmorphism, no animated
   backgrounds, no hero illustrations. Every pixel either carries information or creates the
   whitespace that makes information legible.
2. **Numbers are the interface.** Hashes, row counts, scores, timestamps and rows-per-second are
   the content. Typography must serve them.
3. **Traceability is visible.** A source hash or row reference is never hidden behind two
   clicks. Provenance appears as a persistent, quiet caption under any derived fact.
4. **Certainty is signalled honestly.** Confidence percentages, "estimated", "approximate" and
   "not verified" are shown, not smoothed away. A tool that looks more certain than it is will
   not survive court.
5. **Calm under pressure.** The user may be working the golden hour on a real fraud. No
   attention-grabbing motion, no red unless something is genuinely wrong, no more than one
   primary action per screen.
6. **Prints in black and white.** Colour may reinforce meaning but never carries it alone. Every
   risk band has a text label next to its colour.

### Explicitly avoid
Consumer SaaS styling; rounded pill buttons everywhere; purple-to-pink gradients; emoji as
status icons; dark "hacker" theme with neon green; cards floating on cream backgrounds;
decorative accent stripes down the side of cards or under headings; full-width coloured header
bars; drop shadows used as decoration rather than elevation; illustration mascots.

---

## 2. Colour palette

Light interface. A police workstation is often a bright room with a cheap monitor, and outputs
get printed.

### Core
| Token | Hex | Use |
|---|---|---|
| `--ink` | `#0F172A` | Primary text, headings |
| `--ink-muted` | `#475569` | Secondary text, captions, labels |
| `--ink-faint` | `#94A3B8` | Placeholders, disabled text, provenance captions |
| `--surface` | `#FFFFFF` | Page and card background |
| `--surface-alt` | `#F8FAFC` | Sidebar, table header rows, code blocks |
| `--surface-sunken` | `#F1F5F9` | Drop zones, inactive panels |
| `--border` | `#E2E8F0` | Hairlines, table rules, card borders |
| `--border-strong` | `#CBD5E1` | Input borders, focused dividers |

### Brand and action
| Token | Hex | Use |
|---|---|---|
| `--primary` | `#1B3A5C` | Primary buttons, active nav, headings in the brief |
| `--primary-hover` | `#16304C` | Hover state |
| `--primary-soft` | `#E8EEF4` | Active nav background, selected rows |
| `--accent-verified` | `#0E7C86` | Integrity verified, hashes confirmed, the "Offline" pill |
| `--accent-verified-soft` | `#E0F2F3` | Verified panel background |

Deep navy and teal, not blue-purple. It reads institutional and it does not collide with the
risk scale.

### Risk scale (also the semantic scale)
| Band | Score | Fill | Text on light | Always paired with the word |
|---|---|---|---|---|
| Low | 0–29 | `#15803D` | `#14532D` | "Low" |
| Medium | 30–59 | `#B45309` | `#78350F` | "Medium" |
| High | 60–79 | `#C2410C` | `#7C2D12` | "High" |
| Critical | 80–100 | `#B91C1C` | `#7F1D1D` | "Critical" |

Soft backgrounds for band chips: `#DCFCE7`, `#FEF3C7`, `#FFEDD5`, `#FEE2E2`.

### Status
| State | Colour | Where |
|---|---|---|
| Success / verified | `#15803D` on `#DCFCE7` | Ingest complete, integrity intact |
| Warning / stale | `#B45309` on `#FEF3C7` | Not verified recently, low-confidence mapping, ML disabled |
| Error / tamper | `#B91C1C` on `#FEE2E2` | Parse failure, hash mismatch, broken chain |
| Info | `#1B3A5C` on `#E8EEF4` | Neutral guidance |

### Graph node colours
Nodes use the risk scale. Reserve two extra roles: **Victim** `#1B3A5C` with a ring, and
**Cash-out point** `#7F1D1D` with a double ring. These two must be identifiable at a glance in a
still frame of the demo video.

### Rules
- Body text contrast ≥ 7:1; all other text ≥ 4.5:1 (WCAG AA minimum, AAA for body).
- Never red text on a dark background or light grey text on `--surface-alt`.
- Red appears **only** for genuine failure. Not for emphasis, not for branding.

---

## 3. Typography

| Role | Font | Fallback stack | Size / weight |
|---|---|---|---|
| UI sans | **Inter** | `Inter, "Segoe UI", system-ui, Roboto, Arial, sans-serif` | see scale |
| Mono | **JetBrains Mono** | `"JetBrains Mono", "Cascadia Mono", Consolas, "Courier New", monospace` | hashes, IDs, numbers |
| Brief PDF serif | **Source Serif 4** (headings only) | `"Source Serif 4", Georgia, serif` | printed document gravitas |

**Bundle the font files locally.** Google Fonts will not load on an air-gapped workstation. Ship
`.woff2` in `assets/fonts/` and declare `@font-face`. Always give the full fallback stack.

### Type scale
| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `display` | 30 / 38 | 600 | Screen titles |
| `h1` | 24 / 32 | 600 | Section headings |
| `h2` | 19 / 28 | 600 | Card titles |
| `h3` | 16 / 24 | 600 | Sub-headings, table group labels |
| `body` | 15 / 24 | 400 | Default text |
| `body-sm` | 13.5 / 20 | 400 | Table cells, dense lists |
| `caption` | 12 / 16 | 400, `--ink-muted` | Provenance lines, hints, timestamps |
| `label` | 12 / 16 | 600, uppercase, 0.06em tracking | Field labels, table headers |
| `mono` | 13 / 20 | 400 | Hashes, IMEI, account numbers, IP |
| `metric` | 34 / 40 | 700, tabular figures | Dashboard tile numbers, risk scores |

### Numeric rules
- Use `font-variant-numeric: tabular-nums` on every column of figures so digits align vertically.
  In a table of amounts and scores this is the difference between scannable and unreadable.
- Identifiers — hashes, IMEI, IMSI, account numbers, UPI handles, IP, MAC — are **always
  monospace**, never sans. This is a semantic rule, not a stylistic one: it tells the user
  "this is a literal value you may need to copy exactly."
- Truncate long hashes to the first 12 characters with an ellipsis, full value on hover, click to
  copy.
- Indian number formatting for currency: `₹4,80,000` (lakh grouping), not `₹480,000`.
- Timestamps: `21 Sep 2026, 14:32:07 IST`. Never a bare `2026-09-21T14:32:07Z` in the UI; always
  ISO-8601 in the JSON export.

---

## 4. Component style

### Buttons
Rectangular with a 6px radius. Never fully rounded pills. Height 38px standard, 44px primary.

| Variant | Style |
|---|---|
| Primary | `--primary` fill, white text, 600 weight. **One per screen.** |
| Secondary | White fill, `--border-strong` 1px border, `--ink` text |
| Ghost | No fill, no border, `--primary` text; for tertiary actions in toolbars |
| Danger | White fill, `#B91C1C` border and text; fills red only on hover. Destructive actions must require a deliberate second look. |
| Disabled | `--surface-sunken` fill, `--ink-faint` text, `not-allowed` cursor, tooltip explaining the prerequisite |

Loading state: the label is replaced by a spinner plus a stage word ("Hashing…", "Parsing…",
"Scoring…"), width held constant so the layout does not jump.

### Cards
White, 1px `--border`, 6px radius, 20px padding, 16px gap between cards. Elevation only for
overlays and drawers (`0 4px 12px rgba(15,23,42,0.08)`). **No accent stripe on any edge.** To
distinguish a card, use a `--surface-alt` header row or an icon.

### Tables
The workhorse component; most screens are a table.

- Header: `--surface-alt`, `label` type, sticky on scroll.
- Rows: 40px, 1px `--border` bottom rule, no zebra striping (zebra fights the risk colours).
- Hover: `--surface-alt`.
- Selected: `--primary-soft` with a 3px `--primary` left marker (this is the one permitted left
  marker, because it indicates selection rather than decoration).
- Numeric and monospace columns right-aligned; text left-aligned.
- Sortable headers show a chevron on hover.
- Over 200 rows: paginate, do not infinite-scroll. Officers reference "row 147" out loud.
- Every table has a row count caption above it.

### Risk chips
Pill, 4px radius, soft background, dark band text, bold score, band word alongside:
`[ 87  Critical ]`. Score and word always together, everywhere in the app.

### Hash display
Monospace on `--surface-alt`, 4px radius, 2px 6px padding, `--accent-verified` text when
verified, `#B91C1C` when mismatched, with a copy icon on hover.

### Provenance caption
The signature component of this product. Beneath any derived fact:

> `bank_statement_HDFC.xlsx · row 1,482 · sha256 a4f1c9d2e8b3…`

`caption` size, `--ink-muted`, monospace for the filename and hash, clickable to open the row.
It must appear on every reason code, every graph edge drawer and every brief line item.

### Forms
Labels above inputs, never placeholder-as-label. 38px inputs, 1px `--border-strong`, 6px radius,
2px `--primary` focus ring. Validation messages inline below the field in `#B91C1C`, 13px.
Required fields marked with an asterisk and listed in the button's disabled tooltip.

### Banners and inline alerts
Full content width, 4px radius, 1px border in the status colour, soft background, 16px padding,
an icon on the left, a bold one-line headline, an optional second line, and an action link on
the right. Used for ingest results, integrity status and degradation warnings.

### Drawers
Right-side, 420px wide, for node and edge detail. Overlay dims to `rgba(15,23,42,0.35)`. Closes
on Escape.

### Progress
Determinate bar for ingestion, showing the current filename and an `n of m` counter.
Indeterminate spinner with a stage label everywhere else. Never a bare spinner with no text.

### Icons
Lucide or Phosphor, 20px, 1.5px stroke, `--ink-muted` by default and `--primary` when active.
Vendor them locally. Never emoji.

---

## 5. Layout rules

### Shell
```
┌────────────┬──────────────────────────────────────────────────┐
│  SIDEBAR   │  CONTENT                                         │
│  240px     │  max-width 1360px, centred, 32px side padding    │
│  fixed     │                                                  │
│  --surface │  ┌ Screen title + subtitle ──── primary action ┐ │
│  -alt      │  ├ Status banner (conditional) ────────────────┤ │
│            │  ├ Content: tiles / table / graph canvas ──────┤ │
│            │  └ Footer note (conditional) ──────────────────┘ │
├────────────┤                                                  │
│ Offline    │                                                  │
│ pill       │                                                  │
└────────────┴──────────────────────────────────────────────────┘
```

**Sidebar contents, top to bottom:** app name; active case number and title; officer name, badge
and rank; an integrity status pill; the pipeline-ordered navigation list; a footer with the
offline pill and the version.

### Spacing
An 8px base scale: 4, 8, 12, 16, 24, 32, 48. Section gap 32px, card gap 16px, card padding 20px,
label-to-field 6px. Never invent a 13px or 27px gap.

### Grid
12-column, 16px gutters. Dashboard tiles occupy 3 columns each on desktop. Tables and the graph
canvas span all 12.

### Density
Deliberately denser than consumer SaaS. The officer is comparing many rows, not reading an
article. Table rows 40px, body 15px, generous horizontal padding but tight vertical rhythm.

### Graph canvas
Minimum 620px tall, full content width, 1px `--border`, `--surface` background. Controls in a
240px left panel inside the canvas frame. The legend is always visible in the top-right corner —
it must survive being screenshotted into the brief and the demo video.

---

## 6. Mobile and desktop behaviour

**Design target: desktop, 1366×768 minimum.** That is a standard government workstation
resolution and the app must be fully usable at it without horizontal scrolling.

| Breakpoint | Behaviour |
|---|---|
| ≥ 1600px | Full shell; dashboard tiles 4 across; graph canvas 720px tall |
| 1280–1599px | Full shell; tiles 4 across; graph 620px; tables scroll horizontally within their container, never the page |
| 1024–1279px | Sidebar collapses to 64px icon rail with tooltips; tiles 2 across |
| < 1024px (tablet) | Sidebar becomes a drawer behind a menu button; tiles stack 2 across; graph gets a "best viewed on a larger screen" note but still renders |
| < 768px (phone) | **Read-only support only.** Case list, risk board and brief viewing work in a single stacked column. Ingestion, mapping confirmation and the graph are not supported and show a clear message rather than a broken layout. |

Mobile is explicitly not a v1 goal. Do not spend hackathon time on it. It is specified here only
so the agent degrades gracefully instead of producing an unusable mess.

**Print stylesheet is required** (the brief will be printed): hide the sidebar and all controls,
force `--surface` white, black text, page-break-avoid inside cards and table rows, and print
full hashes rather than truncated ones.

---

## 7. Dashboard design direction

The Case Dashboard is the screen judges see first. It must communicate *state of the
investigation* in under three seconds.

**Order down the page:**
1. **Case header** — number, title, FIR, created by, created on. Plain, two lines.
2. **Integrity banner** — full width, immediately below the header. It is placed above the
   metrics deliberately: in a forensic tool, whether the evidence is trustworthy outranks what
   the evidence says.
3. **Four metric tiles** — Evidence (files · rows), Entities, Links, Top risk. Each shows a
   `metric`-size number, a `label`-size caption, and a small delta or context line. The Top risk
   tile carries its band colour as a chip, not as a filled card.
4. **Pipeline strip** — six steps, horizontal, each a small square with a tick, a spinner, a dash
   or a cross, and a label beneath. Completed steps in `--accent-verified`, running in
   `--primary`, pending in `--ink-faint`, failed in the error colour. This single row tells a
   judge exactly what the system does, which is a quiet but real usability win.
5. **Primary next action** — one large button, label driven by the current state.
6. **Recent activity** — the last five audit entries, compact, with officer and timestamp.

**Keep off the dashboard:** pie charts of file types, generic "total processed" vanity counters,
sparklines with no baseline, and any chart that does not change a decision. Usability is 25% of
the score and it is judged on clarity, not on chart count.

---

## 8. Button and card style summary

| Element | Radius | Border | Fill | Shadow |
|---|---|---|---|---|
| Primary button | 6px | none | `--primary` | none |
| Secondary button | 6px | 1px `--border-strong` | white | none |
| Danger button | 6px | 1px `#B91C1C` | white (red on hover) | none |
| Card | 6px | 1px `--border` | white | none |
| Drawer / modal | 8px | none | white | `0 4px 12px rgba(15,23,42,0.08)` |
| Risk chip | 4px | none | band-soft | none |
| Hash chip | 4px | none | `--surface-alt` | none |
| Input | 6px | 1px `--border-strong` | white | none |

Consistent 6px is the house radius. Deviating per component is the fastest way to make an
interface look assembled from templates.

---

## 9. Overall user experience

### The experience in one sentence
An officer with a folder of messy files and forty minutes should reach a defensible, printable
conclusion without opening a terminal, a spreadsheet or a manual.

### Interaction rules
- **Five clicks, folder to brief.** Count them in review; if the count rises, redesign.
- **One primary action per screen.** If two things look equally important, neither is.
- **Progressive disclosure.** The Risk Board shows three reasons; Entity Detail shows all of
  them; the expander shows the raw rows. Depth is available, never imposed.
- **Never lose work.** Every stage writes to the case file. Closing the app mid-analysis loses
  nothing.
- **Explain before acting.** Any control that changes a result — a confidence slider, the ML
  toggle — carries a one-line caption saying what changing it does and what it risks.
- **Speak the user's language.** "Mule account", "cash-out point", "layering", "beneficiary",
  "IMEI", "FIR". Not "node", "vertex", "anomaly score z-value". Graph vocabulary stays inside
  tooltips for the analyst.
- **Show the cost of automation.** Confidence percentages on every auto-mapping and every link.
  The officer must always be able to see where the machine guessed.

### Accessibility
Keyboard navigable end to end; visible 2px focus rings; every icon button has an `aria-label`;
status is conveyed by icon plus text plus colour, never colour alone; minimum 14px for any text
the officer must read repeatedly; a respect for `prefers-reduced-motion` — and in any case no
animation longer than 150ms anywhere in the app.

### Tone of voice
Plain, factual, unhurried. No exclamation marks. No "Oops!" No congratulation.

| Instead of | Write |
|---|---|
| "Oops! Something went wrong 😕" | "Could not parse 3 of 5 files. See details below." |
| "Awesome! Analysis complete!" | "Scored 412 endpoints. 6 Critical, 14 High." |
| "We think this account is risky" | "Score 87 (Critical). Forwarded 96% of credited funds within 11 minutes." |
| "No data" | "No evidence ingested yet. Ingest a folder to begin." |

---

## 10. Visual references and inspiration

Directional references, to be interpreted rather than copied:

- **Bloomberg Terminal / Refinitiv Eikon** — information density, tabular discipline, the
  principle that numbers are the interface. Take the density, leave the dark theme.
- **Maltego** — entity-link graph conventions: shape by entity type, thickness by weight,
  drill-down into the underlying record. The closest existing analogue to our graph screen.
- **Autopsy / Sleuth Kit** — forensic tooling conventions: an evidence register, hash columns,
  a visible audit trail. Take the conventions, improve the visual clarity considerably.
- **Stripe Dashboard** — form and table craft, restrained palette, excellent empty and error
  states. Take the craft, leave the consumer warmth.
- **GOV.UK Design System** — plain language, accessibility, the idea that a public-service tool
  should be boring and unambiguous. This is the closest match to our tone.
- **Indian government forms and FIR layouts** — for the printed brief only: formal header block,
  numbered sections, a signature and certificate area at the foot.

**Anti-references:** crypto trading dashboards, "AI-powered" marketing landing pages, dark
cyber-security dashboards with glowing globes and world maps. A rotating globe with attack arcs
is the single fastest way to signal that a tool is a demo rather than an instrument.

---

## 11. The brief document design (printed output)

The one-page PDF is a separate design surface and arguably the most scrutinised artifact.

- **A4 portrait**, 20mm margins.
- **Header block:** state/police emblem placeholder, "INVESTIGATIVE BRIEF — CONFIDENTIAL", case
  number, FIR number, police station, generating officer with badge, generation timestamp.
- **Section 1 — Summary:** three or four sentences, template-generated, stating the amount
  defrauded, the number of hops and the time elapsed.
- **Section 2 — Timeline:** a compact horizontal strip with 6–10 labelled events.
- **Section 3 — Prime suspects:** a table of rank, identifier, type, score, band, top reason.
- **Section 4 — Network graph:** a static rendered image, minimum 300 DPI, with a legend.
- **Section 5 — Seizure recommendations:** numbered, imperative, each naming the account, the
  bank, the amount and the urgency.
- **Section 6 — Evidence appendix:** every source file with its full SHA-256 in monospace.
- **Footer on every page:** case number, page `n of m`, the audit-chain head hash, and the
  report's own SHA-256.
- **Certificate section:** the electronic-evidence certificate block. *Confirm the exact required
  wording and the current statutory reference against a primary legal source before use.*

Serif headings, sans body, monospace hashes. Black and white legible throughout — assume it will
be photocopied.
