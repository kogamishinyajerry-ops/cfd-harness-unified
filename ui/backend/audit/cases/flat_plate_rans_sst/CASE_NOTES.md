# `flat_plate_rans_sst` — Case Notes

> Scaffolded in Phase 1 step 2b (2026-05-20). This document is the
> source-of-truth for what is production-ready vs placeholder in this case.

## Lineage

This case is a Phase 1 OpenFOAM scaffold derived from the contract in
`case_manifest.yaml`. The dictionary files under `system/`, `constant/`,
and `0/` are **structurally valid OpenFOAM 11 input** and are wired to
match the manifest's boundary-condition, turbulence-model, and
solver-target declarations. They are **not** yet equivalent to the
NASA TMR reference run (see "What is NOT production-quality" below).

## What is production-quality (used as-is)

- **Turbulence model**: `kOmegaSST` (matches `physics.turbulence_model`).
- **Solver**: `simpleFoam`, steady incompressible RANS (matches
  `physics.regime: steady_incompressible_RANS`).
- **Numerical schemes**: `linearUpwind` for U-advection,
  `upwind` for k/omega advection, `corrected` Laplacian. These are the
  defaults the OpenFOAM Foundation publishes for `kOmegaSST` external
  aerodynamics tutorials and are the right baseline for a Phase 1 run.
- **Residual control**: targets `1e-5` for U, p, k, omega match
  `solver_contract.residual_targets`. `max_iterations` 500 matches
  `solver_contract.max_iterations`.
- **Function object**: `residuals` writes per-iteration residual values
  to the log every time-step, so the trust harness's `residuals.csv`
  parser (Phase 1 step 2c) has structured data to read.
- **Boundary patches**: `inlet / outlet / wall / top / frontAndBack`
  match `geometry_contract.required_patches`.

## What is NOT production-quality (Phase 1 placeholder; flag for Phase 2)

### Mesh (blockMeshDict)

- **Geometry box**: 2 m × 1 m × 0.05 m (single-cell deep for 2.5D).
  NASA TMR flat plate is 2 m × 1 m × thin. **Inlet-to-leading-edge
  laminar region not modeled** — the entire bottom wall is treated as
  "wall" with `noSlip + wall functions`. NASA TMR has a symmetry-plane
  leading section followed by the plate; our scaffold collapses both
  into one no-slip wall. Step 2d's QoI comparison will need to either
  (a) restrict the comparison window to the plate-only section, or
  (b) re-mesh with the symmetry/wall split. Documented for the
  reference-comparison step.
- **Cell count**: `(100 60 1)` = 6,000 cells (live-confirmed by blockMesh
  in step 2b round-14 probe). **Mesh independence study NOT performed.**
  The manifest's `qoi_stability` gate would catch a non-converged Cf
  prediction at this resolution. Phase 2 should produce a
  coarse/medium/fine triplet under `negative_tests/` to expose the gap.
- **R14-F-03 — quantified y+ mismatch (KNOWN, scoped to Phase 2)**:
  Live blockMesh reported first-cell-y of 1.31 mm; cell-center y_p =
  0.654 mm. With manifest's U=30 m/s, ν=1.5e-5: estimated friction
  velocity u_τ ≈ 1.21 m/s (via 1/7-power-law) → **y+ ≈ 53**. The
  manifest's `mesh_contract.y_plus_target` declares `min: 0.5, max: 5.0`.
  Scaffold is roughly **10× above the target maximum**. Implications:
  - the current scaffold produces a **wall-modeled** boundary layer,
    not the wall-resolved one the manifest declares
  - step 2c's post-run y+ audit (when it lands) will report this as a
    BC contract violation
  - to bring y+ ≤ 5 with the same flow conditions, the wall-normal
    cell count must roughly 10× (or simpleGrading climb from 50 to
    ~5000-10000 with `n_y ≈ 80-120`). Doing this also requires switching
    `nutkWallFunction` (high-Re) to `nutLowReWallFunction` for consistent
    near-wall physics.
  - Phase 2 V&V audit is the right home for this reconciliation —
    deferring rather than over-fitting Phase 1 with one specific choice.
- **Wall grading**: `simpleGrading (1 50 1)` (kept from initial scaffold
  for the y+ mismatch reason above; honest about the gap rather than
  silently changing the manifest target). Step 2c's `checkMesh +
  post-run y+ check` is the gate that surfaces this on first run.

### Initial fields

- **k internalField**: computed from `I=0.01, U=30` → `k = 1.5(IU)² ≈ 0.135`.
  Correct algebraically; assumes uniform turbulence everywhere at start.
- **omega internalField**: computed from `k=0.135, L_t=0.01 m` →
  `omega ≈ 67`. Same uniform-everywhere assumption.
- **nut internalField**: `0`. This is a safe initialization for a
  fresh run; `simpleFoam` will populate `nut` from the wall function +
  turbulence model immediately.

### Wall functions

- `kqRWallFunction`, `omegaWallFunction`, `nutkWallFunction` are
  **high-Re / wall-modeled** functions. The manifest declares
  `wall_function_policy: low_re_resolved` — a mismatch the Phase 2
  audit will catch. For a low-Re resolved approach we'd want
  `nutLowReWallFunction` + mesh refined enough for `y+ < 1`. **Phase 1
  step 2b uses high-Re wall functions as a working starting point;
  Phase 2 reconciles this with the manifest declaration.**
  - Documented here so the gap is visible BEFORE Phase 2's audit
    declares it as a finding.

## Validation status (per `bc_contract` / manifest)

```
solver_execution     = mocked          (will become "real" once 2c runs simpleFoam in Docker)
validation_status    = not_validated   (will only move to "validated" after 2d's NASA TMR comparison)
```

## Files

```
system/
  controlDict             - simpleFoam control + residuals function object
  fvSchemes               - discretization
  fvSolution              - linear-solver settings + SIMPLE residualControl
  blockMeshDict           - 2.5D scaffold mesh
constant/
  transportProperties     - Newtonian, nu=1.5e-5 m²/s
  turbulenceProperties    - RAS / kOmegaSST
  polyMesh/.gitkeep       - placeholder; blockMesh populates this at step-2c
                             runtime. Generated files (boundary, faces,
                             neighbour, owner, points) are .gitignore'd —
                             they're reproducible from blockMeshDict.
0/
  U                       - velocity initial + BCs
  p                       - kinematic pressure initial + BCs
  k                       - TKE initial + BCs
  omega                   - specific dissipation initial + BCs
  nut                     - turbulent viscosity initial + BCs
```

## R14-F-02 — `residualControl` naming convention vs manifest

The manifest's `solver_contract.residual_targets` keys by SPLIT components
(`Ux: 1e-5`, `Uy: 1e-5`). OpenFOAM's `fvSolution.residualControl` keys by
the COMBINED vector field name (`U: 1e-5`). The scaffold uses the
combined form because that's what OpenFOAM expects; the contract-fidelity
test (`test_flat_plate_case_dictionaries_reference_manifest_contract`)
accepts both naming styles. **Documenting here so a Phase 2 reviewer
knows this isn't a typo.**
