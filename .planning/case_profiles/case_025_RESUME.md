# case_025 · RESUME

**Case**: Plane Poiseuille Channel · simplest possible analytical canonical
**Started**: 2026-05-15 (V64-A B67 dispatch · 6th FULL attempt · companion to B66 BFS)
**Status**: substrate prep landed (commit 1 of 4)
**Parent DEC**: DEC-V64-A-charter
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-POISEUILLE (in flight)

## North Star (one line)

> 在 4/4 PARTIAL track 之后用 THE simplest analytical canonical (plane Poiseuille · 1D parabolic u(y) · Re=133 deep laminar) 隔离 "infrastructure 是否健全" — 若 PASS 说明 V64-A 流水线干净, PARTIAL track 是 physics-driven; 若 PARTIAL 说明系统性 infrastructure 问题 (重大发现).

## Canonical reference

- Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed. Springer, §5.1.1
- White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.3.1
- Analytical: u(y) = (3/2)·u_mean·(1 - (y/H)²), y ∈ [-H, +H]
- u_mean = 0.1 m/s · ν = 1.5e-5 m²/s · H = 0.01 m
- u_max = 0.15 m/s · dp/dx = -0.045 m²/s²/m · τ_wall = 3e-4 m²/s² · Re_h = 133.3

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_025_v64_poiseuille_dicts/`
- Local-run mount: `~/Desktop/case_025_poiseuille_channel/case/` (copied from repo dicts at commit-2 mesh time)
- OpenFOAM: `~/OpenFOAM-v2512/etc/bashrc` (host install · macOS Apple Silicon)

## Verdict scale (per briefing)

- **FULL**: max |Δu| < 1% across 17+ y-points AND residuals 4/4 < 1e-8 AND |Δ dp/dx| < 1%
- **Marginal**: max |Δu| ∈ [1%, 3%] · documented & user-ratified
- **PARTIAL**: max |Δu| > 3% OR residuals not converged OR setup unfeasible

## Done dim advancement target

- Standalone strict PASS → Done #1 0/3 → **1/3 strict FULL**
- Coupled with B65 case_024 cavity Re=1000 (best of arc, 17/17 strict u at max 2.24%) if user ratifies cavity Re=1000 as standalone strict-PASS → 0/3 → **2/3 strict FULL**
- PARTIAL → stays 0/3 (per honest-failure-recording authorization)
- Done #2 already MET (3/3) ✓ — Schlichting/White canonical is reference but doesn't add to MET quota

## Expectation (honest failure-recording authorization in effect)

Per CASE_SPEC §10:
- Plane Poiseuille is THE simplest analytical canonical · machine-precision-achievable on a reasonable mesh
- 4/4 prior PARTIAL pattern was always physics-specific (rotation / shock / transition / discretization-on-real-canonical)
- Strong expectation: strict PASS · max |Δu| < 0.5% on 40 y-points · residuals 4/4 < 1e-10
- Caveats:
  - codedFixedValue compile path is med-risk on host-OpenFOAM-v2512 macOS (fallback: uniform inlet + sample at x=0.5 = 3.1·L_entrance fully-developed)
  - simpleGrading bilinear convention symmetric-grading not previously exercised in single-block case in this repo

## Next action

Commit 2: write 5 system dicts (blockMeshDict + controlDict + fvSchemes + fvSolution + sampleDict) + 2 constant dicts (transportProperties + turbulenceProperties laminar) + 2 BC files (0/U codedFixedValue + 0/p); copy to sandbox; run blockMesh + checkMesh locally (host-OpenFOAM-v2512); capture logs; commit.
