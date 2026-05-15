# case_024 v2 · Lid-Driven Cavity Re=1000 · Stretched 257×257 Grid

**Sub-DEC**: `DEC-V64-A-sub-M-V64A-VAL-FULL-CAVITY-V2`
**Parent DEC**: `DEC-V64-A-charter`
**Predecessor**: `DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY` (B65 PARTIAL strong · 2026-05-15)
**Date**: 2026-05-15
**Author**: Claude Opus 4.7 autonomous engineering session

---

## §1 Scope

Single-Re focused attack on the **Re=1000 v-centerline 4-point band** failure mode identified in B65:

| Quantity | B65 (uniform 129×129) | v2 target |
|---|---|---|
| Cells | 16,641 | 65,536 (4×) |
| Wall-cell Δx | 0.00775 m (uniform) | 0.00157 m (5× finer) |
| Center-cell Δx | 0.00775 m | 0.00784 m |
| Grading | none (simpleGrading (1 1 1)) | double-sided 5:1 at both x-walls AND y-walls |
| Re=1000 u-centerline strict-PASS | 17/17 ✓ MET | retain 17/17 |
| Re=1000 v-centerline strict-PASS | **13/17 (max Δ 4.10% @ x/L=0.9688)** | **17/17 target** |
| Residuals 4/4 < 1e-7 | ✓ MET (B65) | retain ✓ |
| Strict gate (3% AND 3% AND 1e-7) | **fail by 1.10 pp** | **MET → push Done #1 0/3 → 1/3** |

Only Re=1000 (not Re=100, Re=400) — single-Re focused attack per user Path A ratification.

## §2 Mesh design rationale

B65 failure mode 3 (validation report §1, failure mode 3): "Re=1000 v-centerline 4-point band (x/L ≥ 0.9531): max 4.10% @ x/L=0.9688, near the right-wall steep-gradient region where 129×129 uniform grid is at the edge of resolving the descending wall jet."

**Diagnosis**: with uniform Δx=0.00775, the cell-centroid nearest x=1 sits at x≈0.9961 (single wall cell of width 0.00775). Sampling Ghia's x/L=0.9688 requires interpolation across 4 cells (x ∈ [0.9612, 0.9844]) where the v-velocity descends from ~−0.215 toward 0 at the wall. Linear interpolation across a coarse grid in this steep-gradient region under-resolves the local extremum.

**v2 fix**: double-sided clustering with simpleGrading multi-grading:

```
simpleGrading
(
    ((0.5 128 5)(0.5 128 0.2))   x: clustered at x=0 AND x=1
    ((0.5 128 5)(0.5 128 0.2))   y: clustered at y=0 AND y=1 (lid)
    1
)
```

Cell-size analytical estimate (geometric progression, half-block):
- q = 5^(1/127) ≈ 1.01275 (cell-to-cell ratio)
- a_1 = 0.5 / (q^128 − 1)/(q − 1) = 0.5 / 318.6 ≈ 0.001569 m (wall cell)
- a_128 = a_1 · 5 ≈ 0.007844 m (center cell)

This places **~5 cells in x ∈ [0.95, 1.0]** (B65 had ~1 cell), matching the typical "y+ ~1 first-cell" RANS heuristic translated to laminar gradient resolution.

## §3 Boundary conditions / solver (identical to B65)

- 0/U: lid `fixedValue (1 0 0)`, walls_fixed `noSlip`, frontAndBack `empty`
- 0/p: zeroGradient on all walls, `pRefCell 0; pRefValue 0;` in fvSolution
- constant/transportProperties: `Newtonian; nu 0.001;` (Re=1000 with U_lid=1, L=1)
- constant/turbulenceProperties: `simulationType laminar`
- system/fvSchemes: `ddtSchemes steadyState`, `bounded Gauss linearUpwindV grad(U)`, `cellLimited Gauss linear 1` for grad(U), `Gauss linear corrected` laplacian
- system/fvSolution: GAMG p (1e-9 tol, 0.01 relTol) + PBiCGStab U (1e-9 tol, 0.1 relTol); URF 0.30/0.70; residualControl 1e-7 strict
- system/controlDict: endTime 20000 (B65 used 10000; v2 widened headroom for stretched grid convergence), purgeWrite 2, writeInterval 5000

## §4 4Q gate compliance

- **Q1 LLM-offline**: `bash scripts/v64_v2_run_solver.sh` runnable under `env -i HOME PATH .venv/bin/python`; no LLM dependency at runtime
- **Q2 artifacts**: blockMeshDict + 0/{U,p} + constant/{transportProperties, turbulenceProperties} + system/{controlDict, fvSchemes, fvSolution, sampleDict} + BLOCKMESH_LOG + CHECKMESH_LOG + SIMPLEFOAM_LOG + CONVERGENCE_TRACE + results/centerline_Re1000_{u,v}.csv + results/summary.json + sub-DEC + validation report
- **Q3 TrustGate**: every Δ value cites postProcessing/sampleDict/<latest>/u_vertical_centerline_U.xy or v_horizontal_centerline_U.xy row + Ghia 1982 Table I (page 396) or Table II (page 397)
- **Q4 advisor-only**: zero edits to `ui/backend/` or any advisor stack file

## §5 Reverse condition (failure-recording authorization)

Per briefing:
- v-centerline 17/17 strict-PASS max < 3% AND u 17/17 PASS AND residuals 4/4 < 1e-7 → **FULL**
- v-centerline 17/17 PASS but max ∈ [3%, 3.5%] → **marginal strict** (document promote rationale)
- v-centerline 16/17 PASS OR max ∈ [3%, 4%] → **marginal** (user裁决 promote OR PARTIAL)
- setup fail / mesh fail / divergence → **PARTIAL v2** (document root cause)

Honesty over arc inflation: PARTIAL keeps Done #1 at 0/3, FULL advances to 1/3 strict ✓.
