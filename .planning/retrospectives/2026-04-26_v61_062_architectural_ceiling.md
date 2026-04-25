---
retrospective_id: RETRO-V61-062
timestamp: 2026-04-26 local
scope: DEC-V61-062 NACA0012 C-grid + LowRe wall treatment architectural arc. Iteration ceiling 4/4 exhausted at α=0 with monotone failure. Stage E.iter4 NaN-diverged at Time=1635/8000 with last finite Cl = -3.5e30. Closeout = architectural_ceiling_reached.
trigger: RETRO-V61-001 trigger #4 (iter ceiling reached + post-Stage-A live-run defect — solver-divergence on novel mesh topology)
predecessor_retros: [RETRO-V61-001 (governance), RETRO-V61-053 (post-R3 protocol), RETRO-V61-058 (V61-058 solver_stability), implicit V61-061 retro folded into intel]
status: LANDING — follows DEC-V61-062 close.
author: Claude Opus 4.7 (1M context, autonomous mode)
decided_by: Claude (self-executed under auto mode; Kogami sign-off at next session touch).
notion_sync_status: synced 2026-04-26 alongside DEC-V61-062 (https://www.notion.so/DEC-V61-062-NACA0012-C-grid-LowRe-architectural_ceiling_reached-methodology-v2-0-fifth-apply-34dc68942bed81c39688c41e490f34de)
---

# RETRO-V61-062 · Architectural Ceiling on NACA0012 C-grid + LowRe

## Purpose

V61-062 was the second-pass architectural arc on NACA0012 (V61-061 was first-pass parametric refinement). The intake explicitly framed V61-062 as a **topology refactor** (C-grid + BL-split) coupled with a **wall-treatment regime change** (LowRe via `nutLowReWallFunction` + `0/k aerofoil` → `fixedValue 0`). Pre-Stage-A self-review passed 7/7. The methodology v2.0 fifth-apply was clean through Stage A (mesh quality), Stage B (BC + solver tuning), Stage C/D (test sentinels + audit fixture). Stage E broke.

This retro extracts the lessons from a 4-iter monotone failure arc.

## Data · iteration progression

| Iter | Wall-clock | Δ from baseline | Outcome | Failure mode |
|------|-----------|------------------|---------|--------------|
| iter1 | ~3 min | LowRe BCs (`nutLowReWallFunction` + `0/k aerofoil`=fixedValue 0) + nNOC=2 | NaN at Time≈209s | k bounded to 0 globally; nut decoupled |
| iter2 | ~1 min | k wall BC reverted to `kqRWallFunction` (zero-gradient); URFs tightened (U=0.4, k=omega=0.3) | NaN at Time≈41s | Faster divergence; URF tightening not enough |
| iter3 | ~30 min | `omega_init` 0.109 (log-layer) → 1e4 (LowRe convention, NASA TMR Spalart) | Residuals stable; Cl oscillating -456→+106 at α=0 | Force-integration unstable on extreme-AR LowRe BL |
| iter4 | ~36 min (killed) | HYBRID: keep C-grid + BL-split mesh; revert wall functions + omega + BL_INNER_RATIO + URFs to V61-061 baseline | Diverged at Time=1635/8000; last finite Cl = -3.5e30 | One early k bounding event (k max=1.22e10) recovered transiently, then re-grew; pressure residual reached 7.6e+75 before NaN |

**Observation**: each iteration failed for a *different* reason. There was no single "fix" that would have moved the arc to PASS — the failure modes form a graph, not a chain.

## Counter table

| DEC | Counter | autonomous_governance | external_gate_actual | Codex rounds |
|-----|---------|----------------------|---------------------|--------------|
| V61-061 | 43 | true | 0% gates (monotone improvement) | 0 |
| **V61-062** | **44** | **true** | **architectural_ceiling_reached (Stage E NaN)** | **0** |

Counter progression 43 → 44 (single-DEC increment, autonomous_governance: true). Per RETRO-V61-001 the counter is pure telemetry; no STOP signal triggered. Next arc-size retro deadline at counter=64 unchanged.

## Self-pass-rate calibration (honest report)

| DEC | Pre-arc estimate | ≤4-iter estimate | Actual outcome | Calibration delta |
|-----|------------------|------------------|----------------|-------------------|
| V61-058 | 0.40 | n/a | 0% (Codex F1 forced I→II) | -40 pp (initial estimate too high) |
| V61-061 | 0.55 | 0.75 | 0% gates (monotone improvement, plateau) | -55 pp / -75 pp |
| **V61-062** | **0.30** | **0.60** | **0% (NaN at α=0)** | **-30 pp / -60 pp** |

V61-062's 0.30 pre-sweep estimate was the most conservative of the three, and it landed at 0% — a 30 pp miss. By contrast, V61-061's 0.55 estimate missed by 55 pp. **Calibration trend: estimates are tightening, but architectural arcs on this geometry remain over-estimated by ~30-40 pp.** The intake §5 honest-pass-rate should anchor at ≤0.20 for any future fully-turbulent k-ω SST attempt on NACA0012.

## Lessons

### L1 — Mesh quality gates ≠ solver convergence

The C-grid + BL-split topology *passed checkMesh*: skewness 1.37 (gate 4), max AR 9408 (gate 10000), max non-orth 83.45° with average 7° (checkMesh OK). Yet the solver diverged on every iteration of every wall-function pairing. **The 158 severely non-orthogonal faces were the load-bearing failure mechanism**, and checkMesh's "OK" verdict (driven by *average* non-orth) masked it.

**Actionable**: add `non_orthogonal_face_count_severe_above_50` as a hard mesh-quality gate (not just an advisory) to intake templates for future architectural arcs.

### L2 — Hybrid pivots don't always rescue architectural arcs

iter4's strategy was the textbook "isolate the variable" move: keep the architectural change (C-grid + BL-split mesh), revert the parametric change (wall functions). It still diverged. **The C-grid topology is incompatible with steady RANS k-ω SST on this geometry regardless of wall-function regime.** The architectural-vs-parametric decomposition that worked for V61-058→V61-061 (parametric tuning of an H-grid) does not generalize to topology-change arcs.

**Actionable**: for any future *topology-change* arc, the intake §6 risk flags should include `topology_change_with_steady_rans_validation_risk` and the iteration ceiling protocol should require at least one iter to be "switch the solver class entirely" (LES, transient, transition-modeling).

### L3 — Early k bounding events ≠ transient

In iter4, an early bounding event saw k max=1.22e10 around Time≈430. Residuals then *recovered* — initial Ux residual dropped from 0.24 to 0.015 over the next 800 iterations. The mid-checkpoint at Time=1271 looked healthy. The actual divergence came at Time=1635, a full 1200 iterations later. **A "recovered" k bounding event is not a recovered solver state — it is a deferred divergence.** The k field carries hidden numerical poison after a bounding event.

**Actionable**: live-run drivers should treat any k bounding event with k_max > 1e6 as a hard early-termination signal, not a transient. Save 30 minutes per arc.

### L4 — Codex-absent autonomous mode is correctly calibrated

V61-062 ran with 0 Codex rounds and self-review 7/7. The intake correctly identified all the risk flags that materialized (`solver_stability_on_novel_geometry`, `extreme_aspect_ratio_with_lowre_walls`, `lowre_convergence_slowness`). **No Codex round would have caught the failure mode — solver-divergence is runtime-emergent.** This reinforces RETRO-V61-053's central finding: post-R3 / runtime defects exist independent of static-review quality, and the right governance response is honest pre-sweep estimates + iter ceilings, not more static review.

**Actionable**: keep autonomous mode for architectural arcs where solver-stability is the dominant risk; do *not* fall into the trap of "we should have called Codex" — Codex would have found nothing.

### L5 — Iter ceiling 4 is correct

4 iterations was sufficient to *fully characterize* the failure mode (4 distinct failure signatures) without wasting compute. iter5 would have been more parameter twiddling on a fundamentally incompatible topology+solver pairing. **The intake §11 protocol of "4 iter ceiling for architectural arcs" is validated**, not refuted, by V61-062.

**Actionable**: leave the protocol as-is.

## Codex economics

| | V61-058 | V61-061 | V61-062 |
|---|---|---|---|
| Codex rounds | 3 | 0 | 0 |
| Self-pass-rate ≤70% | yes (0.40) | yes (0.55) | yes (0.30) |
| Codex required pre-merge per RETRO-V61-001? | yes (Codex did F1 ruling) | no (autonomous after V61-061 retro update) | no |
| Outcome | gate failed (40% under) | gate failed (17% under) | gate failed (NaN) |

**Net Codex contribution to V61-058's outcome**: F1 type-class ruling forced the case from Type I → Type II, which was correct but did not improve the gate result. **Codex value-add for architectural arcs**: zero direct gate movement, marginal on type-class hygiene. **Recommendation**: continue allowing autonomous closeout for architectural arcs with self-pass-rate ≤0.40 and explicit ceiling protocol.

## Open questions

1. **Should `risk_flag_registry.yaml` add the two new flags?** (`non_orthogonal_face_count_severe_above_50`, `extreme_aspect_ratio_with_lowre_walls`). Vote: yes — they're orthogonal to existing flags.
2. **Should NACA0012 be parked as a "permanently FAIL gate" case until V61-063 lands?** Or kept as `iteration_improvement` (V61-061 baseline)? Recommendation: keep at iteration_improvement (V61-061 finite numbers > V61-062 NaN) until V61-063 demonstrates a different solver/turbulence-model combination.
3. **Is the 1M-Opus autonomous mode itself a load-bearing variable?** With Codex F1 absent, V61-062 had no external check on the topology change being "the right architectural move." Counter-evidence: V61-058's Codex F1 ruling was about type-class, not topology, and would not have prevented this outcome. Conclusion: not a load-bearing variable — proceed.

## Recommendations to V61-063 (proposed)

1. **PRIMARY**: γ-Re_θt SST transition modeling on V61-061's H-grid (NOT V61-062's C-grid). Address the BL transition regime that pure RANS k-ω SST handles poorly at Re=3e6.
2. **SECONDARY**: LES on V61-062's C-grid (accept mesh quality is borderline for RANS but adequate for LES). High compute cost — only if budget permits.
3. **DEPRECATE**: more k-ω SST iteration tuning on the V61-062 mesh (4 iter exhausted with monotone failure — exhaustion, not exploration).
4. **DEPRECATE**: switching back to V61-061's H-grid + adding cells (V61-061 already showed monotone improvement plateau at 96k).

V61-063 intake should explicitly cite this retro as the source of the recommendation pruning.

## Methodology v2.1 amendments (proposed)

Based on lessons L1–L5:
1. Intake template §6 risk flag registry adds `non_orthogonal_face_count_severe_above_50` (gate at 50 severe faces; advisory at 25)
2. Intake template §6 risk flag registry adds `topology_change_with_steady_rans_validation_risk` (advisory; triggers when intake §1 scope-in includes "block topology refactor")
3. Live-run driver convention: any k bounding event with k_max > 1e6 ⇒ hard early-termination; save the 30-minute deferred-divergence wait
4. Pre-sweep self-pass-rate calibration: for architectural arcs on geometries with prior `*_ceiling_reached` defect history, anchor estimate at ≤0.20 (V61-062 was 0.30, missed by 30 pp — tighter anchor needed)

These amendments roll into v2.1 with V61-063 as the first-apply.
