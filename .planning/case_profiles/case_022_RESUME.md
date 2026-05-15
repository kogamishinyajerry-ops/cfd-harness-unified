# case_022 · RESUME

**Case**: Driver-Seegmiller Backward-Facing Step · incompressible canonical · NASA TM 86658 1985
**Started**: 2026-05-15 (V64-A B65/B66 dispatch · 5th FULL attempt)
**Status**: substrate prep landed (commit 1 of 5)
**Parent DEC**: DEC-V64-A-charter
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS (in flight)

## North Star (one line)

> 用 incompressible canonical (Driver-Seegmiller 1985 BFS · simpleFoam kOmegaSST RAS · x_R/h + 5-station Cp + 5-station Cf) 在 case_021 之外开一条独立 FULL 通道; 与 B65 lid-driven cavity cross-class 验证。

## Canonical reference

- Primary: Driver, D.M. & Seegmiller, H.L. (1985). "Features of a Reattaching Turbulent Shear Layer in Divergent Channel Flow." **NASA TM 86658** (also AIAA J Vol 23 No 2 pp 163-171 Feb 1985)
- Comparison metrics:
  - **x_R/h = 6.26 ± 0.10** (Fig 7)
  - **Cp on downstream wall** at x/h = 1, 4, 8, 12, 16 (Fig 8)
  - **Cf on downstream wall** at x/h = 1, 4, 8, 12, 16 (Fig 9)

## Reference convention (vs case_021 naming)

case_021 used `CASE_SPEC.md` (markdown) as the case specification — there is no `case.yaml` schema in this repo. case_022 follows the same convention: `parts_manifest.yaml` (minimal stub for blockMesh-native cases) + `CASE_SPEC.md` (markdown spec citing NASA TM 86658). Briefing's "case.yaml" terminology is interpreted as CASE_SPEC.md per repo convention; deviation documented here.

## 5 Cp & Cf query stations

| Station | x/h | x_abs [m] | Driver-Seegmiller Cp (Fig 8) | Driver-Seegmiller Cf (Fig 9) |
|---|---|---|---|---|
| S1 | 1.0 | 0.2667 | -0.10 | -0.0010 |
| S2 | 4.0 | 0.3048 | -0.05 | -0.0018 |
| S3 | 8.0 | 0.3556 | +0.08 | -0.0008 |
| S4 | 12.0 | 0.4064 | +0.15 | +0.0005 |
| S5 | 16.0 | 0.4572 | +0.20 | +0.0020 |

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_022_v64_val_full_5_bfs_dicts/`
- Docker mount: `~/Desktop/case_022_driver_seegmiller_bfs/case/` (copied from repo dicts at commit-2 mesh time)

## Verdict scale (per briefing reverse condition)

- **FULL**: x_R/h ∈ [6.0, 6.5] AND Cp |Δ| < 10% all 5 stations AND residuals 6/6 < 1e-5
- **Marginal**: x_R/h ∈ [5.5, 7.0] OR Cp 4/5 within tol
- **PARTIAL**: x_R/h outside [5.5, 7.0] OR residuals not converged OR solver crash

## Done dim advancement target

- Done #1: 0/3 → 1/3 strict FULL (standalone) OR 0→2/3 (if B65 cavity also FULL)
- Done #2 already MET (3/3) ✓ post-B63 — no further movement expected

## Honest expectation (honest failure-recording authorization in effect)

Per CASE_SPEC §4 §8 §10:
- Uniform inlet at 20·h → expected pre-step δ/h ≈ 0.4-0.5 (vs canonical 1.5)
- Literature shows thinner inlet BL → smaller x_R/h
- Expected actual x_R/h ≈ 5.4-6.0 — likely **marginal** verdict, possibly low-end of FULL

This is documented openly; the verdict will be what the physics give, not what the gate prefers.

## Next action

Commit 2: write 7 system dicts (blockMeshDict + controlDict + fvSchemes + fvSolution + decomposeParDict + sampleDict) + constant/turbulenceProperties + constant/transportProperties + 5 BC files (0/U, 0/p, 0/k, 0/omega, 0/nut); copy to sandbox; run blockMesh + checkMesh in Docker; capture logs; commit.
