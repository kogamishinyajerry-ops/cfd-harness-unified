---
decision_id: DEC-V61-026
timestamp: 2026-04-21T18:40 local
scope: |
  Option A Phase 2 deepening of /learn — interactive mesh-density
  slider + Pro Workbench entry link. Combines user-directive items
  (1) "Interactive mesh-density demo" and (3) "Pro Workbench tab
  wiring" in one PR per session plan "do 1 + 3 together".

  New `grid_convergence` RunCategory + 12 fixtures (3 cases × 4 meshes)
  + new Mesh tab + SVG ConvergenceSparkline. Pro Workbench link on
  LearnCaseDetailPage routes to existing /cases/:id/report.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: 56d86d8
codex_tool_report_path: null
  (Codex round 12 ran inline via `codex exec` on commit 56d86d8; output
  lives in `/private/tmp/.../bw3zj0mgm.output`. Same archival backlog
  as DEC-V61-024/V61-025 — queued for `reports/codex_tool_reports/`.)
codex_verdict: CHANGES_REQUIRED → RESOLVED (round 12; 3 MED + 1 LOW
  findings, all applied in 32a2893).
  MED-1: `list_runs()` returned filename-lex order → mesh_160 sorted
  before reference_pass, Compare tab no longer opened on reference.
  Fix: explicit pedagogical category order with numeric mesh_N secondary.
  MED-2: TFP mesh fixtures claimed "5% 容差" but gold is ±10% → copy
  disagreed with comparator. Fix: updated all four fixtures to 10%.
  MED-3: BFS narrative claimed "convergence to Driver 1985 gold" but
  whitelist Re=7600 ≠ Driver Re_H≈36000. Fix: relabel as "convergence
  to repo gold" with explicit Re-mismatch note.
  LOW: ConvergenceSparkline + formatNumber let NaN through (NaN == v
  is true for `v != null`). Fix: `Number.isFinite` guards at all render
  sites.
counter_status: "v6.1 autonomous_governance counter 13 → 14."
reversibility: fully-reversible-by-pr-revert
  (15 files changed on main commit; 9 files changed on follow-up. All
  additive fixture files, 1 RunCategory literal expansion, 1
  component addition + sort logic. `git revert -m 1 <merge>` restores
  prior state cleanly. Hook-count stability in `MeshTab` verified by
  Codex — `useQueries({queries: []})` is safe when no sweep exists.)
notion_sync_status: pending
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/35
github_merge_sha: 5d54d48
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 82%
  (Same as DEC-V61-025 in spirit — multi-file frontend + API schema
  change. Honest pre-Codex estimate was 85%; got CHANGES_REQUIRED
  with 3 MED + 1 LOW (no HIGH this round, improvement over PR #34's
  2-HIGH verdict). Calibration: every multi-file frontend + schema
  change sits in the 75-90% band until we build a pre-Codex checklist
  covering (a) sort-order test coverage when adding run categories,
  (b) tolerance-copy regression grep against gold_standards/*.yaml,
  (c) Reynolds-consistency between whitelist and literature source.)
supersedes: null
superseded_by: null
upstream: DEC-V61-025 (PR #34 full-coverage deepening) — this decision
  is the next layer of commercial-demo depth: where V61-024/V61-025
  delivered breadth (every case has coverage), V61-026 delivers depth
  for 3 flagship cases (LDC/TFP/BFS each get an interactive convergence
  demo instead of just static fixtures).
---

# DEC-V61-026: interactive mesh-density slider + Pro Workbench entry

## Why now

User directive after DEC-V61-025 landed: *"do 1 + 3 together"*.
Item 1 = interactive mesh-density demo (the most pedagogically valuable
next feature per session-end ranking). Item 3 = Pro Workbench tab
wiring (closes the "student ↔ auditor" narrative arc that DEC-V61-024
originally called out but hadn't implemented).

Combining them in one PR made sense because:
- Item 3 is ~3 LOC (a Link component) + matches Item 1's scope
  (LearnCaseDetailPage touches)
- Both are contained within the /learn surface, same QA path
- Single Codex round instead of two

## What landed

### Commit 56d86d8 — feat(learn): slider + Pro Workbench entry

**New `grid_convergence` RunCategory**:
- Backend: `ui/backend/schemas/validation.py` Literal expanded from 4 → 5 values
- Frontend: `ui/frontend/src/types/validation.ts` mirrors the change
- Categoriy labels + colors added to LearnCaseDetailPage dictionaries

**12 new fixtures** (3 cases × 4 mesh densities each):

| Case | Sweep values | Gold | Tol |
|---|---|---|---|
| lid_driven_cavity | `{-0.048, -0.042, -0.038, -0.0375}` u @ y=0.0625 | -0.03717 (Ghia 1982) | 5% |
| turbulent_flat_plate | `{0.0065, 0.0052, 0.00436, 0.00423}` Cf @ x=0.5 | 0.00420 (Blasius) | 10% |
| backward_facing_step | `{4.8, 5.5, 6.1, 6.25}` Xr/H | 6.26 (repo) | 10% |

All sweeps monotone → classroom-friendly convergence story.
Run_ids use `mesh_{N}` convention (mesh_20, mesh_40, mesh_80, mesh_160).

**New UI**:
- `MeshTab` — new 5th tab on LearnCaseDetailPage between Compare and Run
- `useQueries` — parallel fetch of all 4 densities on tab mount so slider feels instant
- `ConvergenceSparkline` — SVG plot showing value vs density with gold line + tolerance band + per-point status color
- Density slider + numeric anchor buttons + live value/deviation/verdict card
- Empty state for cases without a sweep (DHC / duct / NACA / etc)

**Pro Workbench entry**:
- Top-right inline link on LearnCaseDetailPage: "进入专业工作台 · Pro Workbench →"
- Routes to `/cases/:caseId/report` (existing ValidationReportPage from Phase 0)
- Restrained surface-border treatment — not a CTA, just a "when you're ready" affordance

### Commit 32a2893 — fix(learn): Codex round 12 closure

See Codex verdict block above. Summary:
1. Explicit category + numeric-aware run ordering in `list_runs()`
2. TFP fixtures 5% → 10% tolerance copy match
3. BFS fixtures relabeled "repo gold" vs "Driver 1985 literature gold"
4. NaN guards at ConvergenceSparkline / formatNumber / deviation render sites

## Regression

- **Backend pytest**: 42/42 green, including extended
  `test_case_runs_endpoint_lists_reference_pass_first` with order assertions
- **Frontend tsc --noEmit**: clean
- **`list_cases()`**: 8 PASS · 2 HAZARD across 10 cases · 43 runs
  (was 31 — added 12 mesh runs)
- **三禁区**: untouched (no writes to `src/**`, repo-root `tests/**`,
  `knowledge/gold_standards/**`, `knowledge/whitelist.yaml`)

## Delta

| Metric | After V61-025 | After V61-026 |
|---|---|---|
| Total curated runs | 31 | 43 |
| Cases with interactive demo | 0 | 3 (LDC/TFP/BFS) |
| Cases with Pro Workbench link | 0 | 10 |
| Frontend routes | /learn + Pro (phase 0 unchanged) | same + cross-link |
| RunCategory literal values | 4 | 5 |

## Known residuals

1. **BFS Reynolds mismatch predates PR**. Whitelist declares Re=7600,
   but Driver & Seegmiller 1985 gold Xr/H=6.26 is documented at
   Re_H≈36000 (NASA TMR, OpenFOAM validation cases). The new mesh
   narrative no longer over-claims, but the underlying gold-anchor
   vs literature-anchor gap lives on as a Q-class item. Future work:
   either re-source BFS gold to a Reynolds-consistent benchmark at
   Re=7600 (Kim/Moin/Moser 1987 channel analog) or bump whitelist
   Re to 36000 (impacts adapter mesh). **NOT triggering Gate Q-3**
   since this precedes the PR.

2. **Interactive slider only covers 3 of 10 cases.** The other 7
   render an empty state with a hint. If we want universal coverage,
   each additional case needs 4 fixtures + a literature-sourced gold
   anchor for `_plain_scalar_quantity`. Carries forward as
   Option A Phase 3 if pursued.

3. **Pro Workbench link is a link, not a tab.** It takes the student
   out of the /learn shell and into the Pro layout. Could be made
   smoother with a slide-over modal, but that adds modal-routing
   complexity for negligible UX gain (Pro page has its own nav back
   via the logo).

## Pending closure

- [x] PR #35 merged as `5d54d48`
- [ ] STATE.md update
- [ ] Notion sync DEC-V61-026 + backlog (V61-021/022/023/024/025 + RETRO-V61-002 still pending; token expired)
