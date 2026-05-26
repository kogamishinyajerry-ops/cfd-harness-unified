---
decision_id: DEC-V61-206
title: M5.5 charter — truth-chain extension to the construction steps (de-fake boundary/doe/geometry/mesh/physics/solver)
status: Accepted
parent_dec: DEC-V61-205-M5-POST-PROCESSING-DEPTH (M5 Post truth-chain de-fake · COMPLETE)
phase: M5.5 cycle 1 (charter + surface-scan · continuation session 2026-05-26)
notion_sync_status: pending
autonomous_governance: false
confidence: high
date: 2026-05-26
ratified_by: user (chose "De-fake the other UI steps" 2026-05-26, after the turbine full-pipeline dogfood)
---

# DEC-V61-206 · M5.5 charter — truth-chain extension to the construction steps

## TL;DR

M5 de-faked **only the Post step**. The user, after the turbine full-pipeline
dogfood, observed (correctly) that boundary-setup / design-exploration / etc.
still show blueprint SVG placeholders. M5.5 extends the M5 honesty pattern —
**real run-derived data, or an explicit 示意/无 state, never silent fake data;
delete fake constants so they can't silently return** — to the remaining six
step renderers. This is a **verify-and-truthify** milestone, NOT a viz rebuild.

## Surface-scan finding (2026-05-26 · subagent audit · the reason cycles are ordered worst-first)

Every non-Post step has a `*Blueprint.ts` constant file mirroring the pattern M5
retired for Post. Findings classified A (fake-as-truth) / B (illustrative-
unlabeled) / C (chrome, fine). Key result: **most steps already fetch real data
via hooks** — the fakes are *fallback* paths or stray literals, so the high-ROI
fixes are "use the real source that's already wired, drop the fabricated
fallback."

| Step | Real hooks already wired | Worst fake-as-truth | Real source? |
|---|---|---|---|
| Physics | `useGlbAvailability` + VTP range | `Re 8.4e5 · Pr 0.71` **hardcoded literal** (renderer:64); velocity legend 0–40 fallback | literal: derive or drop · range: REAL (VTP) |
| Solver | `useResidualSeries`, run context, VTP | iter `1250/2000 · 00:12:14` overlay next to a LIVE run_id; temp `96.4°C`; GPU/CPU/MEM chips | iter/temp: REAL (`sample_count`/`key_quantities`) · host chips: NEEDS-BACKEND |
| Mesh | `meshMetrics` (densities+GCI) | `18.86M · skew 0.128` trailing fallback (renderer:88) | REAL (`meshMetrics`; show — when absent) |
| Boundary | `useV4WorkbenchContext` patches/counts | `61/62` + inlet 28/outlet 27 fallback counts | LABEL-ONLY (honest empty state) |
| Geometry | context parts + GLB | `17 零件 · 2 缝隙` intake fallback | LABEL-ONLY |
| DOE | **none** | entire step (thumbnails + Pareto + "最优 V-12" + 18h42m KPIs) | NEEDS-NEW-BACKEND (no sweep engine) |

Dead imported-but-unrendered fake constants (silent-return risk per M5):
`MESH_BLUEPRINT_HISTOGRAMS`, `GEOMETRY_BLUEPRINT_RIGHT_CARDS/_CALLOUTS/_PARTS`,
various `*_RIGHT_CARDS` / `DOE_BLUEPRINT_LEFT_TREE`.

## In scope (cycles, worst-first by ROI)

- **C1 (this DEC)**: charter + surface-scan.
- **C2 · Tier-1 fake-as-truth WITH real source** (highest ROI — the M5 "verdict
  pill" analogue): Physics Re/Pr literal + velocity fallback; Solver iter overlay
  + temperature; Mesh cell-count fallback. Use the already-wired real value, else
  honest "—". + vitest guards at the render contract.
- **C3 · Tier-2 needs-new-backend → honest interim states**: the whole DOE step
  gets a "功能开发中 · 示意" banner (no fabricated optima presented as truth);
  Solver host-telemetry chips (GPU/CPU/MEM) get an inline 示意 badge (upgrade the
  existing dashed-border disclaimer).
- **C4 · Tier-3 LABEL-ONLY + dead-constant deletion + close retro**: Boundary /
  Geometry fallback counts → honest empty states; decorative flow overlays →
  示意 badges; DELETE the dead fake constants; live visual spot-check; retro.

## Out of scope

- New compute engines (DOE sweep, solver-host telemetry, temp probe) — those are
  separate builds; M5.5 makes their UIs honest, it doesn't build the backends.
- Physics advisor model/material lists — already formally deferred (M5.5 keeps
  them; they're advisory-labelled, not fabricated metrics). Re-examine post-M5.5.
- The compressible/CHT engine work (the user's cooled-blade target) — its own
  milestone, scoped in `2026-05-26_turbine_cascade_full_pipeline_dogfood.md`.

## Close criterion (passes:true iff ALL hold)

1. No construction step renders a fabricated numeric/verdict as if it were a real
   computed result: each is real run-derived OR an explicit 示意/无/功能开发中
   state. `grep` shows the Tier-1 literals/fallbacks gone or gated on real data.
2. Dead fake constants deleted (can't silently re-fake), per M5 pattern.
3. No regression: V4 vitest green; no crash when a case has no run/mesh.
4. Live visual spot-check (a real solved case + an unbuilt case) in the close retro.

## Four-question gate (V130)

- LLM offline? ✅ pure display of solve/mesh artifacts, no AI call in render.
- Artifacts canonical? ✅ the whole point — stop showing non-artifact fake data.
- TrustGate explainable? ✅ real provenance or explicit honest-state labels.
- AI advisory-only? ✅ read-only display; no AI action.

## Gating / rollback

C2 starts with this charter Accepted (now true) + parent DEC-V61-205 complete.
Cycles are sub-DECs / spike-class under this charter per v2.3. Charter-only DEC;
unwind = mark Status=Rejected/Superseded.

## Kogami

Not summoned (opt-in per v2.3). Low strategic risk — a continuation of the
established M5 truth-chain SSOT, no new direction. Invoke only if a de-fake turns
out to need a strategic call (e.g. "should DOE ship at all before the engine").
