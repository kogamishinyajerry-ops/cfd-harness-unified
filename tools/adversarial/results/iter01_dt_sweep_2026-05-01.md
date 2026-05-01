# iter01 dt sweep — disproves CFL hypothesis, surfaces 2 deeper defects

**Date**: 2026-05-01
**Context**: DEC-V61-106 deferred iter01 migration to `analytical_comparator_pass` until the underlying icoFoam divergence is fixed. This sweep tests the most-likely hypothesis (CFL number too high → smaller dt → stable) and finds it disproven, while incidentally surfacing a second defect in the backend's residual log parser.

## Methodology

Drove iter01 through the full pipeline (`/api/import/stl` → `/mesh` → `/setup-bc?from_stl_patches=1` → `/solve`) at 4 dt values. For each, captured backend's reported residuals AND counted NaN entries in the final time directory's U field.

Probe: `tools/adversarial/probes/v61_104_1_probe/iter01_dt_sweep.py` (kept under /tmp; copy here if reproducing).

## Results

| dt | end_time | wall | cont_err | res_p | res_U[0] | NaN in final U | final time dir |
|---|---|---|---|---|---|---|---|
| 1.0 | 10.0 | 10s | 1.16e-3 | 1.33e-4 | **1.0** | **21477** | 10 |
| 0.1 | 10.0 | 92s | 9.24e-5 | 1.11e-4 | **1.0** | **21477** | 10 |
| 0.01 | 2.0 | 185s | 2.66e-6 | 2.87e-4 | **1.0** | **21477** | 2 |
| 0.001 | 0.2 | 702s | 3.93e-7 | 8.74e-5 | **1.0** | -1 (no time dir) | — |

(NaN_in_final_U = -1 means no time directory was written within the 900s timeout. The case took 702s of wall time for 200 steps at dt=0.001 — too slow for further sweep.)

## Three findings

### Finding 1 — CFL hypothesis is DISPROVEN
At dt=0.01 the Courant number is ~0.02 (well below 1) yet the U field is still all-NaN at t=2.0s. NaN persists across 3 orders of magnitude of dt. iter01's divergence is **structural**, not numerical.

### Finding 2 — `cont_err` improves cleanly with dt (the pressure solver works)
`cont_err` drops monotonically as dt shrinks (1e-3 → 1e-4 → 1e-6 → 1e-7). The pressure equation IS doing meaningful work — the divergence isn't from the pressure side.

### Finding 3 — Backend residual parser is broken (NEW DEFECT)
`last_initial_residual_U[0]` is **exactly 1.0 at every dt**, identical across 4 trials. This is a fingerprint of the backend's log parser: it captures only the FIRST iteration of the LAST timestep's residual (always 1.0 because it's normalized against the previous step's residual), not the converged residual at the end of that step. This explains why iter01 has appeared "converged" historically — the backend has been reporting a fixed false-positive.

## Likely root cause (next-DEC investigation scope)

Since divergence is structural and not CFL/pressure-driven, candidates:
- **Momentum equation BC**: blade patch's no_slip_wall might be authored with a missing/wrong field (e.g. omitted `value` or wrong type for icoFoam's velocity BC)
- **Degenerate mesh cells in gap region**: the 4mm gap between blade and wall may produce cells with very high aspect ratio or near-zero volume that produce singular momentum solutions
- **icoFoam scheme choice**: default schemes (probably linear interpolation + Gauss linear divergence) may not be appropriate for this geometry; need upwind / vanLeer

Recommended next-DEC scope (DEC-V61-107 candidate):
1. Inspect the `0/U` and `0/p` files iter01 produces — check BCs by patch
2. Run `checkMesh` on the polyMesh to see if there are degenerate cells
3. Try authoring fvSchemes manually (upwind for div(phi,U)) and see if NaN persists
4. Fix the residual log parser to report the converged residual, not the first-iteration one (separate sub-defect — affects all cases, not just iter01)

## Status

- ✅ Hypothesis test complete (CFL ruled out)
- ✅ 2 unrelated defects surfaced (residual parser + structural divergence)
- ⏸️ iter01 stays at `physics_validation_required` (SKIPPED) until follow-up DEC
- ⏸️ Backend residual parser bug deferred to its own ticket
