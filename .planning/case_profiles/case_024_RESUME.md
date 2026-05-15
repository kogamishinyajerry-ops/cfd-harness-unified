# case_024 · RESUME

**Case**: Lid-Driven Cavity · Ghia 1982 canonical · 3 Re query points (100/400/1000)
**Started**: 2026-05-15 (V64-A B65 dispatch)
**Status**: substrate prep landed (commit 1 of 5)
**Parent DEC**: DEC-V64-A-charter
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-4-CAVITY (in flight)

## North Star (one line)

> 用 simplest possible canonical (lid-driven cavity · laminar simpleFoam · Ghia 1982 Re=100/400/1000 reference · 17 u/v centerline points each) 把 V64-A Done #1 推到 1/3 strict FULL. Every complexity layer stripped: no turbulence model, no transition, no shock, no rotation, no STL, no heat — just the CFD textbook example.

## Canonical reference

- Primary: Ghia, Ghia & Shin (1982) JCP 48:387-411 Tables I & II (u/v centerline @ Re=100/400/1000)
- Secondary: Botella & Peyret (1998) Comp & Fluids 27:421-433 (high-order Chebyshev validation of Ghia at Re=1000)

## 3 Re query points

| Case dir | Re_L | ν [m²/s] |
|---|---|---|
| case_re100  |   100 | 0.01    |
| case_re400  |   400 | 0.0025  |
| case_re1000 |  1000 | 0.001   |

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_024_v64_val_full_4_cavity_dicts/`
- Docker mount per case: `~/Desktop/case_024_lid_driven_cavity/case_re{100|400|1000}/` (cloned from repo dicts at commit-2 mesh time, with per-case ν override)

## Verdict scale (per briefing strict reverse condition)

- **FULL**: max |Δ u| < 3% AND max |Δ v| < 3% AND residuals 4/4 < 1e-7 on **3/3** Re cases
- **marginal**: 2/3 Re cases pass strict AND 1 case 略超 (3-5% Δ OR residuals 1e-6 to 1e-7) → user裁决 promote OR PARTIAL with disclosure
- **PARTIAL**: ≤1/3 Re cases pass strict OR mesh fail OR solver divergence

## Done dim advancement target

- **Done #1**: 0/3 → **1/3 strict FULL** (if FULL verdict on 3/3 Re cases)
- **Done #2**: already 3/3 ✓ MET post-B64 (Ghia 1982 + Botella-Peyret are net-new canonical refs)
- **Done #3**: unchanged (1/1 ✓ MET post-B58, mesh refinement study orthogonal to this sub-DEC)
- **Done #4**: unchanged (no V63-A PARTIAL upgrade work in scope)

## Next action

Commit 2: write 7 dicts (blockMeshDict 129×129 + controlDict + fvSchemes + fvSolution + decomposeParDict + transportProperties × 3 + turbulenceProperties + sampleDict + 0/{U,p}), run blockMesh + checkMesh in Docker on case_re100 first, mirror to case_re400 + case_re1000.

## Field-count note (briefing transparency)

Briefing reverse condition said "residuals 6/6 < 1e-7". Laminar simpleFoam has only 3 prognostic
fields (p, Ux, Uy) + continuity = 4 quantities. There is no k/omega for laminar regime. Strict gate
honored via **4/4 < 1e-7** (field-count adjusted for laminar regime, NOT gate relaxed). Documented
in CASE_SPEC §7 and validation report §1.
