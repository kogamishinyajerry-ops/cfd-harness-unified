---
retrospective_id: RETRO-V61-064
timestamp: 2026-04-26 local
scope: DEC-V61-064 NACA0012 kOmegaSSTSAS pimpleFoam transient architectural arc. Iteration ceiling 4/4 used at 1 (statistical-convergence ceiling judgment — first time used in the V61-058 → V61-064 series). Stage E iter1c (single sweep) produced Cl@α=8°=0.7057 — first non-zero HEADLINE progress since V61-061 baseline (+4.3 pp), but still 13.4% under Ladson 0.815. Closeout = architectural_ceiling_reached (with progress).
trigger: RETRO-V61-001 trigger #4 (iter ceiling-effective judgment + post-Stage-A live-run confirmation of mesh-vs-model ceiling for hybrid RANS-LES on RANS-resolved mesh)
predecessor_retros: [RETRO-V61-001 (governance), RETRO-V61-053 (post-R3 protocol), RETRO-V61-058 (V61-058 solver_stability), RETRO-V61-062 (architectural ceiling on C-grid), RETRO-V61-063 (transition-modeling ceiling + v2.2 amendments)]
status: LANDING — follows DEC-V61-064 close.
author: Claude Opus 4.7 (1M context, autonomous mode)
decided_by: Claude (self-executed under auto mode; Kogami sign-off at next session touch).
notion_sync_status: synced 2026-04-26 alongside DEC-V61-064 (https://www.notion.so/DEC-V61-064-NACA0012-kOmegaSSTSAS-transient-architectural_ceiling_reached-with-progress-34ec68942bed81d3b947de91844f8ef6)
---

# RETRO-V61-064 · Hybrid RANS-LES Ceiling on RANS-Resolved Mesh

## Purpose

V61-064 was the V61-063-followup SECONDARY recommendation: kOmegaSSTSAS scale-adaptive URAS on V61-061's H-grid. Pre-Stage-A self-review passed 7/7. Methodology v2.2 first-apply (post RETRO-V61-063 amendments). The arc had a 3-commit Stage A sub-arc with 2 runtime defects (delta keyword, *Final PIMPLE solvers) caught by Stage E smoke, then a single Stage E iter1c sweep that produced **the first non-zero HEADLINE progress since V61-061** (+4.3 pp Cl@α=8°). Closed at iter 1/4 via statistical-convergence judgment — a new ceiling-test pattern that complements RETRO-V61-063's 2-iter ceiling-test.

This retro extracts lessons from a 1-iter, partial-progress arc — the first DEC in the series with non-zero HEADLINE motion that nonetheless cannot pass the gate without a separate mesh redesign.

## Data · iteration progression

| Iter | Wall-clock | Δ from V61-061 baseline | Cl@α=8° outcome | Why this iter? |
|------|-----------|-------------------------|------------------|-----------------|
| Stage A.fix1 | minutes | added `delta cubeRootVol;` | n/a | Runtime fix #1 — SAS LES filter length scale required |
| Stage A.fix2 | minutes | added kFinal/omegaFinal solvers | n/a | Runtime fix #2 — PIMPLE nOuterCorrectors=2 invokes *Final |
| iter1c | 232 min | turbulence model kOmegaSST → kOmegaSSTSAS; solver simpleFoam → pimpleFoam transient; Tu_inf 0.5%; endTime=10s; 5-chord avg | 0.7057 (-13.4% vs gold; **+4.3 pp vs V61-061**) | Test PRIMARY hypothesis: unsteady-physics axis closes residual gap |

**Observation**: iter1c produced the most informative single iter in the V61-058 → V61-064 series. Statistical convergence at α=8° (cl_drift_pct_last_100 = 3.18%) with first non-zero progress (+4.3 pp) makes the answer decisive: SAS adds something on this mesh, but the mesh's RANS-resolution caps how much.

## Counter table

| DEC | Counter | autonomous_governance | external_gate_actual | Codex rounds |
|-----|---------|----------------------|---------------------|--------------|
| V61-062 | 44 | true | architectural_ceiling_reached (NaN at α=0) | 0 |
| V61-063 | 45 | true | architectural_ceiling_reached (Cl@α=8 unchanged) | 0 |
| **V61-064** | **46** | **true** | **architectural_ceiling_reached (with +4.3 pp progress)** | **0** |

Counter progression 45 → 46 (single-DEC increment). Per RETRO-V61-001 the counter is pure telemetry; no STOP signal triggered.

## Self-pass-rate calibration (continuing tightening trend)

| DEC | Pre-arc estimate | Actual outcome | Calibration delta |
|-----|------------------|----------------|-------------------|
| V61-058 | 0.40 | 0% | -40 pp |
| V61-061 | 0.55 | 0% | -55 pp |
| V61-062 | 0.30 | 0% | -30 pp |
| V61-063 | 0.20 | 0% | -20 pp |
| **V61-064** | **0.10** | **0%** | **-10 pp** |

V61-064's -10 pp delta is the smallest in the series. RETRO-V61-062 v2.1 amendment 4 + RETRO-V61-063 L4 (≤0.20 anchor for prior-ceiling geometry arcs) further calibrated: V61-064 at 0.10 was correct on the gate-pass dimension but UNDER-estimated the partial-progress dimension (+4.3 pp was the high end of the "small improvement" bucket, not the "no progress" bucket). **Recommendation**: keep ≤0.10-0.20 anchor for gate-pass estimate; track partial-progress estimate separately as a new pre-registered field.

## Lessons

### L1 — Statistical-convergence ceiling judgment is a third valid ceiling pattern

Methodology v2.0/v2.1/v2.2 had two ceiling patterns:
- **4-iter exhaustion** (V61-062): each iter genuinely tests a different sub-hypothesis
- **2-iter ceiling-test** (V61-063): iter1 + iter2 at opposite parameter bounds

V61-064 introduces a third:
- **1-iter statistical-convergence**: when iter1 produces statistically-converged forceCoeffs (cl_drift_pct_last_100 ≤ 5%) with a gap > 2× tolerance AND there is no opposite-bound parameter to test (the limiting axis is locked, e.g., mesh+model interaction with mesh held fixed by predecessor), declare ceiling at iter 1/4

V61-064's α=8° run: cl_drift = 3.18%, gap = 13.4% (~2.7× tolerance), opposite-bound = "redesigned LES mesh" which is OUT OF SCOPE per intake (deferred to V61-065). Iter2 with longer endTime cannot close a 13.4% gap when the time-mean has already settled.

**Actionable**: methodology v2.3 amendment — formalize the 1-iter statistical-convergence ceiling pattern. Pre-conditions: cl_drift_pct_last_100 ≤ 5%, gap ≥ 2× tolerance, locked-bound axis. If all three hold, iter ceiling = 1.

### L2 — First non-zero HEADLINE progress in the V61-061 → V61-064 series validates partial-axis activation

V61-064 broke the 0.677 plateau established by V61-061 + V61-063. The +4.3 pp is small but physically meaningful:
- Cl@α=8°: 0.677 → 0.706 (+4.3%)
- Cd@α=8°: 0.0376 → 0.0356 (-5.3%) — consistent with reduced over-turbulent BL dissipation
- Cd@α=0°: 0.0126 → 0.0126 (0%) — no detached/unsteady physics for SAS to feed on at zero incidence
- dCl/dα: 0.0844 → 0.0882 (+4.5%) — slope partially recovered

The signature is consistent with SAS partially activating in the trailing-edge separated region at α=8° (where there IS some unsteady physics) but degenerating to standard kOmegaSST elsewhere (because RANS-resolved mesh can't supply LES content). The model is doing what the textbook predicts — the question is whether 4.3 pp is the ceiling or whether finer mesh would unlock more.

**Actionable**: future intakes for hybrid RANS-LES arcs should pre-register the *expected* per-α partial-activation distribution. V61-064's intake §3 was correctly nuanced about the mesh-vs-model risk; the +4.3 pp result vindicates the SECONDARY-not-PRIMARY positioning vs full LES.

### L3 — OF10 dict-completeness defects are the dominant Stage A failure mode for transient model swaps

V61-064 Stage A had 2 runtime defects, both in the same class:
- 65fce0a: kOmegaSSTSAS requires `delta cubeRootVol;` (LES filter length scale) in turbulenceProperties RAS dict
- acba70e: PIMPLE nOuterCorrectors=2 invokes `*Final` solvers — kFinal + omegaFinal must be in fvSolution solvers block

Both are runtime-emergent (the OF10 dictionary parser surfaces them only at solver init). Static review (Codex or self-review) cannot catch these without a comprehensive checklist of every model's dict requirements — which is impractical for the dozens of OF10 turbulence models.

A 1-step `pimpleFoam` smoke run (deltaT=1e-6, endTime=1e-6, no real time evolution) would catch both defects in <30 seconds, avoiding the cost of two full-launch attempts.

**Actionable**: methodology v2.3 amendment — Stage A protocol for transient model swaps must include a 1-step canary run before Stage E launch. Implement as a `--canary` flag on the live-run driver that exits after `Time = 0` is logged.

### L4 — Codex-absent autonomous mode continues to be correctly calibrated for runtime-emergent defect classes

V61-064 ran with 0 Codex rounds and self-review 7/7. The intake correctly identified all the high-level risk flags (`hybrid_rans_les_on_rans_resolved_mesh`, `transient_simulation_first_application`, `solver_stability_on_novel_geometry`). The 2 OF10 dict-completeness defects were caught by Stage E smoke, exactly as RETRO-V61-053 protocol expects (post-R3 = post-static-review live-run defects).

Codex would not have caught these defects either: the closest reference would be the OF10 source tree at `/opt/openfoam10/src/MomentumTransportModels/momentumTransportModels/RAS/kOmegaSSTSAS`, but Codex doesn't have read access to that path in the harness's review context.

**Actionable**: continue autonomous mode for architectural arcs. The 1-step canary protocol (L3) is the methodology-level fix; Codex involvement does not address this defect class.

### L5 — V61-061 H-grid is now the validated "RANS plateau" baseline; further RANS work on this mesh is bounded

V61-058 → V61-064 progression establishes V61-061's 96k H-grid as the RANS plateau:
- V61-061 baseline (kOmegaSST steady): 0.677
- V61-063 (kOmegaSSTLM steady): 0.6763 (no movement)
- V61-064 (kOmegaSSTSAS pimpleFoam transient): 0.7057 (+4.3 pp partial activation)

The +4.3 pp partial activation suggests this mesh has ~5 pp of remaining RANS-class headroom — accessible only via hybrid models that exploit detached regions. Further attempts (DDES, SBES, IDDES) would likely produce 3-5 pp more, all of which combined cannot close the 13.4% gap.

**Actionable**: methodology v2.3 amendment — register `v61_061_h_grid_rans_plateau` as a known-bound: any future ARC on this mesh with a RANS-class or hybrid-RANS-LES model has expected gate-pass probability ≤ 0.05. Skip such arcs unless they test a fundamentally different physics axis (which they don't — V61-064 is the last one before LES territory).

## Codex economics

| | V61-058 | V61-061 | V61-062 | V61-063 | V61-064 |
|---|---|---|---|---|---|
| Codex rounds | 3 | 0 | 0 | 0 | **0** |
| Self-pass-rate | 0.40 | 0.55 | 0.30 | 0.20 | **0.10** |
| Codex required pre-merge per RETRO-V61-001? | yes (F1 ruling) | no | no | no | **no** |
| Outcome | gate failed | gate failed | gate failed (NaN) | gate failed (no movement) | **gate failed (+4.3 pp partial progress)** |

V61-064 reinforces the V61-061→V61-063 finding: for autonomous architectural arcs on prior-ceiling geometries, Codex contributes zero to the gate outcome. The 2 runtime defects at Stage A would not have been caught by static review (Codex would have approved both Stage A attempts as correct, single-axis turbulence-model swaps with proper dispatch routing). They were caught by the live-run smoke (the methodology v2.0 protocol working as designed). Total token cost for V61-064 = 0 Codex tokens (vs V61-058's 3 Codex rounds = ~250k tokens).

## Open questions

1. **Does the ≤0.10 anchor stay or move?** V61-064 -10 pp delta is the smallest in the series. If V61-065 LES (full LES on a redesigned mesh) produces 0-5 pp delta, the anchor could float to 0.05. But until then, 0.10 is the anchor for prior-ceiling-with-partial-progress arcs.

2. **Is V61-065 LES the right next step, or should NACA0012 be parked?** V61-064's +4.3 pp progress signals there IS more physics to capture if the mesh allows. V61-065 LES with a wall-resolved mesh (target 500k-1M cells, y+_max ≤ 1) is the natural test. Cost estimate: 100-150 wall-clock hours per α — exits the autonomous-overnight regime. **Recommendation**: V61-065 should proceed but as a deliberate, planned arc (not autonomous overnight), and only after Kogami sign-off on the compute budget.

3. **Should the gold reference be challenged?** Ladson 1988 NASA TM-4074 reports ±5% measurement uncertainty. V61-064 closing at -13.4% is still ~2.7× the declared uncertainty, so the gold cannot be challenged on uncertainty grounds alone. **Recommendation**: do not challenge the gold; run V61-065 LES first. If LES also fails to close the gap, then propose a gold-uncertainty audit DEC.

## Recommendations to V61-065 (proposed)

Per intake §11 ceiling protocol:

1. **PRIMARY**: Wall-resolved LES (WALE or k-equation SGS) on a *redesigned* mesh
   - Target: y+_max ≤ 1 in BL (vs V61-061's y+~30); dx⁺/dz⁺ ~ 50/15; chord-direction 200-400 cells
   - Mesh size: 500k-1M cells (vs V61-061's 96k); spanwise extent ≥ 0.1c with periodic BCs
   - Transient pimpleFoam (already wired by V61-064)
   - Time-averaged forceCoeffs over ~10 chord-flow-throughs after 5-chord initial transient
   - Compute cost: ~30-50× V61-064 SAS per α (estimate: 100-150h per α, 300-450h per 3-α sweep)
   - Risk: this exits the autonomous-overnight regime; needs deliberate planning (chunked overnight runs or distributed cluster execution); **must have Kogami sign-off before launch**

2. **DEPRECATED**:
   - Further hybrid RANS-LES variants (DDES, SBES, IDDES) on V61-061 H-grid (V61-064 evidence: 4.3 pp partial activation is the bound; further hybrid models will produce ≤5 pp more, not enough to close 13.4%)
   - Pure LES on V61-061 H-grid (96k is RANS-resolved; LES would be ill-posed)
   - Mesh refinement on H-grid > 96k cells with steady RANS (V61-061 plateau evidence)
   - C-grid + any model (V61-062 + V61-063 jointly: topology not the limiter)
   - Tu_inf or other parametric sweeps on existing models (V61-063 sweep null; V61-064 mesh-bounded)

V61-065 intake should explicitly cite this DEC + retro as the source of the recommendation pruning, AND must include compute-budget justification (this is the first arc in the V61-061 → V61-065 series that requires conscious resource commitment beyond the autonomous-overnight envelope).

## Methodology v2.3 amendments (proposed)

Based on lessons L1–L5:
1. **Add "1-iter statistical-convergence ceiling pattern"**: pre-conditions = cl_drift_pct_last_100 ≤ 5%, gap ≥ 2× tolerance, locked-bound axis. Iter ceiling = 1. (L1)
2. **Pre-register expected per-α partial-activation distribution** for hybrid-RANS-LES arcs (intake §3): track the partial-progress dimension separately from gate-pass dimension. (L2)
3. **Stage A 1-step canary protocol for transient model swaps**: add `--canary` flag to live-run driver that exits after `Time = 0` is logged. Catches OF10 dict-completeness defects in <30 seconds. (L3)
4. **Continue ≤0.10-0.20 anchor for prior-ceiling geometry arcs**: V61-064 -10 pp delta validates the tightest anchor. (L4 / RETRO-V61-063 L4 confirmed and tightened)
5. **Register `v61_061_h_grid_rans_plateau`**: any future ARC on this mesh with a RANS-class or hybrid-RANS-LES model has expected gate-pass probability ≤ 0.05. Skip such arcs unless they test a fundamentally different physics axis. (L5)

These amendments roll into v2.3 with V61-065 LES (if launched) as the first-apply.
