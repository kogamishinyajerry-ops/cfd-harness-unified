---
decision_id: DEC-V61-202-SUB-M30-CYCLE7-BEGINNER-TEST
title: M3.0 cycle 7 — junior-engineer beginner test (litmus surrogate)
status: Accepted
proposed_date: 2026-05-23
accepted_date: 2026-05-23
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 7 (litmus surrogate · M3.0 close)
notion_sync_status: synced 2026-05-23 (https://www.notion.so/368c68942bed81b28e30d622864c0ed9)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE
  - DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR
  - DEC-V61-202-SUB-M30-CYCLE3-FOCUS-DRIVER
  - DEC-V61-202-SUB-M30-CYCLE4-MULTIPHYSICS-DOGFOOD
  - DEC-V61-202-SUB-M30-CYCLE5-E2E-DEFAULT-ON
  - DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL
  - DEC-V61-202-SUB-M30-CYCLE6-PROVENANCE-AUDIT-V2
---

## Why

The DEC-V61-202 charter litmus is *"junior CFD engineer constructs
case_007 KCS ship VOF in ≤30 minutes via the dynamic UI"*. Cycles 1-6
+ integration built and instrumented the engine; cycle 7 measures whether
the engine actually drives a beginner forward.

We don't have a real junior engineer on the loop, so cycle 7 is a
**programmatic surrogate**: an agent that follows whatever the rail says
at each step, applies the suggested fix, and advances when the topbar CTA
is enabled. We measure (a) does the rail drive monotonic forward progress,
(b) does step transition happen at most once per step (no back-and-forth),
(c) is the total interaction count within a 30-minute budget proxy, and
(d) does the provenance log faithfully replay the journey.

Pass = the workbench is coherent enough that a *programmatic* engineer
can reach a solveable case from a sparse starting state in ≤20
rail interactions. If a real junior engineer with comparable behaviour
hits ≥2x that count, M3.1 needs UX work — but the engine itself is
proven coherent at cycle 7.

## What

### In scope

- `scripts/dogfood/case_007_cycle7_beginner_test.py`:
  - Stages a minimal KCS-VOF skeleton manifest (case_id + family + backend),
    no artifacts
  - Loops over steps 1→5; at each step:
    - GET workbench_frame
    - If `rail.kind == "info_gap"` and `suggested_default` is present, PATCH
      the manifest with that default at `rail.field_path`
    - If `rail.kind == "info_gap"` and no `suggested_default`, the agent
      synthesizes a plausible value (one of {string token, numeric default,
      empty dict}) at `rail.field_path` to simulate engineer judgment
    - If `rail.kind == "problem_fix"` and the field_path resolves to a
      manifest field, apply a minimal mitigation
    - If `rail.kind == "step_default"` and `topbar.enabled`, advance one step
    - Track interaction count per step + total
  - **Acceptance assertions**:
    - Total decide() calls ≤ 20 (junior 30-min budget proxy)
    - Each step exited at most once (no back-edge in the step graph)
    - Within a step, rail severity decreases monotonically (FAIL → WARN
      → info → step_default), never increases
    - Provenance log file exists with the right number of lines
    - Replay reader shows the step arc as 1→2→3→4→5 in order

### Out of scope (M3.1+)

- Real human eval (separate milestone, requires recruiting an engineer)
- Full case_007 KCS interFoam solver run (compute budget; v2 of case_007)
- Multi-cycle case construction with branches/rework (assumes happy-path
  beginner journey)
- UX latency / animation polish (engine coherence first, UX second)

## Closure criteria

- [x] `scripts/dogfood/case_007_cycle7_beginner_test.py` runs ✅ with
      8 decide() calls (≤20 budget), monotonic severity (rank 3→0),
      single-pass step arc backend-driven via topbar.target_step
- [x] DOGFOOD report `.planning/dogfood/DOGFOOD_M30_CYCLE7_BEGINNER.md`
- [x] Codex ≤ 3 rounds — **R0 (2 P2) + R1 (2 P2) + R2 (APPROVE) = 2
      iteration rounds, under cap**
- [x] DEC Proposed → Accepted
- [x] M3.0 milestone retro `.planning/retrospectives/2026-05-23_m30_milestone_close.md`
- [x] Notion sync (session-end, Accepted DECs only) — https://www.notion.so/368c68942bed81b28e30d622864c0ed9

## Closure addendum (2026-05-23)

**R0** — 2 P2 findings, no P1:
- severity check was vacuous (read `rail.severity` which doesn't exist;
  rank map missed `critical`/`warning` gap vocabulary). Fix: parse
  severity from `rail.provenance` strings; extend rank map to cover
  both vocabularies.
- step advance ignored backend `topbar.target_step`; back-edge would
  PASS. Fix: capture every transition; assert `to == frm+1, 1 ≤ to ≤ 5`.

**R1** — 2 more P2 (second-order holes from R0 fixes):
- step-5 terminal CTA not validated; regression to `kind=next_step` at
  the terminal frame would slip through. Fix: snapshot the step-5
  topbar before breaking; validate `submit_solve / target_step=None /
  enabled=True`.
- `target_step=0` would crash harness on next GET before the
  well-formed check could fire. Fix: validate range 1..5 BEFORE
  assigning; record bad value so check fails loudly with payload visible.

**R2** — APPROVE: "the new step-5 snapshot check and the target-step
range guard both make malformed backend responses fail explicitly
instead of slipping through or crashing."

Result: 8/8 checks PASS, 8 decide() calls, step transitions
`[(1,2),(2,3),(3,4),(4,5)]` verified, step-5 CTA contract confirmed.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Programmatic agent passes but real engineer fails | Cycle 7 is a *necessary not sufficient* litmus; real eval is M3.1 |
| Agent finds "trivial" fixes that real engineers wouldn't | suggested_default path mirrors UI affordance; synthesized fallback is a transparency liability we document, not hide |
| ≤20 budget arbitrary | Document it explicitly as "1.5 min/action × 30 min wall-clock"; revisit in M3.1 from real eval data |
| Step graph back-edges hide rework loops | Test asserts each step exited at most once; loops fail the test |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Predecessors: cycles 1-6 + integration (engine + audit log live)
- User authorization 2026-05-23: "我批准你的多agent团队持续工作，奔着里程碑继续"

Surface-scan: clean (new dogfood script + retro doc, no top-level
production files added)
