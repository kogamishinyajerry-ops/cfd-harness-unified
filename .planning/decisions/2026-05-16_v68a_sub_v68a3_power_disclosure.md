---
decision_id: DEC-V68-A.3
title: V68-A.3 · Step body Power-mode disclosure adoption · 5 step bodies + reusable PowerDisclosure wrapper
status: Accepted
parent_dec: DEC-V68-A-charter
phase: V68-A
notion_sync_status: pending
predecessor: DEC-V68-A.2
batch: B129
confidence: med
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-A charter §4 Done dim #3 + V67-C.3 BeginnerPower context
---

# DEC-V68-A.3 · Step body Power-mode disclosure adoption

## 1 · Decision

Land reusable `PowerDisclosure` wrapper component + adopt it in all 5 step
bodies (Step1Import / Step2Mesh / Step3SetupBC / Step4SolveRun /
Step5ResultsView). Each step body gates ONE advanced section behind
`useBeginnerPowerOptional().isPower`.

**Done dim #3 (Step body Power-mode adoption) → FULL-MET** at sub-DEC landing.

## 2 · Rationale · why now

V67-C.3 landed the BeginnerPower context + Toggle (Engineer Control Rail
infrastructure) but no step body consumed it. The toggle existed; the
disclosure semantics didn't. V67-C close DEC §10 explicitly deferred
"step body adoption" to V68-A.3.

V68-A.3 closes that loop with the **minimum surgical touch**: 1 reusable
wrapper + 5 small additions to existing step bodies. The wrapper degrades
gracefully when no Provider is present (test environments) — defaults to
Beginner-mode summary so the panel still surfaces an explanation rather
than empty space.

## 3 · Implementation

### Files added (2 NEW)

- `ui/frontend/src/pages/workbench/step_panel_shell/PowerDisclosure.tsx` (~65 LOC)
  Subscribes to `useBeginnerPowerOptional()` · Power mode renders children
  inline · Beginner mode renders single-line summary · header chip flips
  POWER ⇄ BEGINNER · graceful fallback when no Provider.
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/PowerDisclosure.test.tsx`
  4 tests: graceful no-provider fallback · Beginner mode hides advanced ·
  Power mode hides summary · default testIdPrefix.

### Files modified (5 step bodies)

Each gets +1 import + ~15-line `<PowerDisclosure>` block with concrete
engineer-tier knobs:

- `steps/Step1Import.tsx`: "Unit & coordinate system" override (m/mm/inch,
  origin offset, up-axis)
- `steps/Step2Mesh.tsx`: "sHM tuning" (nSurfaceLayers, expansionRatio,
  resolveFeatureAngle)
- `steps/Step3SetupBC.tsx`: "Solver-specific BC overrides" (turbulence
  intensity, hydraulic diameter, wall function)
- `steps/Step4SolveRun.tsx`: "Solver schemes & tolerances" (divSchemes,
  residual tolerance, relaxation factors)
- `steps/Step5ResultsView.tsx`: "Post-processing knobs" (timestep,
  colorbar, slice plane)

## 4 · Test evidence

- `vitest run PowerDisclosure.test.tsx`: **4/4 PASS**
- `vitest run` (full suite): **355/355 PASS** (was 351, +4 from new tests)
- `npx tsc --noEmit`: 0 errors
- 5 step body imports verified by typecheck pass

## 5 · v2.3 governance compliance

- **DEC scope**: sub-DEC (crosses PowerDisclosure.tsx + 5 step body files +
  vitest path · ≥3 shared paths threshold MET → full DEC, not spike-class)
- **Codex 1-sync-trigger**: NOT applicable (UI-only · no auth / signing)
- **Kogami opt-in**: NOT invoked
- **Confidence**: med (5-file modification surface · pure additive)
- **Counter**: B129 autonomous_governance=true · +1

## 6 · 4Q gate

| Q | A | Justification |
|---|---|---|
| LLM offline · workbench full pipeline | ✓ YES | PowerDisclosure is pure client-side render gating · no LLM dep |
| Artifacts produced | ✓ YES | PowerDisclosure.tsx + test file + 5 step body diffs + DEC |
| TrustGate / completeness / audit trail | ✓ YES | does not touch TrustGate; surfaces engineer-tier control symmetric to Beginner-preset audit summary |
| AI advisory-only · no mutating route | ✓ YES | no API calls · V132 MUTATING_ROUTES = 9 unchanged |

## 7 · What this LANDS for V68-A close

- Done dim #3 Step body Power-mode adoption: **FULL-MET**
- 5 step bodies now actually obey Beginner/Power toggle
- Substrate verified for V68-A.5 e2e to toggle mode mid-flow and assert
  advanced sections appear/hide

## 8 · Out of scope

- **NOT** persisting per-step advanced field values (Beginner-shows-summary
  semantics suffice for V68-A close)
- **NOT** wiring advanced fields to backend (they're explanatory ULs · real
  knobs land in M-XX advanced-controls arcs)
- **NOT** Beginner/Power per-step override (global toggle is sufficient per
  Blueprint v3 §3)

— Claude Code (Opus 4.7 1M) · B129 · V68-A.3 Power-mode disclosure · 2026-05-16
