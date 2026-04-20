# UI Design: CFD Harness Workbench

Authored 2026-04-20 as companion to `docs/product_thesis.md` and
DEC-V61-002. Covers information architecture, visual design language,
the six-screen MVP, component library, and tech-stack rationale.

## Design principles

Four principles govern every screen. When a design decision is
ambiguous, resolve toward the principle listed earliest.

**1. Show the provenance, always.** Every numeric quantity on screen
is accompanied by its tolerance band, its reference citation, and its
commit SHA lineage. Bare numbers are a bug. This is the product's
reason to exist.

**2. Red means "fail the audit," not "broke the software."**
Color is bound to physics-contract outcomes, not to system health.
A `FAIL` case is red because it violates a gold-standard, not
because a microservice crashed. System-health status lives in a
single header strip, visually distinct (neutral iconography).

**3. The human audits; the agent drafts.** Agent-authored content is
always visually flagged (left border accent, subtle background tint).
Human-authored overrides look different. An audit-package reader must
be able to tell at a glance which lines were machine-suggested.

**4. Never lose the decision trail.** Every state-changing action
writes a decision record. Delete is archival, not destructive (hard
floor #3 extends to the UI: no UI action permanently removes data).
Every screen shows an "Audit" affordance that expands the decision
history for the current entity.

## Visual design language

**Dark-first**. CFD engineers spend their days in ParaView,
OpenFOAM logs, and terminal sessions. A dark canvas matches the
environment; light mode is a secondary option. Default:
`bg-[hsl(220,15%,10%)]` (near-black, slightly warm), `text-
[hsl(220,10%,92%)]` (near-white, slightly cool).

**Three-state color semantics** for physics-contract outcomes:

| State | Color | Hex (dark) | Meaning |
|---|---|---|---|
| PASS | Green | `#4ade80` (emerald-400) | Measurement within tolerance; contract preconditions all satisfied |
| COMPATIBLE_WITH_SILENT_PASS_HAZARD | Amber | `#fbbf24` (amber-400) | Measurement within tolerance but a known silent-pass hazard is armed; requires `audit_concern` review |
| FAIL | Red | `#f87171` (red-400) | Measurement outside tolerance OR contract precondition unmet |

**Typography**:

- **UI sans** — Inter for headings, body, and labels. Clean, geometric,
  renders well on dense forms.
- **Monospace** — JetBrains Mono for `case_id`, commit SHA, tolerance
  values, physics quantities (`Re`, `Ra`, `Nu`). Any value that
  appears in audit packaging verbatim.
- **Math serif** — STIX Two Math for rendered equations
  (MathJax / KaTeX output). Avoid emoji for technical content.

**Spacing**: 8px base grid. Tight forms (8/12/16 stack), generous
section spacing (32/48). Never less than 8px between clickable
elements (Fitts's law on touch + dense-grid pointer work).

**Iconography**: Lucide (agreed open-source set, pairs with shadcn/
ui). No custom iconography in MVP; each icon has an accompanying
text label (accessibility + audit legibility).

**Motion**: deliberately understated. Transitions 120-180ms, ease-
out. No bouncy springs. This is a compliance product; motion signals
"something changed," not personality.

## Information architecture

Five top-level concepts form the mental model:

```
PROJECTS
  └── CASES (instances of whitelist.yaml entries scoped to a project)
        └── RUNS (individual solver invocations)
              └── MEASUREMENTS (extracted quantities per key_quantity)
                    └── AUDIT PACKAGE (signed export bundle)

DECISIONS (cross-cutting — attaches to any of the above)
```

Top-level navigation (left rail, persistent):

```
 ┌─────────────┐
 │  Projects   │  — the project picker + dashboard
 │  Cases      │  — whitelist-governed case definitions
 │  Runs       │  — solver run history, live status
 │  Decisions  │  — ADWM + external-gate queue
 │  Audits     │  — export history + verification
 │             │
 │  (settings) │  — user / project settings
 │  (help)     │  — skill-index.yaml browser
 └─────────────┘
```

Content area shows one of the six screens below. Right rail is
context-aware: in Cases view it shows contract preconditions;
in Runs view it shows live residual plot; in Decisions view it
shows the affected-entities list.

## The six screens (MVP)

### Screen 1: Project Dashboard

**Purpose**: one-glance project health. First screen on login.

**Layout** (12-column grid):

```
 ┌─────────────────────────────────────────────────────────────────┐
 │ HEADER: project name · last-sync · current v-number              │
 ├──────────────────────────────┬──────────────────────────────────┤
 │                              │                                  │
 │  10-CASE CONTRACT MATRIX     │   PENDING GATE DECISIONS         │
 │  (8 cols)                    │   (4 cols)                       │
 │                              │                                  │
 │  case_id × mesh×param grid   │   Q-1 DHC gold (P-1/P-2)         │
 │  each cell: pass/hazard/fail │   Q-2 R-A-relabel                │
 │  hover → mini audit_concern  │   DEC-V61-002 follow-up          │
 │  click → Case detail         │                                  │
 │                              │   ┌──────────────────────────┐   │
 │                              │   │ DECISIONS THIS WEEK       │   │
 │                              │   │ (timeline)                │   │
 │                              │   └──────────────────────────┘   │
 ├──────────────────────────────┴──────────────────────────────────┤
 │ FOOTER: 10/10 cases · 3 HAZARD · 1 FAIL · 0 STALE (>30d)         │
 └─────────────────────────────────────────────────────────────────┘
```

**Key UX patterns**:

- **Contract matrix cells** are the product's hero: each shows a
  compressed summary (measured value · ref value · tolerance ±%)
  that scales with cell size. At large size, shows a tiny inline
  chart (gold-band + measured point). At small size, shows only
  the color chip.
- **Pending gate decisions** panel is Linear-style: cards sortable
  by severity, each card links to the decision-queue entry.
- **Decisions-this-week timeline** is a horizontal strip of decision
  icons with hover cards; click navigates to Decisions queue filtered
  by that decision.

### Screen 2: Case Editor

**Purpose**: author and lint a whitelist case against its gold-standard
schema. This is where the AI agent's proposed edits are reviewed.

**Layout** (three-column, full-height):

```
 ┌─── SCHEMA TREE ─┬──── YAML EDITOR ──────┬──── CONTRACT PANEL ───┐
 │ (240px)         │ (flex)                │ (380px)               │
 │                 │                       │                       │
 │ whitelist.yaml  │ Monaco editor         │ Physics preconditions │
 │ ├ id            │  schema validation    │ ├ mesh resolves BL:❌  │
 │ ├ name          │  live lint markers    │ ├ regime matches:  ✅ │
 │ ├ parameters    │  auto-complete from   │ ├ extractor aligned:✅│
 │ │  ├ Re         │   gold_standards/     │                       │
 │ │  └ …          │                       │ Gold-standard bind    │
 │ ├ gold_standard │ [agent-suggested      │ ref: Dhir 2001        │
 │ │  ├ quantity   │  lines tinted]        │ ref_value: 30.0       │
 │ │  ├ tolerance  │                       │ tolerance: ±15%       │
 │ │  └ references │                       │                       │
 │ │               │                       │ Last review: 2026-04- │
 │ │               │                       │ 18 (DEC-ADWM-004)     │
 └─────────────────┴───────────────────────┴───────────────────────┘
 │ SAVE · DRAFT · DIFF-FROM-MAIN · RUN-PRECHECK · VIEW-AGENT-DIFF  │
 └─────────────────────────────────────────────────────────────────┘
```

**Key UX patterns**:

- Schema tree is **schema-driven not text-driven**: clicking `parameters
  .Re` jumps to that line and highlights. Adding a subkey requires
  explicit menu action (no free-form additions that would invalidate
  schema).
- YAML editor is Monaco with a custom language server wrapping
  `monaco-yaml` + a server-side endpoint that cross-validates against
  the matching `gold_standards/{case_id}.yaml` on every keystroke.
- **Contract panel** is the product's secret sauce. It reads
  `physics_contract.preconditions[]` and evaluates each against the
  in-editor case in real time. If a precondition's
  `satisfied_by_current_adapter` becomes false, the panel flashes
  amber before the run is even attempted.
- **Agent-suggested lines** are marked with a left-border accent
  (`#7c3aed` violet); a `VIEW-AGENT-DIFF` button shows the before/
  after with a `Rationale` expander fed from the agent's decision
  record.

### Screen 3: Run Monitor

**Purpose**: watch a solver run live; intervene if needed.

**Layout** (split top/bottom):

```
 ┌───────────────────────────────────────────────────────────────┐
 │ HEADER: case_id · run_id · solver · wall-clock · checkpoint   │
 ├───────────────────────────────────────────────────────────────┤
 │                                                               │
 │                                                               │
 │              3D VTK.JS VIEWPORT                               │
 │              (mesh · field · probe lines)                     │
 │              [play/pause  time-slider  field-selector]        │
 │                                                               │
 │                                                               │
 ├─────────────────────────────┬─────────────────────────────────┤
 │   RESIDUAL PLOT             │  RUN CONTROLS                   │
 │   (WebSocket stream)        │  ┌─ CHECKPOINT ─┐               │
 │   continuity · Ux · Uy      │  ┌─ STOP ───────┐               │
 │   energy (if applicable)    │  ┌─ RESUME ─────┐               │
 │   k · omega                 │                                 │
 │   log-y axis by default     │  PROGRESS:                      │
 │                             │  step 4200 / 10000 (42%)        │
 │                             │  ETA: 38 min                    │
 │                             │                                 │
 │                             │  CURRENT audit_concern: (none)  │
 └─────────────────────────────┴─────────────────────────────────┘
```

**Key UX patterns**:

- 3D viewport is deferred to Phase 3; Phase 0..2 ship a residual-plot-
  only variant with a placeholder "3D preview coming in Phase 3"
  panel.
- Residual stream uses WebSocket for backpressure-aware delivery
  (Python async yields residual rows as OpenFOAM writes them).
- **Checkpoint** and **Resume** are physical buttons — running CFD
  is expensive; users need confidence they can pause and come back.
  Checkpoint writes `.run_state/` + uploads it to the run's audit
  package artifact list.

### Screen 4: Validation Report (**Phase 0 target**)

**Purpose**: show one run's result next to its gold-standard. This is
the screen that ships in Phase 0 as concept-of-proof.

**Layout** (single column, reading-optimized, max-width 960px):

```
 ┌─────────────────────────────────────────────────────────────┐
 │ CASE HEADER                                                 │
 │ differential_heated_cavity · B1 256² mesh                   │
 │ Ra = 1e10 · Pr = 0.71 · k-ω SST                             │
 │ run 2026-04-18T21:45 · commit 60952b6                       │
 ├─────────────────────────────────────────────────────────────┤
 │ [PASS / HAZARD / FAIL chip — large, colored]                │
 │ nusselt_number · measured vs gold                           │
 │ ┌─────────────────────────────────────────────────────────┐ │
 │ │                                                         │ │
 │ │      tolerance band (gray rectangle)                    │ │
 │ │      ref_value=30.0 (horizontal gold line)              │ │
 │ │      measured=77.82 (red dot above band)                │ │
 │ │                                                         │ │
 │ └─────────────────────────────────────────────────────────┘ │
 │ Deviation: +159%                                            │
 │ Tolerance: ±15% → within-band cutoff: [25.5, 34.5]          │
 ├─────────────────────────────────────────────────────────────┤
 │ AUDIT CONCERNS                                              │
 │ • COMPATIBLE_WITH_SILENT_PASS_HAZARD                         │
 │   BL under-resolution (precondition #1: false)              │
 │   → mesh < 500-1000 cells wall-normal required              │
 │ • DEVIATION                                                 │
 │   Measurement Nu=77.82 closer to literature Ra=1e10 than    │
 │   gold ref_value=30.0                                       │
 │   → See DEC-ADWM-004 (external-gate Q-1 escalation)         │
 ├─────────────────────────────────────────────────────────────┤
 │ PRECONDITIONS                                               │
 │ ├ mesh resolves δ/L thermal BL     ❌ (256² insufficient)   │
 │ ├ regime matches gold              ✅ (2D DHC, Ra=1e10)     │
 │ └ extractor methodology aligned    ✅ (mean-over-y post-60952b6) │
 ├─────────────────────────────────────────────────────────────┤
 │ DECISIONS TRAIL                                             │
 │ → DEC-ADWM-002 (2026-04-18) cycle 1 self-APPROVE            │
 │ → DEC-ADWM-004 (2026-04-18) FUSE + Q-1 escalation            │
 │ [link to full decision records]                             │
 ├─────────────────────────────────────────────────────────────┤
 │ [EXPORT AUDIT PACKAGE (Phase 5)]  [OPEN IN RUN MONITOR]     │
 └─────────────────────────────────────────────────────────────┘
```

**Key UX patterns**:

- The band chart is the centerpiece. Rendered with Plotly (or SVG
  directly in Phase 0 to avoid Plotly bundle size). Tolerance band is
  the visual grammar; any reader understands "the dot is inside/outside
  the box."
- Audit concerns are **typed**, not free-form strings. Each concern's
  type has a canonical human-readable name + resolution link.
- Preconditions ✅/❌ markers are machine-derived from the in-yaml
  `satisfied_by_current_adapter` flags.
- Decisions trail is chronological; clicking navigates to the decision
  record detail.

### Screen 5: Decisions Queue

**Purpose**: Kanban-style board of all decisions (ADWM self-APPROVE,
external-gate, FUSE, etc.) with their current status.

**Layout** (four-column Kanban):

```
 ┌──────────────────────────────────────────────────────────┐
 │ FILTER · STATUS: All · SCOPE: All · CREATED: 30d · SORT  │
 ├─────────┬─────────────┬────────────────┬─────────────────┤
 │ DRAFT   │ PROPOSED    │ ACCEPTED       │ CLOSED          │
 ├─────────┼─────────────┼────────────────┼─────────────────┤
 │         │ DEC-V61-002 │ DEC-ADWM-001..6 │ DEC-ADWM-001... │
 │         │ [card]      │ DEC-V61-001    │ DEC-ADWM-002… │
 │         │             │                │                 │
 │         │             │                │                 │
 └─────────┴─────────────┴────────────────┴─────────────────┘
```

**Card** layout:

```
  ┌── DEC-V61-002 ──────────────────── [Accepted] ──┐
  │ Elect Path B · declare 6-phase MVP roadmap      │
  │ autonomous · reversibility: fully-reversible    │
  │ scope: Project · 2026-04-20                     │
  │                                                 │
  │ Affects: ui/ · docs/ · planning state           │
  │ Notion: [linked]  GitHub: [PR #2]                │
  └─────────────────────────────────────────────────┘
```

**Key UX patterns**:

- Kanban columns mirror the Notion Decisions DB `Status` select.
  Drag-and-drop status change is gated: only certain transitions
  allowed (Draft → Proposed → Accepted; Accepted → Closed or
  Superseded). Invalid drops show a tooltip explaining why.
- Each card shows `autonomous_governance` boolean as a subtle
  bot-face icon; human-authored decisions show a person icon.
  Audit reviewers rely on this distinction.
- Filter bar includes a special filter "external-gate queue only"
  that surfaces only items in `external_gate_queue.md`.

### Screen 6: Audit Package Builder (**commercial gate**)

**Purpose**: produce a signed, byte-reproducible evidence bundle for
external submission. **This is the billable unit** of the product.

**Layout** (wizard-style, 4 steps):

```
 ┌─────────────────────────────────────────────────────────────┐
 │ STEP 1/4: SCOPE                                             │
 │   ○ Single run        ● Multi-run validation campaign       │
 │   ○ Whole-project audit                                     │
 │                                                             │
 │   Included runs:                                            │
 │   ☑ dhc_b1_256_20260418 (PASS-with-hazard)                   │
 │   ☑ dhc_b0_80_20260415 (FAIL)                                │
 │   ☐ dhc_b2_512_20260420 (PASS)  [excluded: not signed off]   │
 │                                                             │
 │   [NEXT]                                                    │
 └─────────────────────────────────────────────────────────────┘
```

Steps are: **1. Scope** (select runs), **2. Include** (pick artifacts:
case, gold, run, residuals, decisions, related ADWM history),
**3. Reviewer metadata** (submitter name, reviewer persona, regulatory
framework — FDA V&V40 / DO-178C / NQA-1 / ASME V&V40 generic),
**4. Sign and export** (HMAC over the canonicalized bundle + PDF
rendering + zip).

**Key UX patterns**:

- **Byte-reproducible**: same inputs produce same bytes. Timestamps
  are canonicalized to UTC; file order is deterministic (sorted);
  no embedded random UUIDs.
- **Signed**: HMAC-SHA256 over the canonical bundle; key is per-
  project. Verification procedure is published in
  `ui/backend/audit_package/VERIFY.md` and can be reproduced with a
  5-line bash script. This is the anti-tampering story.
- **Reviewer-framework-aware**: the PDF template adapts to the
  selected framework (e.g. V&V40 template includes Context-of-Use
  and Credibility Goals; DO-178C template includes DAL assignment).
  Framework templates are in `ui/backend/audit_package/templates/`.
- **Explicit exclusion rationale**: runs excluded from the bundle
  require a stated reason (dropdown: "not yet signed off" / "known
  divergent / superseded" / "other"); the rationale is recorded in
  the bundle itself (transparency over convenience).

## Component library

**shadcn/ui** primitives (Radix-based, unstyled → Tailwind). Selected
over MUI / Ant Design because:

- **Copy-not-install** philosophy: components are vendored into
  `ui/frontend/src/components/ui/`, can be forked per-component
  without fighting a library update cycle. Important for long-lived
  regulated-industry products where "wait for vendor patch" is not
  an option.
- **Radix accessibility** by default (keyboard nav, screen-reader
  semantics, focus management). Regulated markets have accessibility
  requirements (Section 508, EN 301 549).
- **Tailwind idiom** matches our stylistic direction (utility-first,
  dark-mode native).

Specific shadcn components used in Phase 0..5: `button`, `card`,
`dialog`, `dropdown-menu`, `input`, `label`, `sheet`, `tabs`,
`toast`, `tooltip`, `badge`, `separator`, `scroll-area`, `table`,
`skeleton`, `alert`.

Not using shadcn for: `monaco-editor` (use `@monaco-editor/react`
directly), `vtk.js` 3D viewport, `plotly.js` band charts (Phase 0
will hand-roll SVG; Phase 4 may adopt Plotly).

## Tech stack

**Backend**:

- `FastAPI` — Python async framework, OpenAPI schema generation,
  aligns with existing `src/` Python codebase
- `pydantic v2` — schema validation matches the existing
  `src/notion_sync/schemas.py` style
- `uvicorn[standard]` — ASGI server with WebSocket support
- `python-multipart`, `aiofiles` — upload + streaming file support
- **No new Python deps in `src/**`** — only the FastAPI layer
  adds to the dependency graph, behind a `[project.optional-
  dependencies.ui]` group

**Frontend**:

- `vite` + `react` + `typescript` — fast dev loop, good tree-shaking,
  TypeScript end-to-end (shared schema types with backend via
  `openapi-typescript` codegen)
- `tailwindcss` + `shadcn/ui` + `lucide-react`
- `@tanstack/react-query` — server state, caching, background refetch;
  used as the single source of truth for remote data
- `zustand` — client-only state (editor unsaved-state, UI toggles);
  deliberately picked over Redux for smaller surface area
- `react-router-dom` v6 — standard; Phase 0 defines the routes
- `@monaco-editor/react` + `monaco-yaml` — Phase 1+
- `plotly.js-basic-dist` — Phase 4+ (Phase 0 does SVG band chart by hand)
- `vtk.js` — Phase 3
- `zod` — runtime schema validation for backend responses

**Build / CI**:

- `pnpm` for frontend (faster, content-addressable, disk-efficient)
- `uv` for Python (consistent with existing repo posture)
- GitHub Actions workflow `/.github/workflows/ui-ci.yml`:
  - `pnpm install && pnpm typecheck && pnpm test && pnpm build`
  - `uv pip install -e ".[ui]" && pytest ui/backend/tests/`
  - Added in Phase 1 (Phase 0 ships without CI wiring)

**Deployment** (Phase 5+):

- Docker Compose for dev / self-hosted-enterprise customers
- Single FastAPI + static-react container; Postgres + Redis as
  separate containers
- For SaaS: deploy to Fly.io or Render with automatic PR previews
- Audit-package signing key per customer, managed via Doppler or
  1Password Connect

## Accessibility

- **WCAG 2.2 AA minimum**; **AAA where reasonable** (regulated-market
  expectation)
- Every interactive element keyboard-accessible; visible focus ring
  (`ring-2 ring-ring ring-offset-2`)
- Color semantics always paired with an icon or text label (never
  color-only)
- Motion respects `prefers-reduced-motion`
- All `aria-*` attributes from shadcn defaults preserved
- High-contrast mode: the dark theme meets AAA for body text

## Error, empty, and loading states

Standardized patterns:

- **Loading** — `<Skeleton>` placeholders matching final layout;
  never spinners-in-vacuum
- **Empty** — illustration + one-line explanation + single primary
  CTA ("No cases yet. Add your first case →")
- **Error** — machine-readable + human-readable message;
  always show a retry + a "copy diagnostic info" button (copies
  request ID, timestamp, user agent to clipboard for support tickets)
- **Offline** — banner at top: "Working offline. Changes saved
  locally will sync when connection restored." (Phase 4+)

## Testing strategy (overview; detail in `docs/ui_roadmap.md`)

- **Unit** — component-level; `vitest` + `@testing-library/react`
- **Integration** — API contract between FastAPI + React via
  generated OpenAPI types; `vitest` + `msw` for mocks
- **End-to-end** — `playwright`; Phase 4+ only (expensive to maintain,
  high signal)
- **Visual regression** — `playwright` screenshot assertions for
  Screen 4 band chart and Screen 6 PDF render; Phase 5
- **Backend** — `pytest` under `ui/backend/tests/`, separate from
  existing repo-level `tests/**` tree (禁区 isolation)

## Open questions (surfaced for external Gate review)

None blocking Phase 0. The following are flagged for revisit at
Phase 3 / 5 gates:

- **Audit package signing**: HMAC per-project vs. Ed25519 per-
  organization vs. full PKI. MVP uses HMAC for simplicity; revisit
  before first regulated-customer pilot.
- **Data residency**: some aerospace customers will require
  on-premise deployment. Defer SaaS-vs-self-hosted decision to
  Phase 5 and treat both as supported from day one.
- **Multilingual UI**: Kogami's working language includes Chinese;
  user base may be global. Phase 0..4 ship English-only; Phase 5
  reassesses i18n scope based on customer discovery.
