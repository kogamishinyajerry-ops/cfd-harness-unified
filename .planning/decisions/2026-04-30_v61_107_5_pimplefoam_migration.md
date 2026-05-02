---
decision_id: DEC-V61-107.5
title: pimpleFoam migration for the named-patch BC mapper + post-flight rejection plumbing
status: Accepted (2026-05-01 · Codex APPROVE on R20 commit c924360 after 9 rounds R12-R20)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-30
authored_under: |
  user direction "全权授予你开发，全都按你的建议来" + standing CFD strategic
  target "处理任意的 CAD 几何". Direct continuation of DEC-V61-107: V107
  closed as fvSchemes-only partial; the pimpleFoam migration + post-flight
  rejection plumbing (the broader V107 plan) lands here as V107.5.
parent_decisions:
  - DEC-V61-107 (partial fvSchemes upgrade · this DEC builds on V107's solver-config foundation)
  - DEC-V61-103 (Imported-case BC mapper · provides the named-patch substrate driving the new control loop)
  - DEC-V61-105 (Adversarial smoke as hot-path regression gate · exercises this DEC's new solver path)
  - RETRO-V61-001 (risk-tier triggers · solver migration + new SSE event surface = mandatory Codex review)
  - RETRO-V61-053 (executable_smoke_test risk_flag · post-R3 defects on solver paths informed scope)
parent_artifacts:
  - ui/backend/services/case_solve/foam_agent_adapter.py (solver dispatch + SSE event emitter)
  - ui/backend/services/case_solve/solver_streamer.py (FOAM FATAL block detection regex; failed/failed_reason fields on done event)
  - ui/backend/services/case_solve/bc_setup_from_stl_patches.py (named-patch mapper that feeds the new control loop)
  - ui/frontend/src/pages/workbench/step_panel_shell/SolveStreamContext.tsx (SSE consumer; phase=error vs phase=completed branching)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 45% (multi-file solver migration + new SSE event field + new error surface — anticipated solver-config rough edges and partial-migration drift)
actual_pass_rate: ~10% (Codex required 9 rounds — under-calibrated by ~0.30; root cause: I should have grep'd for every reference to icoFoam BEFORE the first commit so the migration surface was bounded explicitly)
codex_tool_report_path: reports/codex_tool_reports/v61_107_5_r17_r20_chain.md (R17-R20 leg; R12-R16 leg lives in commits 7ac83a1/d63e14d/c1225da/3210994/6bdcf21 messages — chain report for R12-R16 leg deferred per "chain report covers tail of the chain" convention; full provenance available via git log)
implementation_commits:
  - 027e236 (feat: pimpleFoam migration for named-patch BC mapper)
  - 7ac83a1 (R12 P1+P2 closure)
  - d63e14d (R13 P2-A + P2-B closure)
  - c1225da (R14 P1+P2 closure)
  - 3210994 (R15 P2-A + P2-B closure)
  - 6bdcf21 (R16 pragmatic scope reduction · ratified in RETRO-V61-V107-V108 as ONE-OFF PRECEDENT FLAG)
  - 2ff11d9 (R17 P1+P3 closure)
  - 7e9483a (R18 P1-A + P1-B closure · IO ERROR variant detection)
  - c924360 (R19 P1 verbatim closure · unused-import removal)
  - e10c9b5 (R17-R20 chain report)
notion_sync_status: pending — to sync 2026-05-02

# Why now

The named-patch BC mapper from DEC-V61-103 was wired into icoFoam,
but icoFoam's incompressible-laminar control loop is too narrow for
realistic CFD geometry — no PIMPLE outer corrector loop, limited
turbulence wiring, and no post-flight rejection surface. pimpleFoam
is the right home: it carries the SIMPLE/PIMPLE control structure,
plays nicely with the named-patch BC mapper's variety, and gives
the solver a place to *reject* a run cleanly when boundary conditions
turn out to be inconsistent (post-flight rejection).

This DEC migrates the call site, plumbs FOAM FATAL detection into
the SSE stream so the frontend can surface failures distinctly from
clean completion, and updates fixtures so the smoke runner stays
green.

# Decision

Migrate the named-patch BC mapper's solver dispatch from icoFoam to
pimpleFoam. Add post-flight rejection plumbing:
- `solver_streamer.py` emits `failed: bool` + `failed_reason: str | null`
  on the terminal `done` SSE event when FOAM FATAL ERROR or FOAM FATAL
  IO ERROR is detected mid-stream
- `SolveStreamContext.tsx` consumes the new fields and branches
  between `phase=error` (with errorMessage surfaced) and the existing
  `phase=completed` happy path
- Critical: `removeQueries` no longer fires on failed runs

# Codex narrative

R12-R15 (4 rounds CHANGES_REQUIRED): Codex repeatedly caught
partial migrations — solver call site updated but controlDict not;
controlDict updated but post-flight rejection not plumbed; runner
updated but test fixture's expected output not re-baselined.

R16 (pragmatic scope reduction): R12-R15 had me building elaborate
static guards (e.g. fvSchemes scrutiny that rejected user override
of `default none` divDevReff terms) that Codex itself rejected as
too brittle. R16 dropped the guard family entirely and let runtime
detection take over. The R16 commit was tagged "pragmatic scope
reduction" in lieu of "verbatim" — flagged as ONE-OFF PRECEDENT
in RETRO-V61-V107-V108 (verbatim subtype "pragmatic" not recognized
going forward).

R17-R18 (2 rounds CHANGES_REQUIRED): R17 found that the frontend
didn't surface FOAM FATAL events at all — the `done` event landed
silently; R18 found that the regex only matched `FOAM FATAL ERROR`,
not `FOAM FATAL IO ERROR`. Both closed cleanly with regex
alternation + new SSE event fields.

R19 (verbatim, 1 round): unused `screen` import blocking tsc; trivial
1-line removal that maps 1:1 to the Codex bullet.

R20 APPROVE.

# Verification

- Smoke baseline (4 PASS · 0 EF · 2 SKIP · 0 FAIL) preserved on
  every closure commit across 9 rounds
- 0 post-R3 defects in the arc
- Frontend tsc clean; 165/165 frontend vitest green at R20

# Future work

The post-flight rejection plumbing now exists; concrete rejection
classes (out-of-bounds Re, non-convergent residuals after N steps,
etc.) can be added incrementally as the user encounters them. No
follow-up DEC required.
