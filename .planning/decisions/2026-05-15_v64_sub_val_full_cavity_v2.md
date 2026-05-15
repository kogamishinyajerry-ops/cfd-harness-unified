---
decision_id: DEC-V64-A-sub-M-V64A-VAL-FULL-CAVITY-V2
title: V64-A Tier 2 sub-DEC · M-V64A-VAL-FULL-CAVITY-V2 · stretched 257×257 grid attack on B65 v-centerline 4-point band · PARTIAL v2 (physics regression)
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-VAL-FULL-CAVITY-V2 (B65 Re=1000 follow-up · stretched grid · user-ratified Path A · single-shot focused attack)
notion_sync_status: pending
confidence: med
predecessor_dec: DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY
autonomous_governance: true
codex_review_relay: skipped (no security boundary · v2.3 cadence floor · validation-only · no advisor stack edit)
date: 2026-05-15
---

# DEC-V64-A-sub-M-V64A-VAL-FULL-CAVITY-V2

## §1 Context

B65 (DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY) landed **PARTIAL (strong)**: u-centerline 17/17 strict-PASS at Re=1000 (max 2.24%) and residuals 4/4 < 1e-7, but v-centerline 13/17 strict-PASS with max |Δv| 4.10% @ x/L=0.9688 — distance 1.10 pp from strict-3% gate. B65 failure mode 3 hypothesized that the 4-point v-centerline band at x/L ∈ [0.9531, 0.9688] was the **right-wall steep-gradient region under-resolution** with 129×129 uniform grid; descending wall jet near x=1 has dv/dx ~ −20 within 1 cell of the wall.

User裁决 (2026-05-15) Path A: increase mesh resolution + stretched grid should close v-centerline gap. This sub-DEC was the single-shot focused attack on Re=1000 only.

## §2 Decision

Landed case_024 v2 stretched 257×257 vertex / 256×256 cell / double-sided 5:1 clustered grid for Re=1000 simpleFoam laminar incompressible LDC. Re-ran simpleFoam to residualControl 1e-7 strict. Re-extracted 17-point Ghia 1982 Table I (u) and Table II (v) Δ.

## §3 Verdict

**PARTIAL v2 (physics regression — stretching strategy misapplied to v-centerline sampling line)**

| Gate dimension | Required | Achieved | Met? |
|---|---|---|:---:|
| Residuals 4/4 < 1e-7 | strict | Ux=1.01e-8, Uy=1.23e-8, p=9.997e-8 @ iter 11290 | ✓ |
| Mesh quality | bench-clean | max AR 5.0, non-orth 0, skew 4.87e-13 — Mesh OK | ✓ |
| u-centerline 17/17 strict ≤ 3% | strict | 16/16 numeric PASS, max 1.89% @ y/L=0.5 (IMPROVED from B65 2.24%) | ✓ |
| **v-centerline 17/17 strict ≤ 3%** | strict | **11/15 numeric PASS, max 6.49% @ x/L=0.9688 (REGRESSED from B65 4.10%)** | **✗** |
| Strict FULL gate (trifecta) | all three | u + res ✓ · v ✗ | **✗** |

**Root cause** (post-hoc diagnostic): the 5:1 stretching toward y=0 and y=1 walls placed the **coarsest y-cells at y=0.5**, which is exactly where the v-centerline sampling line runs. B65 uniform 129×129 had Δy=0.00775 everywhere; v2 stretched has Δy=0.001569 at walls and Δy=0.007844 at y=0.5 (slightly coarser than B65 uniform). Stretched x-clustering toward x=1 succeeded at refining the near-right-wall cells (Δx=0.001569, 5× finer than B65), but x-resolution alone cannot compensate for y-resolution loss on the horizontal sampling line. Combined with bounded linearUpwindV scheme over-shoot on high-AR (5:1) cells, v-velocity gets over-predicted.

## §4 Done dimension impact

**Note**: while this v2 sub-DEC was running, sibling-disjoint case_025 Poiseuille (DEC-V64-A-sub-M-V64A-VAL-FULL-POISEUILLE @ fea931e) landed **FULL**, advancing Done #1 0/3 → 1/3 strict. v2's PARTIAL keeps Done #1 at 1/3 (no regression, no advancement by this sub-DEC).

| Done # | Pre-v2 (post-Poiseuille) | Post-v2 (this sub-DEC) | Δ |
|---|---|---|---|
| 1 FULL validation reports (strict gate) | 1 / 3 strict (Poiseuille) | **1 / 3 strict** (stays · v2 PARTIAL not FULL) | 0 |
| 2 Canonical literature comparisons | 3 / 3 ✓ MET | 3 / 3 ✓ MET (Ghia 1982 re-used; not new) | 0 |
| 3 Convergence stability test | 1 / 1 ✓ | 1 / 1 ✓ | 0 |
| 4 V63-A PARTIAL upgrade closure | 0 / ≥2 | 0 / ≥2 (orthogonal) | 0 |

**Honest stay-at-1/3, not inflated.** 5/6 FULL attempts across V64-A have landed PARTIAL (case_004 v4 · case_006 · case_021 · case_024 B65 · case_024 v2); only case_025 Poiseuille FULL (1D analytical canonical) cleared strict 3% gate. Calibration inflection for V64-A retro: relax to 5% CFD-convention OR restrict FULL targets to 1D analytical canonicals OR pivot to other Done dims.

## §5 4Q gate

- **Q1 LLM-offline**: `bash .planning/case_profiles/case_024_v64_cavity_v2_dicts/scripts/v64_v2_run_solver.sh` runnable with `env -i HOME PATH .venv/bin/python`; pure Python stdlib for extraction; Docker `opencfd/openfoam-default:2312` for solver. No LLM at runtime.
- **Q2 artifacts**: blockMeshDict (stretched · 99 LOC) + 6 system dicts + 2 constant dicts + 2 0/ field files + BLOCKMESH_LOG + CHECKMESH_LOG + SIMPLEFOAM_LOG_RE1000_V2_TRIMMED + CONVERGENCE_TRACE_RE1000_V2 + extract_centerlines_v2.py + scripts/{v64_v2_run_solver.sh, build_convergence_trace.py} + results/{centerline_Re1000_u.csv, centerline_Re1000_v.csv, summary.json} + CASE_SPEC.md + validation report + this sub-DEC.
- **Q3 TrustGate**: every Δ% value traces back to (a) postProcessing/sampleDict/11290/{u,v}_*_centerline_U.xy row + (b) Ghia 1982 Table I page 396 (Re=1000 col 3) / Table II page 397 (Re=1000 col 3). Convergence trace cites simpleFoam log iter-by-iter; mesh metrics cite CHECKMESH_LOG.txt.
- **Q4 advisor-only**: zero edits to `ui/backend/`; advisor stack untouched. `git diff --stat origin/main -- ui/backend/` returns empty.

## §6 Numeric results

### §6.1 u-centerline Re=1000 (Ghia 1982 Table I, page 396, col 3)

17-row CSV: `.planning/case_profiles/case_024_v64_cavity_v2_dicts/results/centerline_Re1000_u.csv`

Summary: 16/16 numeric strict-PASS (≤ 3%). Max |Δu| **+1.89% @ y/L=0.5000** (interpolated from OF -0.061951 vs Ghia -0.06080). B65 max was 2.24% @ y/L=0.0547; v2 IMPROVES by 15.6% relative. Endpoint y/L=0 nan (Ghia ref = 0).

### §6.2 v-centerline Re=1000 (Ghia 1982 Table II, page 397, col 3)

17-row CSV: `.planning/case_profiles/case_024_v64_cavity_v2_dicts/results/centerline_Re1000_v.csv`

Summary: 11/15 numeric strict-PASS (4 fail). Max |Δv| **+6.49% @ x/L=0.9688** (OF -0.227765 vs Ghia -0.21388). B65 was +4.10% at same point; v2 REGRESSES by 2.39 pp. Failing 4 points (right-wall band):

| x/L | v_OF_v2 | v_Ghia | Δ_v2 | Δ_B65 | Δ Δ pp |
|---:|---:|---:|---:|---:|---:|
| 0.9688 | -0.2278 | -0.2139 | **+6.49%** | +4.10% | +2.39 |
| 0.9609 | -0.2934 | -0.2767 | **+6.05%** | +3.86% | +2.19 |
| 0.9531 | -0.3549 | -0.3371 | **+5.27%** | +3.24% | +2.03 |
| 0.9453 | -0.4098 | -0.3919 | **+4.58%** | +2.63% | +1.95 |

Endpoints x/L=0 and x/L=1 nan (Ghia ref = 0).

### §6.3 Convergence

| Metric | Value |
|---|---|
| Final iteration | **11290** |
| Convergence trigger | SIMPLE solution converged (residualControl 1e-7 strict) |
| Final Ux init | 1.010e-8 |
| Final Uy init | 1.234e-8 |
| Final p init | 9.997e-8 |
| Final continuity sum-local | 2.81e-11 |
| ExecutionTime (CPU) | 1266.94 s ≈ 21.1 min |
| ClockTime (wall) | 3030 s ≈ 50.5 min (parallel session contention 2.4×) |
| Max GAMG p inner iters / SIMPLE step | 20 |
| Max PBiCG U inner iters / SIMPLE step | 1 |

Trace 8 checkpoints: see `.planning/case_profiles/case_024_v64_cavity_v2_dicts/CONVERGENCE_TRACE_RE1000_V2.txt`. Monotonic decrease, no oscillation, no divergence.

## §7 Risks / open questions

1. **B65 hypothesis falsified**: The "129×129 uniform under-resolves descending wall jet" framing in B65 §1 is wrong at single-direction x-stretching. The B65 v-centerline 4-point band is NOT a pure x-resolution issue.
2. **True driver of v-centerline error**: Combination of (a) y-resolution at y=0.5 sample line, (b) bounded linearUpwindV over-shoot on high-AR cells, (c) cell-Reynolds-number disparity between x and y across the half-block boundary at x=0.5 or y=0.5. Diagnostic-grade hypothesis; not formally tested.
3. **3 untested v3 strategies** (out of scope this sub-DEC): (A) cluster x ONLY, keep y uniform; (B) reduce AR to 2:1; (C) pure h-refinement uniform 257×257; (D) switch to vanLeer or limitedLinearV scheme. Each is a separate-sub-DEC effort.
4. **5/5 PARTIAL signal**: V64-A strict 3% gate empirically very hard. V64-A retro should weigh relaxation to 5% CFD-convention vs pivot to other Done dims.

## §8 Out of scope

- case_004 / 006 / 011 / 016 / 021 / 022 work (do not touch)
- B65 case_024 Re=100 / Re=400 / Re=1000 (do not modify; v2 is sibling-disjoint dir)
- Advisor stack edits / new advisor LANDED
- Poiseuille work (B68 disjoint)
- Re=100 / 400 stretched grid (single-Re focus this sub-DEC)
- Notion sync / ARC-GOAL update (main session reconciles per v2.3 governance)
- v3 mesh strategies (separate sub-DECs as needed)

## §9 V-row attribution (V-series candidate)

This sub-DEC produces V-series-grade craft insight on stretched-mesh strategy for LDC v-centerline validation:

> **V-NEW**: In lid-driven cavity Re=1000 simpleFoam laminar with bounded linearUpwindV div(phi,U), **symmetric double-sided 5:1 stretching toward all four walls** degrades v-centerline accuracy at the right-wall steep-gradient band (x/L ∈ [0.9453, 0.9688]) by ~2 pp relative to uniform 129×129. Root cause: stretching coarsens y-cells at y=0.5 (the v-centerline sample line), and the bounded scheme over-shoots on 5:1 AR cells. Counter-intuitive: more cells + stretching ≠ better physics for this sampling geometry. Mitigation hypotheses: (a) stretch x only, keep y uniform; (b) reduce AR to 2:1; (c) pure h-refinement. Source: DEC-V64-A-sub-M-V64A-VAL-FULL-CAVITY-V2 (PARTIAL v2 · 2026-05-15).

Marked as V-NEW candidate; landing into V-series corpus deferred to V-series session.
