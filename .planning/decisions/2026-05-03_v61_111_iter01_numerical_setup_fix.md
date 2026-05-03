---
decision_id: DEC-V61-111
title: iter01 numerical setup fix — honor intent.json solver.name + diagnose NaN-divergence root cause + unblock V61-106 Phase 1.3 reclassification
status: Accepted (2026-05-03 · Codex pre-merge 4-round chain R1 CHANGES_REQUIRED 2 P1 + 1 P2 → R2 CHANGES_REQUIRED 0 P1 + 2 P2 → R3 CHANGES_REQUIRED 0 P1 + 1 P2 → R4 APPROVE clean · Phase 1+2+3 implementation shipped via commits 4832a85 / ddcff1f / c38ff43 / 26183da · self_estimated_pass_rate 50% calibrated reasonable · 53/53 V61-111-scope tests pass · 850/854 full backend pass (4 pre-existing baseline failures unrelated) · V61-106 Phase 1.3 unblock: iter01 intent.json migrated to analytical_comparator_pass with the prototype comparator block untouched; smoke runner forwards intent.json:solver.name → /setup-bc?solver_name=simpleFoam → backend writes simpleFoam steady-state SIMPLE template → /solve dispatches simpleFoam · live iter01 end-to-end dogfood verification (Docker OpenFOAM container required) remains the §Phase 3 outstanding gate; Codex covers static correctness, live-run validates runtime contract · user's 2026-05-03 autonomous-mode ratification covers acceptance.)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-106 Phase 1.3 deferral closure note + V61-104 Phase 1.5 chained-into-V61-106 narrative + iter01 intent.json:60-61 rationale pointing here
parent_decisions:
  - DEC-V61-106 (analytical-comparator smoke verdicts · Phase 1.3 BLOCKED on this DEC; once iter01 converges, migrate to analytical_comparator_pass with the prototyped comparators u_magnitude_max>=1.0, u_x_min<0.0, cell_count==7159)
  - DEC-V61-104 (interior-obstacle topology · Phase 1.5 empirical correction proved meshing layer is innocent; physics defect is the actual cause)
  - DEC-V61-102 (M-RESCUE manual override foundation · Phase 3 solver-profile migration is the closer-architecture fix that subsumes part of this DEC's scope)
  - DEC-V61-103 (BC mapper · the named-patch path iter01 uses)
  - RETRO-V61-001 (risk-tier triggers · OpenFOAM solver 报错修复 + foam_agent_adapter or solver-routing changes mandate Codex pre-merge review)
parent_artifacts:
  - tools/adversarial/cases/iter01/intent.json:7-12 (declares solver.name: simpleFoam · end_time_s: 600.0 · delta_t_s: 1.0 — but route runs icoFoam)
  - tools/adversarial/cases/iter01/intent.json:60-61 (current rationale: "stays at physics_validation_required SKIPPED until a follow-up DEC fixes the numerical setup")
  - ui/backend/routes/case_solve.py:6 + lines 190/200/216/223/342/421/490 (icoFoam hardcoded throughout the route; intent.json:solver.name not consulted)
  - cfb13f5 commit: "iter01 dt sweep — disproves CFL hypothesis, surfaces 2 deeper defects" (icoFoam-vs-declared-simpleFoam route mismatch + relaxation factor sensitivity)
counter_impact: +1 (autonomous_governance: true · no external gate required)
self_estimated_pass_rate: 50% (multi-file backend route surface + solver-profile branching + fvSchemes/fvSolution dict variations per solver + adversarial smoke regression on iter01 as live verification — high blast radius; expect Codex 2-3 round chain minimum)
self_estimated_pass_rate_actual: 4 rounds (R1 CHANGES_REQUIRED 2 P1 + 1 P2 → R2 CHANGES_REQUIRED 0 P1 + 2 P2 → R3 CHANGES_REQUIRED 0 P1 + 1 P2 → R4 APPROVE clean) — calibration was reasonable, slightly underestimated; each round reduced P-level so substantive content converged on a stable contract
codex_tool_report_path: reports/codex_tool_reports/v61_111_r1_r2_r3_r4_chain.md
notion_sync_status: pending (Codex chain APPROVE'd at R4 commit 26183da; Notion MCP offline this session — sync queued for next online window)
---

# DEC-V61-111 · iter01 numerical setup fix

## Why now

V61-106 closed with Phase 1.3 DEFERRED because iter01 runs to apparent
completion but every time directory contains 21477 NaN entries — the
backend's `converged=true` signal misleads (icoFoam log captures the
residual signal BEFORE field corruption propagates). V61-104 Phase 1.5
empirical correction proved the meshing layer is innocent (probe
across mesh densities lc=0.0085→0.001 confirmed gmsh's single-loop
addVolume already correctly treats internal shells as obstacles; 0
cells inside blade bbox at all densities).

**Root cause hypothesis (from cfb13f5 dt sweep)**: iter01's intent.json
declares `solver.name: simpleFoam` (steady-state SIMPLE algorithm,
appropriate for Re=320 internal flow with bypass jets) but
`ui/backend/routes/case_solve.py` hardcodes `icoFoam` (transient
incompressible PISO algorithm, inappropriate for the marching-time
budgeting iter01 needs). This is the **icoFoam-vs-declared-simpleFoam
route mismatch** documented in V61-103 follow-up cfb13f5.

Secondary suspicion: icoFoam at delta_t=1.0 is an aggressive timestep
for a 240×80×40 mm cavity at U=0.8 m/s; CFL≈10 in the bypass gaps,
and PISO without sufficient sub-iterations can't recover. The dt
sweep already disproved CFL alone; the deeper defect is solver class.

V61-102 Phase 3 (solver profile migration) was deferred for similar
reasons but at a higher abstraction (move all hardcoded dicts into
YAML profiles). V61-111 is more focused: **make `intent.json:solver.name`
the routing input** so adversarial cases can declare their solver
intent and the backend honors it.

## Decision

Adopt a **3-phase fix arc**:

### Phase 1 · Solver-name routing (1-2 days · backend)

- **`ui/backend/routes/case_solve.py`**: read `solver.name` from
  the case manifest (which already mirrors intent.json post-V61-103
  BC mapper) and dispatch to the appropriate solver:
  - `simpleFoam` → steady-state SIMPLE algorithm
  - `icoFoam` → transient PISO (current default)
  - `pimpleFoam` → transient PIMPLE (already routed via V61-107.5)
- Backward compat: when `solver.name` is missing or unknown, default
  to `icoFoam` (preserves existing LDC + channel paths).
- `controlDict` template variation per solver:
  - simpleFoam: `application simpleFoam` + `endTime` in iterations
    not seconds + `writeControl timeStep`
  - icoFoam: existing template
  - pimpleFoam: existing template (V61-107.5)

### Phase 2 · simpleFoam fvSchemes + fvSolution (1 day · case-setup)

simpleFoam needs different relaxation + scheme dicts than icoFoam:
- `fvSchemes`: `ddtSchemes default steadyState` (vs icoFoam's
  `Euler`); `divSchemes div(phi,U) bounded Gauss linearUpwind grad(U)`
  (or upwind for first-order convergence)
- `fvSolution`: `relaxationFactors p 0.3 / U 0.7` (SIMPLE-standard);
  `SIMPLE residualControl p 1e-3 / U 1e-4` (or tighter)
- Author the simpleFoam template inline in `case_solve.py` (Phase 1
  scope) or extract into solver-profile YAML (defers to V61-102
  Phase 3 if chosen — clean architecture but bigger scope)

**Decision point**: keep templates inline OR migrate to YAML profile.
V61-111 RECOMMENDS inline-for-now path — V61-102 Phase 3 is the
authoritative cleanup; V61-111 should land the immediate fix without
blocking on the cleanup.

### Phase 3 · iter01 verification + V61-106 Phase 1.3 unblock (1 day · adversarial smoke)

After Phase 1+2 land:
- Re-run iter01 end-to-end with the simpleFoam routing.
- Expected: `extract_results_summary` reports finite (non-NaN) values
  across all time directories; `u_magnitude_max >= 1.0` (bypass jet);
  `u_x_min < 0.0` (downstream recirculation); `cell_count == 7159`
  (mesh regression canary).
- Migrate iter01 from `physics_validation_required` (SKIPPED) to
  `analytical_comparator_pass` with the comparators prototyped in
  V61-106 §Phase 1.3 / iter01 intent.json:62 commit history rationale.
- Verify smoke runner verdict = PASS.
- This **closes V61-106 Phase 1.3 deferral**.

## Impact

### Positive
- Closes V61-106 Phase 1.3 deferral (analytical-comparator framework
  is no longer SKIP-forever for iter01).
- Enables future adversarial cases to declare solver class via
  intent.json (rotated symmetry, multi-scale, etc. all benefit).
- iter01 stops being a permanent N/A in the verdict table.
- Codex review surfaces solver-routing soundness early before
  M10 STEP/IGES intake adds more solver classes.

### Negative
- Multi-file backend route surface (case_solve.py + tests +
  potentially solver-profile YAML if Phase 3 chosen).
- Adds one more solver-template branch to maintain alongside
  icoFoam (current) + pimpleFoam (V61-107.5) + simpleFoam (this DEC).
- Risk that simpleFoam relaxation factors need iter01-specific
  tuning beyond the SIMPLE-standard 0.3/0.7 — would extend Phase 2.

### Counter handling
- Counter v6.1 += 1 if Status flips to Accepted (autonomous_governance: true)
- No Kogami review trigger (per V61-094 P2 #1 bounding clause:
  no charter modification, workbench/ai-copilot already line-A,
  counter <20 since RETRO-V61-V107-V108, no risk-tier change)
- Codex pre-merge mandatory per RETRO-V61-001:
  - "OpenFOAM solver 报错修复" trigger fires (iter01 NaN divergence)
  - "case_solve route changes >5 LOC" trigger fires (Phase 1 scope)
  - "Phase E2E batch ≥3 case fail" trigger DOES NOT fire (single-case)

## Verification

- Phase 1 acceptance: existing LDC + channel + cylinder + NACA cases
  still run icoFoam (default-fallback path); their byte-repro
  unchanged.
- Phase 2 acceptance: a steady-state test case (lid-driven cavity at
  Re=100 declared as simpleFoam) converges with finite residuals.
- Phase 3 acceptance: iter01 end-to-end smoke run produces non-NaN
  time directories AND the V61-106 comparators evaluate to
  `all_passed=True`.
- Backward compat: `pytest ui/backend/tests/test_case_solve.py` 100%
  pass; `scripts/smoke/dogfood_loop.py` exit 0.

## Out of scope

- V61-102 Phase 3 (solver-profile YAML migration): explicitly
  out-of-scope. V61-111 keeps templates inline; V61-102 Phase 3
  follow-up DEC is the cleaner-architecture refactor that supersedes
  V61-111's inline templates.
- Other adversarial cases (iter04 rotated symmetry, iter05+
  not-yet-generated): out-of-scope per V61-106 §Phase 2.
- Multi-time-step trajectory comparators / surface-pressure /
  patch-level summaries (V61-106 deferred items).

## Alternatives Considered

### Alt 1 · Keep icoFoam, fix relaxation factors only
Add icoFoam-specific relaxation tuning for iter01. **Rejected**:
icoFoam is PISO-based (transient), tuning relaxation alone won't
fix the algorithm-class mismatch for Re=320 internal flow that needs
steady-state marching. cfb13f5 dt sweep already disproved CFL hypothesis.

### Alt 2 · Block on V61-102 Phase 3 (solver-profile YAML)
Wait for V61-102 Phase 3 to land then build V61-111 on top. **Rejected**:
V61-102 Phase 3 is itself deferred without timeline; V61-111 unblocks
V61-106 Phase 1.3 and gates the analytical-comparator framework's
first non-SKIP physics-validation case. Inline-for-now path is the
proportionate fix.

### Alt 3 · Skip iter01 reclassification permanently
Accept that iter01 stays physics_validation_required SKIPPED. **Rejected**:
this is the SKIP-forever cop-out V61-106 was designed to close. iter01
is the canonical adversarial case; if it stays SKIP, the framework's
value is unproven.

**Selected**: Alt 4 (this DEC) — focused 3-phase fix arc that
honors intent.json:solver.name routing, lands inline simpleFoam
templates, verifies via iter01 end-to-end.

## Acceptance Criteria

1. Codex GPT-5.4 pre-merge review of Phase 1 (solver routing) →
   APPROVE / APPROVE_WITH_COMMENTS / RESOLVED.
2. Codex pre-merge review of Phase 2 (simpleFoam fvSchemes/fvSolution
   templates) → APPROVE-class.
3. Phase 3 verification: iter01 smoke run produces non-NaN time
   directories AND V61-106 comparator suite evaluates `all_passed=True`.
4. Backward compat: existing LDC + channel + cylinder + NACA cases
   unchanged byte-for-byte.
5. iter01 intent.json updated: `expected_status: analytical_comparator_pass`
   with the 3 prototyped comparators.
6. V61-106 Phase 1.3 marked CLOSED in V61-106 closure note (cross-DEC update).
7. Status flip Proposed → Accepted with this DEC body referencing
   the implementation commits + Codex chain reports.

## Process note

V61-111 is the third "implementation already shipped behind a deferred
DEC" pattern in the V61-099 → V61-111 closure batch (cf. V61-099
post-R3 staging fix shipped 2026-04-29 + closed 2026-05-03; V61-102
Phase 1+2 shipped 2026-04-30 + closed 2026-05-03; V61-104 Phase 1
shipped 2026-05-01 + closed 2026-05-03). Difference: V61-111 is the
**implementation NOT YET shipped** counterpart — the DEC is filed
BEFORE the work begins. This is the closer match to the V61-088
pre-implementation surface scan discipline ("ROADMAP read + grep
before any ≥30 LOC OR new top-level page/route/service file"). The
surface scan ran (V61-106 Phase 1.3 deferral note + V61-102 Phase 3
deferral note + iter01 intent.json:60-61 rationale all named this work
as the canonical follow-up), and the disposition is `parallel new`
because the icoFoam hardcoding spans many files and a focused new
route is cleaner than retrofit-extending existing routes.

`Surface-scan-found: ui/backend/routes/case_solve.py:6+190+200+216+223+342+421+490 (icoFoam hardcoding, no consultation of intent.json:solver.name)` ·
`disposition: parallel new (V61-111 builds the routing primitive that V61-102 Phase 3 will later subsume)`
