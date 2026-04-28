---
decision_id: DEC-V61-092
title: Workbench nav-discoverability defect — expose `/workbench` from `/learn` + `/pro` shells
status: Accepted (2026-04-28 · Codex 3-round arc → APPROVE [R1 CHANGES_REQUIRED · 1 P1 responsive overflow + 2 P3 doc / R2 APPROVE_WITH_COMMENTS · 1 doc-nit / R3 APPROVE clean] · Kogami NOT triggered (no §4.1 high-risk-PR criteria met) · CFDJerry explicit ratification 2026-04-28)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-28
authored_under: post-M5.1 dogfood — CFDJerry UX criticism "没有可以使用的workbench工作台，仍然只能看到gold cases的learn内容"
parent_decisions:
  - DEC-V61-087 (v6.2 three-layer governance)
  - DEC-V61-088 (pre-implementation surface scan · routine startup discipline)
  - DEC-V61-089 (two-track invariant · Track B workbench is the imported-case home)
  - DEC-V61-091 (M5.1 imported-case verdict cap · just merged · cap is dormant pending nav exposure to fire end-to-end)
  - .planning/strategic/path_a_first_customer_recruitment_2026-04-27.md (Path A binding gate · stranger MUST be able to reach /workbench)
  - RETRO-V61-001 (risk-tier triggers · multi-file frontend + UX criticism → Codex mandatory)
parent_artifacts:
  - ui/frontend/src/App.tsx (routes /workbench/* are registered but unreached by any nav link)
  - ui/frontend/src/components/learn/LearnLayout.tsx (top-nav has only "Pro Workbench →" pointing to /pro · no /workbench link)
  - ui/frontend/src/components/Layout.tsx (Pro shell sidebar NAV has Dashboard / Cases / Decisions / Runs / Audit Package / ← Learn · NO Workbench entry)
prerequisite_status:
  m5_1_acceptance: confirmed (DEC-V61-091 Accepted 2026-04-28 · commit 7f6e3f2 + ce25e9e on main)
notion_sync_status: pending (sync after Accepted state)
autonomous_governance: true
codex_tool_report_path: reports/codex_tool_reports/m092_workbench_nav_discoverability_2026-04-28.log
kogami_review:
  required: false
  rationale: |
    Per DEC-V61-087 §4.1 high-risk-PR criteria (trust-core boundary /
    security operator endpoint / byte-reproducibility / API schema rename
    ≥3 files / verdict-graph adjacent), this fix matches NONE. None of
    the §4.1 mandatory triggers fires, so Kogami is not invoked. Codex
    per RETRO-V61-001 multi-file frontend + UX-criticism triggers is
    the applicable code-layer review.
---

# DEC-V61-092 · Workbench nav-discoverability defect fix

## Why

CFDJerry attempted the M5.1 close-out manual UI dogfood at
`http://127.0.0.1:5183/` and reported: "没有可以使用的workbench工作台，
仍然只能看到gold cases的learn内容，怎么进行全新的case计算？"

Investigation confirmed the criticism is correct:

1. Root `/` redirects to `/learn` (per `App.tsx:46` — buyer-facing
   front door established 2026-04-22).
2. `/learn` (LearnLayout) has ONE escape link: "Pro Workbench →"
   pointing to `/pro` (the Dashboard).
3. `/pro` (DashboardPage) has NO link to `/workbench`.
4. `Layout.tsx` sidebar NAV (used by `/pro` + `/cases` + `/decisions` +
   `/audit-package`) has NO `/workbench` entry.

A fresh user — including any Path A recruited stranger — cannot reach
the workbench through any link. Routes exist in `App.tsx` and the
backend / API are fully functional (programmatic dogfood passed all 9
checks at M5.1 close), but the navigation surface treats `/workbench`
as if it doesn't exist.

This is a **load-bearing defect**: Path A recruitment per
`.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md`
mandates that strangers be able to walk through ingest → mesh → run
without insider knowledge. Today they cannot, because they cannot find
`/workbench/import`. The M5.1 verdict cap shipped this morning is also
indirectly affected — the cap fires only when `mesh_already_provided`
is set on TaskSpec, which happens only via the workbench-driven import
flow; if the flow is unreachable, the cap is unreachable too.

## Pre-implementation surface scan (per DEC-V61-088)

Performed 2026-04-28 prior to code work:

1. **ROADMAP scan**: no existing milestone covers nav-discoverability.
   This is a defect fix, not a feature add — addressed under
   `RETRO-V61-001 §Q3 Codex trigger #1 (multi-file frontend) +
   UX-criticism trigger`, no roadmap displacement.
2. **Existing-implementation grep**:
   - `to="/workbench"` references in `ui/frontend/src/`: 7 hits, all
     INTERNAL to the workbench (WorkbenchTodayPage, ImportPage,
     WorkbenchIndexPage, WorkbenchRunPage). **Zero** entries from
     LearnLayout, Layout, or DashboardPage.
   - `Workbench` string in `Layout.tsx` NAV array: zero — the sidebar
     has Dashboard / Cases / Decisions / Runs / Audit Package / ← Learn
     and no Workbench entry.
   - `/workbench` link in `LearnLayout.tsx`: zero — only "Pro
     Workbench →" → `/pro`.
3. **Workbench-freeze rule check** (`tools/methodology_guards/workbench_freeze.sh`):
   freeze patterns are `ui/backend/services/workbench_`, `ui/frontend/pages/workbench/`, `ui/frontend/src/pages/workbench/`. This DEC touches only
   `ui/frontend/src/components/Layout.tsx` + `components/learn/LearnLayout.tsx`,
   which are NOT in freeze scope. No `BREAK_FREEZE` escape needed.

## Scope

### In scope (~12 LOC, 2 files)

1. **`ui/frontend/src/components/learn/LearnLayout.tsx`**:
   add a "导入新 case →" / "Import new case →" link in the top-nav,
   adjacent to "Pro Workbench →", pointing to `/workbench/import`.
   This is the load-bearing fix for Path A — a stranger landing at
   `/learn` immediately sees the import entry point.

2. **`ui/frontend/src/components/Layout.tsx`**:
   add `{ label: "Workbench", to: "/workbench", enabled: true,
   phaseLabel: "Phase 6" }` to the `NAV` array between "Dashboard" and
   "Cases" so the workbench is one click away from any pro-shell page.

### Out of scope (deferred / not changed)

- Root `/` redirect target stays `/learn` (per 2026-04-22 convergence
  round, `/learn` is the buyer/student demo front door — that decision
  is preserved).
- `WorkbenchIndexPage` content unchanged (already has "Import STL →"
  link inline — once users reach `/workbench` it works).
- DashboardPage content unchanged (no link added there since the
  sidebar Workbench entry covers the pro-shell case).
- Workbench feature surface (under `ui/frontend/src/pages/workbench/`)
  unchanged — this DEC stays out of the §11.1 freeze scope deliberately.
- No DashboardPage rendering hook for "imported cases count" — that's
  a Phase-7 visibility concern, separate DEC if/when needed.

## Why this is a defect, not a workbench feature

The workbench feature freeze (§11.1, advisory through 2026-05-19)
covers `ui/frontend/src/pages/workbench/*` — i.e., the workbench's own
surface. This DEC touches only the **shell-level navigation** that
**already references the workbench conceptually** (LearnLayout has
"Pro Workbench →"; Layout sidebar has "V&V Workbench" header). The
fix is to make those references reach the actual workbench routes
that have existed since the 60-day extension (2026-04-26) but were
never wired into nav. This is a wiring defect — adding two `<Link>`s
to point at routes that already work.

## Verification plan

### Self-test (pre-Codex)

- `cd ui/frontend && npm run typecheck` — clean (0 errors)
- `cd ui/frontend && npm test -- --run` — all existing tests pass (no
  layout tests exist; nav-link additions are pure JSX with no logic)
- Manual smoke (programmatic via `curl`): all 4 frontend routes still
  return 200 (`/learn`, `/pro`, `/workbench`, `/workbench/import`)

### Codex review

- Multi-round arc per RETRO-V61-001 (multi-file frontend + UX-criticism
  trigger #1)
- Self-pass-rate estimate: **88%** — calibrated against trivial
  frontend nav adds in prior work; small surface, no logic, no API.
  The 12% miss-band is for accessibility/a11y nits (focus styles,
  aria-current behaviors), copy choice, or i18n bilingual consistency.

### Kogami review

NOT triggered. See frontmatter `kogami_review.required: false` rationale.

### CFDJerry explicit ratification

Required per DEC-V61-087 §4.4 — pre-merge gate; STOP point.

### Visual verification (post-merge)

CFDJerry walks the previously-handed-off 5-step manual checklist
WITHOUT typing URLs:

1. ☐ `/learn` → click "导入新 case →" → lands at `/workbench/import`
2. ☐ Upload `examples/imports/ldc_box.stl` → report card renders
3. ☐ "Continue to editor" → editor at `/workbench/case/<id>/edit`
4. ☐ `/workbench/import` → upload non-watertight STL → rejection panel
5. ☐ `/pro` → sidebar "Workbench" link → lands at `/workbench`

If walkthrough passes: M5.0 dogfood deliverable fully closed end-to-end
through the UI (no URL typing).

## Failure modes considered

| Failure mode | Mitigation |
|---|---|
| Adding sidebar link breaks active-route highlighting (e.g., `/workbench/case/xxx/edit` matches both Workbench and other entries) | Use `<NavLink>` default partial-match — only the Workbench entry will be active on `/workbench*` paths since no other NAV entry uses that prefix. Existing entries (Dashboard `/pro`, Cases `/cases`, etc.) use `end={item.to === "/pro"}` pattern; preserve. |
| LearnLayout text-mark too crowded with both "Pro Workbench →" and new link | Keep "Pro Workbench →" link unchanged; add new link to its left with same visual weight + a `\|` separator. Buyer-facing demo flow preserved. |
| i18n drift — "导入新 case" mixes Chinese and English | Match existing "案例目录" Chinese-primary convention. Use "导入新 case →" matching the existing bilingual pattern in LearnLayout (案例目录 + Pro Workbench →). |
| Workbench-freeze advisory blocks the change | Freeze scope is `ui/frontend/src/pages/workbench/*` — this DEC touches `components/*` only. Verified above (§Pre-implementation surface scan). Advisory mode wouldn't block anyway. |
| Codex finds accessibility regression on focus-visible / aria-current | Address inline per Codex multi-round arc. Single-round APPROVE expected for such small surface; doc-only nits are verbatim-exception eligible. |

## Counter impact

Per V61-087 §5 truth table (autonomous_governance=true · Kogami review
not triggered, so the absence of Kogami doesn't affect counter math),
counter advances per Interpretation B (STATE.md `last_updated` SSOT).

- **Pre-advance**: 56 (post-V61-091 Accepted)
- **Post-advance**: 57

RETRO-V61-001 cadence: counter ≥20 since last arc-size retro
(RETRO-V61-005 closed Session B at counter ~50; current delta is
+6..7). Threshold not crossed; no arc-size retro fires.

## Sync

Notion sync runs only after Status flips to Accepted (i.e., after
Codex APPROVE + CFDJerry ratification). Pre-merge state stays
Proposed in the repo decisions/ directory.
