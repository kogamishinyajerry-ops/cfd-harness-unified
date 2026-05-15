# case_021 · RESUME

**Case**: NASA TMR Turbulent Flat Plate · incompressible canonical
**Started**: 2026-05-15 (V64-A B63 dispatch)
**Status**: substrate prep landed (commit 1 of 5)
**Parent DEC**: DEC-V64-A-charter
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP (in flight)

## North Star (one line)

> 用 incompressible canonical (NASA TMR turbulent flat plate · simpleFoam kOmegaSST · 5 Re_x query stations) 完全绕开 compressible gating，把 V64-A Done #1 推到 1/3 strict FULL + Done #2 推到 3/3 ✓ MET.

## Canonical reference

- Primary: Prandtl-Schlichting eq 21.11 (1/7-power Cf_x = 0.0592 × Re_x^(-1/5))
- Secondary: Coles & Wadcock 1979 (experimental Re_θ vs Re_x)
- Tertiary: Mansour-Kim-Moin 1988 DNS (Re_τ-based)

## 5 Cf query stations

| Station | Re_x | x [m] | Cf_canonical |
|---|---|---|---|
| S1 | 2.0e6 | 0.418 | 0.003270 |
| S2 | 4.0e6 | 0.835 | 0.002846 |
| S3 | 6.0e6 | 1.253 | 0.002643 |
| S4 | 8.0e6 | 1.670 | 0.002477 |
| S5 | 9.58e6 | 2.000 | 0.002382 |

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_021_v64_val_full_3_incomp_dicts/`
- Docker mount: `~/Desktop/case_021_nasa_tmr_flat_plate/case/` (copied from repo dicts at commit-2 mesh time)

## Verdict scale (per briefing reverse condition)

- **FULL**: Cf Δ < 5% on 5/5 stations AND residuals 6/6 < 1e-5
- **marginal**: 5-10% Δ on any station OR residuals 4-5/6 converged
- **PARTIAL**: ≥10% Δ on any station OR residuals < 4/6 converged OR solver crash

## Done dim advancement target

- Done #1: 0/3 → 1/3 strict FULL (if FULL verdict)
- Done #2: 2/3 → 3/3 ✓ MET (canonical Prandtl-Schlichting comparison net-new)

## Next action

Commit 2: write 7 system/constant dicts (blockMeshDict + controlDict + fvSchemes + fvSolution + decomposeParDict + turbulenceProperties + transportProperties), run blockMesh + checkMesh in Docker container, capture log.
