# case_028 · APU Bay Ventilation · RESUME

**Case**: APU Bay Ventilation · industrial · simpleFoam kOmegaSST RAS
**Started**: 2026-05-16 (V65-A B74 dispatch)
**Status**: substrate prep landed (commit 1 of 4)
**Parent DEC**: DEC-V65-A-charter
**Sub-DEC**: DEC-V65-A-sub-M-V65A-CASE-APU-BAY (in flight)

## North Star (one line)

> First V65-A net-new industrial case e2e — APU bay enclosure with 29 per-component STL face-name preservation + ventilation simpleFoam RAS + mass conservation + advisor stack coverage + experimental comparison qualitative. Done #3 0/2 → 1/2 primary contribution.

## Geometry source (READ-ONLY external project)

- `~/Desktop/apu-bay-ventilation-cht/work/stl_repair/per_solid/` (29 STLs · 560 MB total · per-solid decomposition validated at source CHT project)
- Source bbox: `(63.5 -1 -1.5)` to `(67.5 2.5 1.5)` — 4 × 3.5 × 3 m bay enclosure
- Source CHT mesh baseline: 89,745 cells, sHM PASS-no-errors (validated)

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_028_apu_bay_ventilation_dicts/`
- Docker mount: `~/Desktop/case_028_apu_bay_ventilation/case/` (copied from repo dicts at mesh time)

## Verdict scale

- **FULL**: residuals < 1e-4 on 4/4 fields + mass balance Δṁ < 1% + advisor ≥5/9 + literature comparison qualitative
- **strong-PARTIAL**: convergence + mass balance OK but comparison weak or advisor < 5/9
- **PARTIAL**: mesh/solver stage blocked

## Phase progress

- [x] Phase 0 final recon (STL location · docker mount · case template) — 2026-05-16
- [ ] Phase 1 substrate (case_028.md · RESUME · parts_manifest · dicts skeleton) — in progress
- [ ] Phase 2 STL import (per_solid → sandbox triSurface)
- [ ] Phase 3 mesh prep (blockMesh + sHM + checkMesh)
- [ ] Phase 4 simpleFoam run (kOmegaSST RAS · ≤5000 iter cap)
- [ ] Phase 5 advisor stack run
- [ ] Phase 6 validation report + sub-DEC + ARC-GOAL update
- [ ] Phase 7 commits + push batch

## Next action

Author parts_manifest.yaml + write OpenFOAM dicts (blockMeshDict + snappyHexMeshDict + controlDict + fvSchemes + fvSolution + decomposeParDict + transportProperties + turbulenceProperties + 0/U + 0/p + 0/k + 0/omega + 0/nut), then commit 1.
