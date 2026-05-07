# OpenFOAM Solver Convergence Playbook

> **Living document.** Codified from APU bay industrial case
> (`~/Desktop/apu-bay-ventilation/`) V3→V13 13-version progression.
> Append new entries when a future industrial case surfaces a
> failure mode not already listed.
>
> **Audience**: engineer driving an industrial OpenFOAM case.
> Not the persona harness. Not the AI advisor. The human who is
> looking at a `solver.log` that ends in NaN or stuck residuals.
>
> **Companion**: `.planning/methodology/industrial_case_solver_findings.md`
> (V-series finding index). This playbook is the decision tree;
> the V-series is the case-by-case audit trail.

## How to use

1. Solver dies / stalls / produces non-physical output. Read the tail
   of the log.
2. Match the **symptom** column below.
3. Read the **root cause** to understand why; **fix** is the minimal
   change to try first.
4. If fix #1 fails, follow the escalation chain in the same row.
5. Record the case + symptom + which fix worked in V-series index.

## Decision tree (most-frequent first)

### S1 · `kOmegaSST` + zero initial U field → ω blowup → wall function NaN at iter 2-3

| field | value |
|---|---|
| Symptom | Solver log shows `ω = 1.5e9` or similar near walls within first 3-5 iterations; subsequent iter shows `nut = nan` from wall function evaluation; smoothSolver fails |
| Root cause | k-ωSST wall functions (Spalding / kqRWallFunction) divide by `sqrt(k)`. With zero initial velocity field and any non-trivial mass-flow / pressure boundary, the first iteration has near-zero k and ω near walls; one iteration of strong source term blows ω to numerical infinity |
| Fix #1 (cheap) | Replace `kOmegaSST` → `laminar` for v1 baseline. Get a converged flow field; **then** restart with kOmegaSST using converged U/p as initial condition |
| Fix #2 | `potentialFoam -writePhi -initialiseUBCs` warm-start before main solver. This produces a divergence-free U field that gives wall functions reasonable inputs at iter 1 |
| Fix #3 | Switch wall function to `nutkRoughWallFunction` with `Ks=0` (less aggressive than Spalding for low-y+ initial guess) |
| Reference | APU bay V4-V7 (REPORT.md §4.3) |

### S2 · `GAMG p_rgh` stuck on V-cycle, residual flatlines

| field | value |
|---|---|
| Symptom | `p_rgh:  Solving for p_rgh, ...` repeats for many V-cycles without residual decrease; or `GAMG: cannot reduce residual below tolerance after N iterations` |
| Root cause | GAMG agglomeration produces ill-conditioned coarse-grid matrix in cases with: high cell-aspect-ratio prism layers, non-orthogonal cells from sHM on thin walls, or boundary layer transitions in compressible buoyant flow with steep ρ gradients |
| Fix #1 (cheap) | Replace `GAMG` solver with `PBiCGStab` + `diagonal` preconditioner for `p_rgh`. Slower per iter but actually converges |
| Fix #2 | Stay with GAMG but switch agglomeration: `algorithm faceAreaPair;` → `algorithm pairCoarsest;` and reduce `nCellsInCoarsestLevel 200` → `100` |
| Fix #3 | Add `nNonOrthogonalCorrectors 2` (was 0 or 1); helps when mesh `maxNonOrtho > 65°` |
| Reference | APU bay V8-V9 (REPORT.md §4.3); fvSolution v14 sets `PBiCGStab + diagonal` for `p_rgh` as default |

### S3 · `DIC` / `DILU` preconditioner SIGFPE on ill-conditioned matrices

| field | value |
|---|---|
| Symptom | Solver crashes with floating-point exception (SIGFPE) inside `Foam::DICPreconditioner::calcReciprocalD`; backtrace points at preconditioner setup |
| Root cause | DIC/DILU computes reciprocals of diagonal entries; with strong source terms (mass-flow injection at first iter, or compressible buoyant ρ→0 at high T), some diagonal entries become tiny or negative → reciprocal overflows |
| Fix #1 (cheap) | Replace `DIC`/`DILU` → `diagonal` preconditioner globally. Less accurate per iter, but stable on bad matrices |
| Fix #2 | Add `fvOptions` clipping: `limitTemperature [250, 1500] K`, `limitVelocity 200 m/s` to prevent the runaway that produces the bad matrix in the first place |
| Fix #3 | Lower URF on the offending field (e.g. `e: 0.20`); slower convergence but gives the linear system a chance to stay well-conditioned |
| Reference | APU bay V10 (REPORT.md §4.3); fvSolution v14 sets `diagonal` as default for all fields |

### S4 · Mass-flow BC + zero initial velocity → first-iter divergence catastrophe

| field | value |
|---|---|
| Symptom | First iter: `Time = 1`, then `\|U\|_max = 1e+129` or similar; solver exits non-zero; or kOmegaSST blowup per S1; or DIC SIGFPE per S3 — all variants of the same root cause |
| Root cause | `flowRateInletVelocity 7.7 kg/s` on a small inlet patch (~0.1 m²) implies |U| ≈ 65 m/s. Combined with `flowRateOutletVelocity` on a different patch and a SIMPLE solver starting from |U|=0 everywhere, iter 1 must construct the entire flow field in one shot. Standard SIMPLE relaxation (URF) cannot handle the impulse |
| Fix #1 (cheap) | `potentialFoam -writePhi -initialiseUBCs` warm start. potentialFoam solves Laplace's equation on Φ to produce a divergence-free U field consistent with the flow-rate BCs. Main solver then iterates from a sensible initial condition |
| Fix #2 | Replace mass-flow BCs with pressure-based equivalents during v1 baseline. e.g. `pressureInletOutletVelocity` + `totalPressure 0` gauge on the outlet, freestream-equivalent on the inlet. Loses the strict mass-flow constraint but lets SIMPLE settle. Restore mass-flow BCs in v2 once flow field is established |
| Fix #3 | Switch from `buoyantSimpleFoam` (steady) to `buoyantPimpleFoam` (transient). Use small `dt = 1e-4 s` with adaptive Co control. Lets physical time damp the impulse instead of forcing SIMPLE to absorb it |
| Reference | APU bay V11-V13 (REPORT.md §4.3, §8.1 v2 transient note) |

### S5 · `ρ` (compressible flow) goes negative → solver explodes

| field | value |
|---|---|
| Symptom | Solver log shows `min(rho) = -0.5` or similar negative value; subsequent iter has `nut = nan` or `e = nan` |
| Root cause | Compressible solvers (`buoyantSimpleFoam`, `rhoPimpleFoam`) use ρ = ρ(p, T). If p_rgh becomes locally negative (compressible code does not always clip), or T crashes through the lower bound of the thermophysics range, ρ derivation produces non-physical values |
| Fix #1 (cheap) | Add `fvOptions` clipping: `limitTemperature` (250-1500 K range typical) **and** `limitVelocity` (≤ Mach 0.6 = ~200 m/s for room-temp air). Both must be set; one alone is insufficient |
| Fix #2 | Lower URF on `p_rgh` to 0.05 (was 0.3 default); lets pressure converge slowly enough that ρ derivation stays bounded |
| Fix #3 | Switch to incompressible solver if Mach number is consistently < 0.3. e.g. `simpleFoam` + `boussinesq` for thermal effects without compressibility |
| Reference | APU bay V11-V12 (REPORT.md §4.3 row v11, "1e+129 发散") |

### S6 · Mesh quality marginal (`max skewness > 4`, `maxNonOrtho > 70°`) → numerical instability anywhere

| field | value |
|---|---|
| Symptom | Any of S1-S5 happens despite the BC + solver choices being correct; solver output shows occasional `bounding e:` or `bounding U:` warnings |
| Root cause | snappyHexMesh on thin walls + narrow gaps produces a small fraction of badly-shaped cells. These act as numerical singularities in the linear system; even with correct preconditioner choice, a few cells contaminate the global residual |
| Fix #1 (cheap) | Tighten `meshQualityControls` in `snappyHexMeshDict`: `maxBoundarySkewness 4` (default 20), `maxInternalSkewness 2` (default 4), `maxConcave 30` (default 80). sHM will reject ill-shaped cells and re-mesh |
| Fix #2 | Geometry surgery before meshing: decimate over-dense STL triangulation (CATIA exports often have 500k+ faces per body), microdilate APU bodies by 0.5% to seal narrow gaps that sHM struggles with. See APU bay `01b_optimize_geom.py` and the extracted `geometry_ingest/geometry_surgery.py` (A3 artifact) |
| Fix #3 | Bump refinement levels on problem patches: thin walls from `[1,2]` → `[2,3]`, critical surfaces from `[2,3]` → `[3,4]`. Costs cell count linearly, but eliminates many marginal-quality cells |
| Reference | APU bay V12 (REPORT.md §3.3); meshQualityDict template in `~/Desktop/apu-bay-ventilation/templates/system/meshQualityDict` |

### S7 · `0/` directory missing or stale after `cp -r 0.orig 0`

| field | value |
|---|---|
| Symptom | Solver fails at startup: `cannot find file 0/U` or `field U not found in field 0` |
| Root cause | Workflow is: (1) sHM writes mesh to `constant/polyMesh/`; (2) `cp -r 0.orig 0` copies initial fields; (3) BC writer modifies values in `0/`. If step (2) is forgotten — e.g. user re-runs sHM without `make solve` cleanup — `0/` is empty or stale |
| Fix | Always run `cp -r 0.orig 0` after mesh generation. Make this a hook in the solver runner script (see APU bay `09_run_solver.sh` which checks `0/` exists before invoking `buoyantSimpleFoam`) |
| Reference | APU bay design decision §4.2 of REPORT.md ("0.orig/ vs 0/"); main project should adopt this pattern |

### S8 · Patch coverage gap — sHM "ate" thin walls; `0/` BC writer silently skips them

| field | value |
|---|---|
| Symptom | mesh log says `boundary  N patches` but expected `M`; `08_write_bcs.py` reports `skipped: <patch_name> (not found in mesh)`. Solver runs but a thin wall is now a missing patch (treated as default fluid interior) |
| Root cause | sHM with `refinementSurfaces.<patch>.level [1,2]` (level 1 = 40 mm, level 2 = 20 mm) on a 50 mm thick beam / frame. The two opposing surfaces of the thin wall are inside the same level-1 cell; sHM merges them, the patch ceases to exist |
| Fix #1 (cheap) | Bump the offending patch's refinement to `[2,3]` (10 mm) — guarantees the wall is at least 5 cells thick |
| Fix #2 | Use `refinementRegions` with a thin slab around the wall to force volume refinement to `[3,4]` (5 mm) without bumping the surface level |
| Fix #3 | Accept the loss as a v1 simplification (APU bay path: 6 of 32 patches lost; 08_write_bcs auto-filters; ventilation result unaffected). Document in REPORT.md §3.4 |
| Reference | APU bay V13 / REPORT.md §3.4 ("Patch 覆盖") |

### S9 · `nut`, `alphat` initial fields wrong → first-iter wall function NaN

| field | value |
|---|---|
| Symptom | Variant of S1: solver dies at iter 1, but the log shows the failure inside `nut.boundaryField` evaluation, not `omega.boundaryField` |
| Root cause | `nut` and `alphat` are derived turbulence fields. Their `0/` files need correct boundary types per patch type (`nutUSpaldingWallFunction` on walls, `calculated` on inlets, etc.). If the `0/nut` file is generic (e.g. all `zeroGradient`), wall evaluation produces 0/0 = NaN |
| Fix | Generate `0/nut` and `0/alphat` from the same SSOT YAML + Jinja2 template that generates `0/U`, `0/p_rgh`. Each patch's BC type is determined by its `naming.yaml` type, not by hand-edit. APU bay `05_make_dicts.py` does this; main project `case_bc/writer.py` should adopt the same pattern |
| Reference | APU bay templates `templates/0/{nut,alphat}.j2` |

### S10 · Solver "converges" but residuals oscillate — pseudo-steady not fully steady

| field | value |
|---|---|
| Symptom | After N iterations, residuals stop decreasing but oscillate ±1 order of magnitude around a floor (e.g. `p_rgh` between 1e-3 and 1e-2). Continuity error is small (< 1% of inlet mass flow) but not zero |
| Root cause | Compressible buoyant flow with strong T gradients (here: 873 K APU body wall vs 328 K freestream) and SIMPLE relaxation cannot reach true steady state. The interaction p ↔ ρ ↔ U ↔ T forms a feedback loop that SIMPLE cannot fully damp |
| Fix #1 (cheap) | Accept pseudo-steady as v1. Document continuity error magnitude. Use last write step as v1 baseline. Move to v2 transient (`buoyantPimpleFoam`) for finer settle |
| Fix #2 | Increase iter budget (1000-5000 instead of 100) and lower URF further (`p_rgh: 0.05`, `U: 0.1`); will eventually settle but expensive |
| Fix #3 | Switch to true transient (`buoyantPimpleFoam`); let physical time damp the oscillation. Costs wall-clock but is the correct physics |
| Reference | APU bay V13 (REPORT.md §5.1, §8.1) |

### S11 · Multi-region post-processing reports `T = ±1e+300` for solid regions; misread as divergence

| field | value |
|---|---|
| Symptom | `11_post.py` (or equivalent) reports per-region T_min/T_max as `1e+300 / -1e+300` for one or more solid regions; appearance of catastrophic divergence; `report.md` summarises "fluid bounded but solid runaway" |
| Root cause | Multi-region solver (`chtMultiRegionSimpleFoam` / `chtMultiRegionFoam`) crashed setup-time or first-iter without writing any `case/<step>/` time directory beyond `0/`. Post-processor iterates time directories looking for solid T fields; OpenFOAM's missing-field path returns `±std::numeric_limits<double>::max()` ~= `±1e+308`, displayed as `±1e+300`. **The "divergence" is an interpretation bug, not a numerical one** |
| Fix #1 (cheap) | Verify `ls case/[0-9]*` shows ≥ 2 entries before diagnosing solid divergence. If only `0/` exists, the run did not progress; investigate setup-time crash, not solid numerics |
| Fix #2 | Drop radiation for v2 baseline (`viewFactor` setup is brittle; a radiation-off run isolates the multi-region transport from radiation issues). Restart radiation in v3 from converged v2 IC |
| Fix #3 | Make post-processor fail loudly when asked to read fields from a run that produced no time output, instead of silently returning sentinels (main-project tooling improvement) |
| Reference | case_002b CHT v1; V14 |

### S12 · Multi-region fluid sub-solver inherits S5 (compressible ρ/T runaway)

| field | value |
|---|---|
| Symptom | Multi-region solver runs without crash, but per-iter fluid-side log shows `limitTemperature limitT Lower limited N (M%) of cells; Upper limited N (M%) cells`. Percentage rises with iter; clamp is doing continuous work |
| Root cause | chtMultiRegionSimpleFoam fluid sub-solver = same compressible-buoyant-RANS numerics as `buoyantSimpleFoam`. With strong T gradients + buoyancy + steady-state SIMPLE relaxation, fluid cells near hot patches overshoot thermophysics range. Multi-region wrapping does not insulate from S5 |
| Fix | Same fix family as S5: (1) keep `fvOptions limitTemperature` clamp; (2) lower URF on `h` (0.40 → 0.20); (3) v2 simplification = drop kωSST → laminar; (4) v3 = transient `chtMultiRegionPimpleFoam` |
| Cross-link | S5 (buoyantSimpleFoam ρ runaway). When the fluid sub-solver class matches, the S-family decision tree applies regardless of multi-region wrapping |
| Reference | case_002b CHT v2 norad; V15; V-series Pattern 6 (inheritance across solver families) |

## Common patterns across all entries

1. **Zero initial field is the root of half the failures.** S1, S4, S9
   are all "first iter has no flow, all derived quantities are
   garbage". `potentialFoam` warm start is the universal cheap fix.
2. **Preconditioner choice trumps solver choice.** S2, S3 both
   resolve by changing preconditioner (`diagonal` for stability,
   `PBiCGStab+diagonal` instead of GAMG when GAMG agglomeration
   fails). Solver choice (PBiCG vs PBiCGStab vs GAMG) is secondary.
3. **Mesh quality margin = numerical safety margin.** S6 underlies
   S1-S5 in many cases — bad cells contaminate the linear system
   regardless of solver/preconditioner. Tightening `meshQualityControls`
   pre-empts S1-S5.
4. **URF lowering is the universal "give it more time" knob.** S2, S3,
   S5, S10 all benefit from lower URF on the offending field. Cost
   is iter count, gain is stability.
5. **v1 simplification is legitimate.** APU bay v1 = laminar +
   pressure-outlet BC instead of kωSST + mass-flow. The simplification
   gets a working baseline; v2 layers complexity on top. Do not
   chase production physics on v1.

## How to add a new entry

When a future industrial case surfaces a death mode not in S1-S10:

1. Add a row to V-series index
   (`industrial_case_solver_findings.md`) with case ID, symptom,
   root cause, fix, reference
2. Add a corresponding section here (S11, S12, ...) with the
   decision tree expansion
3. Cross-link both directions
4. Update "Common patterns" if the new entry surfaces a new pattern
   class

## References

- `~/Desktop/apu-bay-ventilation/evidence/v13_post_v5_183632/REPORT.md`
  — original V3→V13 trail
- `~/Desktop/apu-bay-ventilation/templates/system/fvSolution.j2`
  — production fvSolution template embodying S2+S3 fixes
- `~/Desktop/apu-bay-ventilation/scripts/09_run_solver.sh`
  — production solver invocation embodying S4 (potentialFoam warm
  start) and S7 (`0/` existence check)
- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series
  case-by-case index
