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

### S13 · Compressible-RANS pseudo-steady mass imbalance: totalPressure-inlet + fixedValue/waveTransmissive-outlet on a coarse mesh fails to lock in mass conservation

| field | value |
|---|---|
| Symptom | rhoSimpleFoam runs 0-500 iter without crashing; Tmin/Tmax bounded; no NaN/SIGFPE. But residuals oscillate without monotonic decrease (Ux 0.1-0.3 throughout, p ~0.005 throughout); cumulative continuity error grows; `surfaceFieldValue` shows phi_inlet ≠ phi_outlet by factor 2-3 |
| Root cause | SIMPLE algorithm with totalPressure inlet + fixedValue (or waveTransmissive) outlet, started from non-zero but rough initial U, struggles to establish the inlet→outlet pressure ratio. Compressible momentum equation lags the pressure update (URF p=0.20, U=0.50), and a coarse mesh (50-100k cells, no prism layers) does not have enough resolution to enforce wall-bounded boundary layer. Mass conservation does not lock in within 500 iter — the BC chain is in transient balance |
| Fix #1 (cheap) | `potentialFoam -writePhi -initialiseUBCs` warm-start before rhoSimpleFoam. potentialFoam solves Laplace's equation on Φ with the totalPressure-inlet flow-rate BCs to produce a divergence-free U field. rhoSimpleFoam then iterates from a sensible initial condition that satisfies mass conservation at iter 1 |
| Fix #2 | Lower URF further (p: 0.20 → 0.10, U: 0.50 → 0.30, e/h: 0.20 → 0.10) + extend iter budget to 2000-5000. Slower per iter but eventually settles. Compressible URF tuning is more sensitive than incompressible — overshoot the URF and the SIMPLE pressure update overshoots, producing waveTransmissive bounce-back. **case_005 v2 falsification (2026-05-08 afternoon)**: applied this fix in isolation (URF.p 0.20→0.10, URF.U 0.50→0.30, iter 500→2000, Sutherland transport added). Result: Ux Initial residual dropped 30-70× (0.2-0.5 → 0.007-0.008) — solver-side convergence achieved. **But inlet/outlet mass imbalance preserved at 2.8× (vs v1's 2.9×); cumulative continuity error grew to 419k (vs v1's 131k); AIP Mach actually dropped 0.18 → 0.15.** **Lesson: Fix #2 alone is INSUFFICIENT when the totalPressure-inlet + fixedValue-outlet BC chain is the structural cause. Local solver convergence ≠ global mass conservation between BC patches.** Must combine with Fix #1 (potentialFoam warm-start) OR Fix #3 (rhoPimpleFoam transient) OR mesh-side refinement |
| Fix #3 | Switch to `rhoPimpleFoam` transient (Codex's v2 fallback). Use `dt = 1e-5` to `1e-4 s` with adaptive Co control. Lets physical time damp the transient instead of forcing SIMPLE to absorb it |
| Mesh-side | Refine mesh on duct wall to (3, 4) — get to ~150-300k cells; add 3-layer prism (expansion 1.2, finalLayerThickness 0.4); fix concave cells from sHM on S-curve transitions (geometry surgery + smoother centerline parameterization upstream). All three reduce the BC-chain settling time |
| Reference | case_005_rae_m2129_sduct v1 (2026-05-08 morning); **case_005 v2 (2026-05-08 afternoon, evidence/v2_final/REPORT.md — Fix #2 falsification)**; V18 (compressible-RANS root) |
| **Diagnostic check** | If Ux Initial residual drops to <1e-2 but `phi_inlet ≠ phi_outlet` by >1.5×, Fix #2 alone is INSUFFICIENT — escalate immediately to Fix #1 / Fix #3. Local-solver convergence is necessary but not sufficient for BC-chain mass-conservation closure. v1 vs v2 of case_005 demonstrates this signal cleanly |

### S14 · `cq.Compound.makeCompound([Face, Face, ...])` STEP export pattern fragments through FreeCAD as N standalone Part::Feature objects

| field | value |
|---|---|
| Symptom | Defect manifest verification command `len(o['<body>'].Shape.Faces)` returns 1 instead of the expected N. FreeCAD doc has N+M objects total (M expected named bodies + N triangle-face objects with auto-generated suffix names) |
| Root cause | Codex CAD generator builds N standalone `cq.Face` objects and packs them via `cq.Compound.makeCompound(faces)` to inject an over-density defect. cadquery's STEP exporter emits each face as a separate top-level entity; FreeCAD's `Import.insert()` correctly creates one Part::Feature per top-level entity. The single-object verification command was written assuming a single `Solid` wrapping the over-dense triangulation |
| Fix #1 (verification side) | Aggregate by label prefix in the verification script — sum `Shape.Faces` across all `<body>*` objects matching `startswith()`. case_005 `verify_defects.py` demonstrates this (302 LOC) |
| Fix #2 (generation side) | Update `codex_case_design_protocol.md` to require Codex CAD generators to wrap over-density triangulations in a single `cq.Solid` (or `cq.Shell`) — emit a structurally-coherent body, not a Compound of disjoint faces. Update Codex case-design prompts to specify "single solid output" for D2-class defects |
| Fix #3 (downstream pipeline) | For the meshing pipeline (sHM input STL), regenerate the surface parametrically as a connected manifold trimesh from the same constants used by the CAD generator. case_005 `01_extract_stl.py` demonstrates: 80×96 axial × theta grid with vertex deduplication produces a 15,360-face cylinder surface from the same `radius()` + `centerline_z()` formulas |
| Reference | case_005_rae_m2129_sduct (2026-05-08); V16 (Codex CAD pattern) |

### S15 · rhoCentralFoam infrastructure: adjustTimeStep + smoothSolver + freestream BC family (density-based root)

| field | value |
|---|---|
| Symptom | (a) First-iter Mean Co > 100 / Max Co > 10⁴ when controlDict has `adjustTimeStep no` + fixed `deltaT 1`. Solver may not crash immediately because rhoCentralFoam's `diagonal` solver tolerates Co arbitrarily, but produces numerical garbage and downstream errors. (b) `Unknown symmetric matrix preconditioner type DILU` runtime error after iter 1. (c) `0/p/boundaryField/... characteristicPressureInletOutletPressure not found in valid types`. All three are first-time-density-based traps |
| Root cause | rhoCentralFoam is **explicit central-upwind**: CFL stability requires Co < 1 universally. (a) Fixed dt=1 on 31 mm cells at 625 m/s wave speed = Co ≈ 20,000. (b) rhoCentralFoam wraps U/e/k/omega in symmetric matrix path; DILU is asymmetric-only. (c) `characteristicPressureInletOutletPressure` is foam-extend; OpenFOAM ESI uses `freestream`+`freestreamPressure`. Pattern: density-based solvers have an entire class of numerics + BC + solver-setup conventions distinct from pressure-based compressible solvers (rhoSimpleFoam, rhoPimpleFoam) |
| Fix #1 (cheap) | controlDict: `adjustTimeStep yes`, `maxCo 0.5`, initial `deltaT 1e-6`. Single change — gets solver running with self-adjusting CFL |
| Fix #2 | fvSolution: `diagonal` for ρ/ρU/ρE; `smoothSolver + symGaussSeidel` for U/e/k/omega. Standard rhoCentralFoam pattern from `tutorials/compressible/rhoCentralFoam/biconic25-55Run35` |
| Fix #3 | 0/* fields use OpenFOAM ESI canonical BC family for transonic external: U → `freestream` (with `freestreamValue`), p → `freestreamPressure`, T → `freestream`. NOT `characteristicPressureInletOutletPressure` (foam-extend) NOT `pressureInletOutletVelocity` (incompressible-only) |
| Mesh-side | Density-based mesh requirements differ from pressure-based: (a) max Co ≤ 0.5 on smallest cell drives wall-clock cost — coarse mesh is acceptable for v1 pipeline validation; (b) lambda-shock pattern resolution needs ≥30 spanwise cells across η=0.65-0.95 lambda zone + ≥10 cells across shock thickness — minimum ~1M cells for canonical case_006-class problem |
| Reference | case_006_onera_m6_transonic v1 (2026-05-08); first density-based case for the project |
| **V-row anchors** | V27 (adjustTimeStep), V28 (smoothSolver), V29 (freestream BC), V30 (thin_wall_advisor extreme-thinness validation), V31 (Codex defect-mapping mismatch), V32 (Tier-1 source double-blocker) |

### S16 · Lagrangian-on-frozen-Eulerian: simpleFoam → freeze U/p/nut → kinematicCloud one-way; cloud needs no further pressure-velocity coupling (incompressible-RANS-Lagrangian root)

| field | value |
|---|---|
| Symptom | First Lagrangian (kinematicCloud / DPMFoam / sprayCloud) case in a project. Engineer attempts to run a coupled solver (e.g., DPMFoam from iter 0) on a not-yet-converged Eulerian. Symptom space: (a) particle parcels see chaotic velocity field while Eulerian solver still ramping → unphysical trajectories near walls; (b) two-way source terms re-perturb Eulerian momentum that hasn't yet converged → SIMPLE oscillations; (c) cloud post-processing (β(s/c), parcel mass balance) becomes meaningless because the Eulerian field is non-stationary. Even after Eulerian convergence, leaving the solver in coupled mode forces the cloud-step ddt scheme to be non-zero, producing additional p-U updates the converged Eulerian doesn't need |
| Root cause | (a) Particle-laden flow has two timescale regimes — convection (driven by U_inf, fast) and particle relaxation (driven by Stokes number, slower or comparable depending on regime). Coupling both into one staged solver works for transient cases (DPMFoam) but is overkill when volume fraction is dilute (case_008: 7e-7 → 1-way is correct). (b) For dilute particle-laden flow at steady-state, the **right pattern is staged decoupling**: converge the Eulerian first as if there were no particles, then run the cloud as a pure post-processing pass on the frozen Eulerian. The cloud step does not require any p-U update — the velocity field is given. This is sometimes called "frozen-flow Lagrangian", "post-processed cloud", or "Eulerian-then-Lagrangian" |
| Fix #1 (canonical pattern, case_008) | Three-stage shell: (1) `simpleFoam` to convergence (residuals < 1e-5 OR a fixed iteration budget if pseudo-steady oscillating per S13); (2) snapshot final `U`, `p`, `nut`, `k`, `omega` from latest time → copy into stage-2 0/; (3) `icoUncoupledKinematicParcelFoam` (OpenFOAM-2312) or `simpleCoupledKinematicParcelFoam` (older OF) with `solution.coupled=false` in `kinematicCloudProperties`. The cloud solver only advances parcels; no Eulerian fields are touched. Stage-3 ddt scheme is `Euler` for the cloud-internal U integration, `steadyState` (ignored, no p-U update) for the Eulerian. Pattern reference: `~/Desktop/case_008_glc305_irt_lagrangian/scripts/09_run_solver.sh` |
| Fix #2 (when 2-way coupling needed) | If particle volume fraction > ~1e-4 (concentrated dispersed flow, sprayCloud combustion injection, sediment-laden flow), 1-way is wrong; switch to DPMFoam (or rhoPimpleFoam variant if compressible) with `solution.coupled=true`. Run transient. Cost is non-trivial: full p-U-cloud coupled iteration per dt. Use only when dilute-1-way assumption demonstrably fails (force-monitor sensitivity to coupling toggle, or empirical particle-vs-fluid timescale > 0.1) |
| Fix #3 (post-processing only) | If the engineering question is purely descriptive (where do particles deposit, what's the catch rate), and Eulerian is already converged from a prior run, **only stage 3 needs to run**. This is functionally a post-processor that happens to use OpenFOAM's particle solver as the trajectory integrator. Promotion candidate: `lagrangian_postprocess_only.sh` shell artifact for main-project shared services |
| Reference | case_008_glc305_irt_lagrangian v1 (2026-05-08); first Lagrangian case for the project; pattern intended for inheritance by future Lagrangian/spray/sediment cases |
| **V-row anchors** | V36 (A2 advisor cross-topology PASS on Lagrangian airfoil-mount topology), V37 (thin_wall_advisor 6-topology arc closed) |

### S17 · reactingFoam infrastructure: chemkin mech ingestion + thermo header normalization (case_009 / reacting-low-Mach root)

| Branch | Action |
|---|---|
| Symptom | `chemkinToFoam` fails with one of: (a) "expected `<word><label>` (4(2A1,I3)) but found '\"0\"0.000'" — bare `THERMO` header parsed as species record; (b) "ill defined primitiveEntry starting at keyword 'AR' on line 1 and ending at line 111" — tran.dat missing `END` terminator; (c) `attempt to use janafThermo<...> out of temperature range 300 -> 3000` floods log even though physical T is 294 K — GRI-3.0 header line clamps Tlow=300 |
| Decision tree |  |
| Fix #1 (`THERMO` header) | Normalize header line to `THERMO ALL` before chemkinToFoam (chemkin-II convention; chemkinReader requires the `ALL` keyword to recognize the next line as global temperature range). Idempotent sed `s/^THERMO$/THERMO ALL/`. **V-row**: V38 |
| Fix #2 (transport file `END`) | Append `END\n` to tran.dat if missing. OpenFOAM's primitiveEntry reader is strict about block terminators; chemkin-II spec requires `END` after transport block but some published mech files (Berkeley GRI-3.0 mirror) omit it. **V-row**: V39 |
| Fix #3 (Tlow=200 patch) | If physical T can drop below 300 K (e.g. ambient inflow, buoyancy-driven cooling), edit thermo file's header `300.000  1000.000  5000.000` → `200.000  1000.000  5000.000` BEFORE chemkinToFoam. Per-species records in GRI-3.0 thermo30.dat already include polynomial fits down to 200 K; only the global header was clamping. Without this fix, log floods with limit warnings + wall-clock dominates I/O. **V-row**: V41 |
| Fix #4 (transport input choice) | chemkinToFoam transport-file argument is dual-mode: chemkin tran.dat (per-species coefficients) OR OpenFOAM-format dict with regex `.*` and air-like sutherland (`As 1.4584e-06; Ts 110.4;`). For v1 reacting baseline, OpenFOAM-dict path is faster + more portable; per-species fitting from chemkin tran.dat is a v2 deliverable. **V-row**: V40 |
| Productizable artifact | `chemkin_mechanism_loader.py` — fetches chem.inp + therm.dat + tran.dat (with cache); applies V38/V39/V41 patches idempotently; chooses transport-input mode (chemkin or dict); invokes chemkinToFoam in OpenFOAM container. Composition: under DEC-V61-198 sub-DEC, ~150 LOC. Bundles V38+V39+V40+V41 |
| Reference | case_009_sandia_flame_d v1 (2026-05-08); first reacting-low-Mach case for the project; pattern intended for inheritance by future reacting cases (fireFoam, reactingPimpleFoam, edcSimpleFoam) |
| **V-row anchors** | V38, V39, V40, V41 — chemkinToFoam infrastructure cluster |

### S18 · reactingFoam staged startup: cold-flow → ignite → ramp (case_009 / reacting-low-Mach root)

| Branch | Action |
|---|---|
| Symptom | reactingFoam with chemistry on at t=0 + zero IC fields → first chemistry ODE solve sees ill-conditioned state (no flow, no temperature gradient, no species mixing). Diverges or NaNs in first few iterations |
| Decision tree |  |
| Stage A (cold-flow) | `combustionProperties:active false`; `deltaT 1e-5`; run for ≥ 0.005 s of physical time (∼1× domain pass for the slowest inlet). Develops velocity field, species mixing layers, temperature stratification. Verdict: clean exit + min/max(T) bounded by inlet values + no spurious species drift |
| Stage B (ignite) | `combustionProperties:active true`; `deltaT 1e-6` (10× smaller than cold-flow); run from latestTime for ≥ 1e-3 s. Pilot's hot products propagate finite-rate chemistry into the fuel-air mixing layer; T_max should rise above the hottest inlet bound (1880 K for Flame D pilot) within ∼200 μs of physical time. Verdict: T_max climbs without overshoot above ∼2200 K (CH4/air adiabatic flame); species bounded in [0, 1] |
| Stage C (ramp) | `adjustTimeStep yes`, `maxCo 0.5`, initial `deltaT 1e-5`; run from latestTime to pseudo-steady (∼ 0.5-1.0 s for Flame D L_vis ≈ 482 mm jet at 49.6 m/s = 1 flow-through). Solver auto-tunes dt against chemistry stiffness + Courant; expect dt to settle at ∼1e-5 with maxCo=0.5 |
| Failure mode A — skipping Stage A | Chemistry on at t=0 with zero IC → first ODE solve is on garbage state, NaN within 10 iterations. **Fix**: NEVER skip Stage A |
| Failure mode B — Stage B dt too large | dt=1e-5 with chemistry on → heat-release rate spike per cell exceeds local enthalpy advection → first inner iteration explodes. **Fix**: drop dt to 1e-6 in Stage B; Stage C re-ramps with adjustTimeStep + maxCo |
| Failure mode C — endTime too short for Stage C | Pseudo-steady requires ≥ 1 flow-through (∼ 0.012 s at U_jet=49.6 m/s for the 576 mm domain). v1 smoke runs of 0.001 s ignite + 0.005 s cold are PIPELINE demonstrations, NOT verdict-grade |
| Productizable artifact | `staged_startup_runner.sh` shell artifact: `09_run_solver.sh cold|ignite|ramp|all` — flips combustionProperties.active + dt + endTime per stage; bundle template with main-project case-runner shared services |
| Reference | case_009_sandia_flame_d v1 (2026-05-08); cold-flow ran clean at min/max(T) = [294, 1880] K; ignite started chemistry; T_max = 1880 → 1980+ K within 5e-4 s of physical time |
| **V-row anchors** | (no V-finding — this is the "good practice" S-row that PREVENTS V-findings; it is the chemistry-startup playbook) |

### S19 · pimpleFoam LES staged restart: transient settle → averaging → tail-mean (case_010 / incompressible-LES root)

| Branch | Action |
|---|---|
| Symptom | LES Cd / Cl / Cm signals contaminated by initial transient if `fieldAverage` includes the spin-up window. Time-averaged Cd appears to "drift" continuously instead of converging — but the drift is settling-bias, not insufficient sampling. Fix is two-stage restart: discard the spin-up time, then start averaging cleanly |
| Decision tree |  |
| Stage A (transient settle) | `system/controlDict.functions.fieldAverage1` ABSENT (or `timeStart` set beyond endTime). `endTime = 2 * L / U_inf` (= 2 flow-through times). Run from t=0 to discard the artifact-rich window during which boundary-layer growth + recirculation onset + wake-shedding-frequency-locking happen. For case_010: endTime ≈ 0.576 s. Verdict: clean exit; sampled Cd signal swings around mean without monotonic drift |
| Stage B (averaging) | Restart from latestTime. `system/controlDict.functions.fieldAverage1` now present with `cleanRestart true; timeStart <Stage_A_endTime>`. `endTime = 7 * L / U_inf` (= 5 additional flow-through times after the 2-FT settle). For case_010: endTime ≈ 2.017 s. Verdict: forceCoeffs1 tail-window mean (last 5 FTs) is the time-averaged Cd; std-dev across the 5 sub-windows quantifies sampling error |
| Stage C (tail-mean) | After Stage B, parse `postProcessing/forceCoeffs1/<startTime>/coefficient.dat`; tail-average the last 5 L/U_inf samples; report Cd_total = Cd_pressure + Cd_friction; also extract `<startTime>/U` and `<startTime>/p` (Stage B time-averaged fields) for surface Cp at TUM tap regions + base-pressure-recovery analysis |
| Failure mode A — skipping Stage A | `fieldAverage` ON at t=0 with zero IC + initial-pressure-pulse + boundary-layer growth → all included in mean → Cd over-predicts by 5-15% (depends on settling artifact magnitude). **Fix**: NEVER include `fieldAverage` in Stage A; ALWAYS use `cleanRestart true` in Stage B |
| Failure mode B — Stage B too short (< 5 FT) | Cd visibly varies between sub-windows; std-dev across 5 sub-windows is large compared to mean. **Fix**: extend Stage B endTime; rerun. (Common for first LES iteration: estimate endTime conservatively then extend if std-dev > 2% of mean) |
| Failure mode C — Stage A 0/0.orig template wrong | `0.orig` for LES MUST contain `nut` (Spalding wall function), MUST NOT contain `nuTilda` (Spalart-Allmaras only) and MUST NOT contain `k`/`omega` (k-omega RANS only). Inheriting RANS templates fails immediately. **Fix**: dedicated LES `0.orig` template with U+p+nut only |
| Productizable artifact | `field_average_function_object_writer.py` (case_010 sandbox `08e_write_field_average_function_object.py`) — `--stage transient` emits Stage A controlDict; `--stage averaging` emits Stage B controlDict with cleanRestart + timeStart. Same script writes both stages from the same case.yaml SSOT. Promote to harness for next LES case |
| Reference | case_010_drivaer_fastback_les v1 baseline 2026-05-08 (`scripts/08e_write_field_average_function_object.py`, `templates/controlDict_LES.j2`); two-stage restart contract |
| **V-row anchors** | V45 (LES infrastructure) — this is the "how to use V45's templates correctly" playbook |

### S20 · LES wall-modeled y+ band (30-100): nutUSpaldingWallFunction + addLayers tuning (case_010 / incompressible-LES root)

| Branch | Action |
|---|---|
| Symptom | LES with target y+=30-100 (wall-modeled regime) on vehicle/airfoil bodies. Mean y+ acceptable but max y+ overshoots (e.g., 200+) at A-pillar / wing-LE / sharp-edge stagnation regions. Overshoot regions get spurious wall-shear + skin-friction drag |
| Decision tree |  |
| Stage A (diagnose) | After Stage A averaging or even mid-spinup, enable `yPlus` function-object in controlDict. checkMesh-style scan: parse log.transient for "max yPlus" and "min yPlus" + `postProcessing/yPlus/0/yPlus.dat`. **Pass criterion**: 5th–95th percentile y+ in [30, 100] band; max y+ < 200 acceptable (peak local overshoot tolerable for wall-modeled) |
| Stage B (mesh fix · increase prism layers) | If max y+ overshoots > 200: `addLayersControls.nSurfaceLayers` from 3 → 5-6 with `expansionRatio` from 1.3 → 1.2 (smaller growth ratio packs more cells in inner layer). Also `finalLayerThickness` from 0.5 → 0.3 (relative to background). Re-run sHM addLayers stage |
| Stage C (alternate · switch wall function) | If sHM layer addition keeps failing on sharp edges (negative-volume warnings during layer extrusion): switch from `nutUSpaldingWallFunction` to `nutUWallFunction` (smoother but less accurate at log-layer transition). Acceptable for v1 LES; revisit in v2 with refinementRegions slab around the offending sharp edge |
| Failure mode A — y+ < 5 (over-resolved sublayer) | Means addLayers thickness too small OR background cell already too small. `nutUSpaldingWallFunction` works at any y+ but cells smaller than required at y+=5 waste compute and may trigger near-wall instability for LES (subgrid model assumes inertial-range eddies which require y+ >~ 30). **Fix**: bump background cell size or reduce nSurfaceLayers |
| Failure mode B — y+ > 200 globally | Background mesh too coarse. **Fix**: bump body refinement level (4,5) → (5,6); rerun sHM. Cost: ~4× cells in body region |
| Failure mode C — local y+ spikes only | Tolerable; documented in v2 REPORT.md as "expected at sharp-feature stagnation". Do not over-refine globally to chase local outliers |
| Productizable artifact | yPlus diagnostic snippet `scripts/post/yplus_audit.py` (parse postProcessing/yPlus output → percentile distribution → severity classification). Not extracted in v1; candidate for v3 |
| Reference | case_010_drivaer_fastback_les v1 sandbox (`templates/controlDict_LES.j2` includes yPlus FO; templates/snappyHexMeshDict.j2 has addLayers config) |
| **V-row anchors** | V45 (LES infrastructure) |

### S21 · LES rear-base separation over-prediction → WALE Cw constant tune OR dynamicKEqn fallback (case_010 / incompressible-LES root)

| Branch | Action |
|---|---|
| Symptom | After Stage A + Stage B (S19), time-averaged Cd compared to TUM fastback target (Cd ≈ 0.281) shows over-prediction by 10-30%, primarily from over-active rear-base separation. WALE may under-predict subgrid dissipation in the high-shear rear-slant region |
| Decision tree |  |
| Stage A (diagnose) | Cd_pressure / Cd_friction decomposition (case_010 `scripts/10c_compute_cd_decomposition.py`): if Cd_pressure dominates (> 80% of total), separation-driven; if Cd_friction dominates, skin-friction-driven (different cause; see S20). Visualize Q-criterion isosurfaces near rear base — over-predicted separation shows as too-large recirculation bubble + premature reattachment downstream |
| Stage B (WALE Cw tune) | `templates/turbulenceProperties_LES.j2.WALECoeffs.Cw` default 0.325. Reduce to 0.25 (less aggressive subgrid eddy-viscosity in regions with strain-rate dominance) and rerun Stage B. Cost: ~5 FTs of compute. Risk: Cw too small lets numerical diffusion dominate → opposite problem (under-resolved structures) |
| Stage C (model swap · dynamicKEqn) | `08c_write_les_turbulenceProperties.py --les-model dynamicKEqn`. dynamicKEqn computes Cw locally per-cell from the resolved scales (Germano dynamic procedure) — typically more accurate near separations but ~30% more expensive per timestep. v2 fallback per Codex brief |
| Stage D (mesh fix) | If v2 stage fails → mesh is the limiter. Bump body level (4,5) → (5,6) AND wake box level (3) → (4); rerun sHM. Cost: 3-5× total cells |
| Failure mode A — Cd over-predicts by < 5% | Acceptable for wall-modeled half-domain LES with stationary wheels. The TUM Cd ≈ 0.281 reference ALSO has wheel/floor-rotation modeling that case_010 v1 simplified away. **Fix**: not a fix — document as "consistent with stationary-wheel/half-domain caveats" in v3 REPORT.md |
| Failure mode B — Cd UNDER-predicts | Different cause: typically y+ over-resolved (S20 failure A) or AVeraging window too short (S19 failure B). **Fix**: revisit S20 + S19 first before tuning WALE |
| Productizable artifact | None in v1; v3 candidate `cd_decomposition_post_processor.py` |
| Reference | case_010_drivaer_fastback_les v1 templates (`turbulenceProperties_LES.j2` parameterized on `les_model`); v2 fallback path documented |
| **V-row anchors** | V45 (LES infrastructure) |

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
