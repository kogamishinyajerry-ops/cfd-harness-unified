# Industrial Case Solver/Mesh Findings Index (V-series)

> **Living document.** Append a new row whenever an industrial CFD
> case (case_002+) surfaces a solver-internal or mesh-internal
> failure mode. SSOT for all engineer-facing solver/mesh failure
> modes during industrial CFD on the workbench.
>
> **Companion**: `.planning/methodology/solver_convergence_playbook.md`
> (decision tree). The V-series is the case audit trail; the
> playbook is the lookup tree.

## Why this index exists (parallel to F-series)

The B-extend arc (DEC-V61-172 .. V61-197) accumulated F1-F15
**persona-facing** failure modes — workbench REST API surface gaps,
route taxonomy mismatches, OpenAPI descriptors that misled the
DeepSeek persona. F-series is the SSOT for that surface
(`workbench_persona_findings.md`).

But the F-series misses an entire failure axis: **engineer-facing
solver / mesh internals** that only surface when a real engineer
drives an industrial CAD case end-to-end. These do not show up
when a persona drives a 2829-cell backward_step LDC; they only
emerge under industrial conditions (943k cells, multiple compressible
boundary types, kωSST + buoyancy, thin walls + narrow gaps from
CATIA STEP exports).

The V-series captures these. F-series and V-series are
**complementary, non-overlapping**:

| axis | F-series | V-series |
|---|---|---|
| who drives | LLM persona (DeepSeek / GPT) | engineer (human + Claude Code) |
| surface | workbench REST API | OpenFOAM solver / mesh internals |
| substrate | toy cases (LDC, backward_step, NACA) | industrial cases (APU bay, ...) |
| symptom | HTTP 404, route taxonomy mismatch, OpenAPI ambiguity | NaN at iter 3, GAMG stuck, mesh skewness 4.0+ |
| fix scope | route handler / OpenAPI descriptor / persona prompt | solver config / preconditioner / mesh quality / BC initial guess |
| primary doc | `workbench_persona_findings.md` | this file + `solver_convergence_playbook.md` |

A finding rarely needs to be classified as both. If you cannot
decide, ask: "would this still happen if no LLM was in the loop?"
If yes → V-series. If no → F-series.

## Status legend

- **closed** — fully fixed and live-verified in at least one
  industrial case
- **partial** — mitigated; structural fix deferred (e.g., needs
  refactor in main project)
- **open** — known gap, not yet addressed
- **playbook** — codified in `solver_convergence_playbook.md`; no
  code fix needed (the knowledge is the fix)

## Findings index

### V1 · CATIA STEP `Part::insert` drops body labels

| field | value |
|---|---|
| Surface | FreeCAD CAD-ingest path; main project `geometry_ingest/stl_loader.py` |
| Engineer symptom | After STEP import, all body labels are auto-generated `Part`, `Part001`, etc. instead of CATIA names like `body_3` / `combustor_outlet`. Downstream `naming.yaml` cannot map labels to patch types |
| Root cause | FreeCAD's `Part::insert(filename, doc.Name)` is the documented STEP loader, but it does **not** preserve the named-body hierarchy. The undocumented `Import.insert(filename, doc.Name)` (from the `Import` module) does |
| Fix | Use `Import.insert()` instead of `Part::insert()`. APU bay `02_domain_subtract.py:102` demonstrates. Extracted as artifact A1 (`cad_ingest_freecad.py`) per DEC-V61-198 |
| Status | **partial** — APU bay uses workaround in case-local script; A1 extraction makes it main-project capability |
| Reference case | APU bay 2026-05-07 |
| Lesson | When a documented API is "almost what you want" but loses metadata, search for an undocumented sibling. The 60-second-import cost difference between Part::insert and Import.insert is meaningless compared to losing the entire patch-type mapping chain |

### V2 · BREP 1:1 face matching fails on CATIA non-manifold STEP exports

| field | value |
|---|---|
| Surface | FreeCAD geometry analysis path |
| Engineer symptom | Code that pairs `body_a.Face_i` with `body_b.Face_j` by BREP-level equality (FreeCAD `isSame()`) returns no matches. But visually, body_a and body_b clearly share an interface plane in the model |
| Root cause | CATIA STEP exports are often non-manifold at body interfaces — body_a's interface face and body_b's interface face occupy the same geometric plane but are distinct BREP entities (different vertex orderings, different parametric directions, different topology). FreeCAD's BREP comparison is too strict |
| Fix | Geometric (not topological) face matching: compare BoundBox + face area + face normal direction. Two faces match if their bounding boxes overlap by > 80%, areas differ by < 5%, and normals point toward each other (dot product < -0.5). APU bay `02_domain_subtract.py` `INTERFACE_SPECS` with `mode: shared`. Extracted as artifact A2 (`virtual_interface_detector.py`) per DEC-V61-198 |
| Status | **partial** — APU bay workaround in case-local script; A2 extraction productizes |
| Reference case | APU bay `apu_intake` patch (body_2 ↔ body_4) |
| Lesson | Industrial CAD exports are noisy. Geometric heuristics are more robust than topological equality on real-world data |

### V3 · `kOmegaSST` + zero IC → ω blowup at iter 3 → wall function NaN

| field | value |
|---|---|
| Surface | OpenFOAM solver internals; turbulence model + wall function chain |
| Engineer symptom | Solver crashes at iter 2-3 with `nut = nan`; backtrace points at `omegaWallFunction.evaluate` |
| Root cause | k-ωSST wall functions divide by `sqrt(k)`. Zero initial U → near-zero k near walls → ω blows to numerical infinity in one source-term step. See playbook S1 for full chain |
| Fix | (1) `laminar` for v1 baseline → restart kωSST from converged v1 IC. Or (2) `potentialFoam -writePhi` warm start before main solver. APU bay V4-V7 → V8 (laminar) |
| Status | **playbook** (S1) |
| Reference case | APU bay V4-V8 |
| Lesson | RANS models with wall functions assume non-zero turbulence near walls. SIMPLE solvers cannot manufacture that from a zero IC in one step |

### V4 · `GAMG p_rgh` agglomeration fails on prism + thin-wall meshes

| field | value |
|---|---|
| Surface | OpenFOAM linear solver; GAMG agglomeration |
| Engineer symptom | `p_rgh` residual flatlines at first iter; GAMG V-cycle reports "cannot reduce residual below tolerance" |
| Root cause | GAMG agglomeration produces ill-conditioned coarse-grid matrix when mesh has high cell-aspect-ratio prism layers + non-orthogonal cells from sHM on thin walls. See playbook S2 |
| Fix | Replace `GAMG` → `PBiCGStab` + `diagonal` preconditioner for `p_rgh`. Slower per iter but actually converges. APU bay V8-V9 |
| Status | **playbook** (S2) |
| Reference case | APU bay V8-V9 |
| Lesson | GAMG is the "default fast solver" but assumes well-conditioned meshes. Industrial sHM meshes on thin walls are often outside that assumption |

### V5 · `DIC` / `DILU` preconditioner SIGFPE on compressible buoyant matrices

| field | value |
|---|---|
| Surface | OpenFOAM linear solver; preconditioner setup |
| Engineer symptom | Solver crashes with floating-point exception inside `Foam::DICPreconditioner::calcReciprocalD`; not at a specific iter, can be iter 5 or iter 50 |
| Root cause | DIC/DILU computes reciprocals of diagonal entries. Compressible buoyant flow with high-T gradients produces moments where some diagonal entries become tiny / negative → reciprocal overflows. See playbook S3 |
| Fix | Replace `DIC`/`DILU` → `diagonal` preconditioner globally. APU bay V10-V11 |
| Status | **playbook** (S3) |
| Reference case | APU bay V10-V11 |
| Lesson | DIC is more accurate per iter but is fragile on bad matrices. `diagonal` is the universal "stability over speed" choice |

### V6 · Mass-flow BC + zero IC → `\|U\| = 1e+129` first-iter divergence

| field | value |
|---|---|
| Surface | OpenFOAM BC + SIMPLE solver coupling |
| Engineer symptom | Solver runs iter 1, log shows `max(\|U\|) ~ 1e+129` and `min(rho) = -0.5`; subsequent iter has all NaN |
| Root cause | `flowRateInletVelocity 7.7 kg/s` on small inlet implies |U| ≈ 65 m/s. SIMPLE solver from |U|=0 IC must construct entire flow field in one shot; URF cannot absorb the impulse. See playbook S4 |
| Fix | (1) `potentialFoam -writePhi -initialiseUBCs` warm start (cheap). Or (2) replace mass-flow with pressure-based BC for v1 baseline (APU bay V13 path). Or (3) switch to transient `buoyantPimpleFoam` |
| Status | **playbook** (S4) |
| Reference case | APU bay V11-V13 |
| Lesson | Steady-state SIMPLE solvers are not robust to "flow-rate impulse on cold start". Either warm-start the velocity field, or relax the BC for v1, or pay the wall clock for transient |

### V7 · Compressible flow `ρ` goes negative → solver explodes

| field | value |
|---|---|
| Surface | OpenFOAM thermophysics; compressible solvers |
| Engineer symptom | Solver log shows `min(rho) = -0.5`; subsequent fields go to NaN |
| Root cause | Compressible solvers derive ρ from p,T. If p_rgh becomes locally negative or T crashes through thermophysics range bound, ρ derivation produces non-physical value. See playbook S5 |
| Fix | `fvOptions` clipping: `limitTemperature [250, 1500] K` AND `limitVelocity ≤ 200 m/s`; both required, one alone insufficient. APU bay templates do this |
| Status | **playbook** (S5) |
| Reference case | APU bay V11-V12 |
| Lesson | Compressible solvers do not auto-clip ρ. The engineer must add `fvOptions` limiters to bound T+|U|, indirectly bounding ρ |

### V8 · Mesh `max skewness > 4` infects all linear solvers

| field | value |
|---|---|
| Surface | snappyHexMesh quality + linear solver stability |
| Engineer symptom | Solver fails with any of V3-V7 symptoms despite correct BC + solver choices; log shows occasional `bounding e:` or `bounding U:` warnings |
| Root cause | sHM on thin walls + narrow gaps produces small fraction of badly-shaped cells. These act as numerical singularities; preconditioner choice cannot save them. See playbook S6 |
| Fix | (1) Tighten `meshQualityControls`: `maxBoundarySkewness 4`, `maxInternalSkewness 2`. (2) Geometry surgery before meshing (decimate + microdilate; A3 extraction). (3) Bump refinement levels on problem patches |
| Status | **playbook** (S6); A3 productizes geometry surgery |
| Reference case | APU bay V12 |
| Lesson | Mesh quality is a numerical safety margin. Loose meshQualityControls means sHM accepts cells that contaminate the linear system regardless of downstream choices |

### V9 · `0/` directory missing after sHM → solver fails at startup

| field | value |
|---|---|
| Surface | Workflow orchestration; `0.orig/` → `0/` copy |
| Engineer symptom | Solver fails with `cannot find file 0/U` immediately at startup |
| Root cause | Workflow is sHM → `cp -r 0.orig 0` → BC writer modifies `0/`. If the copy step is skipped (e.g. user re-runs sHM without cleanup), `0/` is empty or stale. See playbook S7 |
| Fix | Solver runner script must check `0/` exists before invoking solver. APU bay `09_run_solver.sh` does this; main project `case_solve/solver_runner.py` should adopt |
| Status | **partial** — APU bay has the check; main project does not |
| Reference case | APU bay throughout |
| Lesson | The `0.orig/` ↔ `0/` distinction is a load-bearing OpenFOAM convention. Tooling must enforce it |

### V10 · sHM ate thin walls; BC writer silently drops missing patches

| field | value |
|---|---|
| Surface | snappyHexMesh refinement levels + BC writer patch existence check |
| Engineer symptom | Mesh log says "boundary 26 patches" but case.yaml expected 32. `08_write_bcs.py` reports `skipped: beam_3 (not in mesh)`. Solver runs but a thin wall is now silently a fluid interior cell |
| Root cause | sHM with `refinementSurfaces.<patch>.level [1,2]` (level 1 = 40 mm) on a 50 mm thick beam. Two opposing surfaces of thin wall are inside same level-1 cell; sHM merges, patch ceases to exist. See playbook S8 |
| Fix | (1) Bump to `[2,3]` (10 mm). (2) Use `refinementRegions` with a slab. (3) Accept as v1 simplification (APU bay path: 6/32 patches lost, ventilation result unaffected) |
| Status | **playbook** (S8); needs main-project advisor surface to flag this |
| Reference case | APU bay V13 (REPORT.md §3.4) |
| Lesson | Refinement-level selection on thin walls is a pre-meshing decision that cannot be recovered post-meshing without re-running sHM. Advisor should warn when surface refinement level is coarser than wall thickness |

### V11 · `nut` / `alphat` initial fields with wrong BC types → wall function NaN

| field | value |
|---|---|
| Surface | OpenFOAM derived turbulence fields; initial condition templates |
| Engineer symptom | Variant of V3: solver dies at iter 1, log shows failure inside `nut.boundaryField` evaluation, not omega |
| Root cause | `nut` and `alphat` need correct boundary types per patch type (`nutUSpaldingWallFunction` on walls, `calculated` on inlets). Generic `0/nut` (e.g. all `zeroGradient`) → wall evaluation 0/0 = NaN. See playbook S9 |
| Fix | Generate `0/nut` and `0/alphat` from same SSOT YAML + Jinja2 template that generates `0/U`, `0/p_rgh`. APU bay does this; main project `case_bc/writer.py` partial |
| Status | **partial** — APU bay templates have it; main project derives some fields and not others |
| Reference case | APU bay V4-V8 |
| Lesson | Derived fields (`nut`, `alphat`, `epsilon` from k+ω, etc.) are not optional initial conditions. Each needs the same SSOT-driven BC type derivation as primary fields |

### V12 · Mass conservation only checked at verdict stage → too late

| field | value |
|---|---|
| Surface | Multi-inlet / multi-outlet case configuration |
| Engineer symptom | Solver runs to completion; verdict reports continuity error 12% > tolerance 5%. Days wasted; the case had imbalanced inlet vs outlet mass flows from the start |
| Root cause | Sum of inlet `mdot` ≠ Sum of outlet `mdot` in `case.yaml`. Currently only caught after solver finishes. The user-input error is detectable at dict-render time but not checked there |
| Fix | Pre-flight check: at `05_make_dicts.py` (or main project `case_bc/writer.py`), sum inlet `mdot` and outlet `mdot`; fail-fast if `\|in − out\| / max(in,out) > tolerance`. APU bay `case.yaml.mass_balance.tolerance: 0.05` defines the threshold; check should run before any dict writes. Extracted as artifact A4 per DEC-V61-198 |
| Status | **open** — APU bay implements at user-input level; A4 extraction wires into main project |
| Reference case | not yet observed in production (preventive) |
| Lesson | Verdict-time checks are too late. Configuration-time checks save hours of solver wall-clock |

### V13 · Pseudo-steady residual oscillation accepted as v1 baseline

| field | value |
|---|---|
| Surface | Compressible buoyant flow + steady-state SIMPLE convergence |
| Engineer symptom | Residuals stop decreasing after ~50 iter, oscillate ±1 order around floor; continuity error < 1% but not zero. Engineer must decide: accept v1 or escalate to v2 transient |
| Root cause | Strong T gradient (873K vs 328K) + buoyancy + SIMPLE relaxation = unable to reach true steady state. p ↔ ρ ↔ U ↔ T feedback loop is undamped. See playbook S10 |
| Fix | Three options, depending on engineering goal: (1) accept pseudo-steady as v1 baseline, document continuity error magnitude, layer v2 transient on top. (2) Increase iter budget + lower URF (slow). (3) Switch to `buoyantPimpleFoam` transient (correct physics, expensive) |
| Status | **playbook** (S10) |
| Reference case | APU bay V13 (REPORT.md §5.4) |
| Lesson | Pseudo-steady is a legitimate v1 baseline, not a failure. The engineer's job is to decide whether v1 is enough for the question being asked, not to chase production physics on v1 |

## Cross-cutting patterns observed

### Pattern 1 — Zero IC is the universal first-iter killer

V3, V6, V11 are all variants of "first iter has no flow field, derived
quantities go to garbage". `potentialFoam -writePhi` warm start is
the single highest-leverage fix; main project should make it the
default for any compressible / buoyant / multi-BC case.

### Pattern 2 — Preconditioner choice trumps solver choice

V4, V5 both resolve by changing preconditioner, not solver. The
default OpenFOAM `DIC` / `GAMG` choices are tuned for academic
benchmark cases; industrial sHM meshes need `diagonal` /
`PBiCGStab` instead. Main project default fvSolution should reflect
this.

### Pattern 3 — Mesh quality is a numerical safety margin

V8 underlies V3-V7 in many real cases. Tightening
`meshQualityControls` is preventive medicine; loose controls let
sHM accept cells that contaminate everything downstream. A3
(geometry surgery) attacks this at the geometry source.

### Pattern 4 — Configuration-time checks beat verdict-time checks

V12 (mass conservation pre-flight) is the canonical case. Same
pattern likely applies to: BC type ↔ patch type consistency,
turbulence model ↔ wall function compatibility, solver ↔ schemes
compatibility. Each of these can fail at runtime but is detectable
at configuration time.

### Pattern 5 — v1 simplification is not a failure mode

V3 (laminar fallback), V6 (pressure BC instead of mass-flow), V13
(pseudo-steady) are all "the production physics did not work; the
v1 simplified version did". This is the correct engineering
sequence: get a working baseline, then layer complexity. Tooling
should encourage this, not penalize it.

## How to add a new V-finding

1. Industrial case surfaces a death mode not in V1-V13
2. Add a row here with: Surface / Engineer symptom / Root cause /
   Fix / Status / Reference case / Lesson
3. If the death mode generalizes → add a new section (S11+) to
   `solver_convergence_playbook.md`
4. If the death mode requires main-project code change → file as
   sub-DEC under DEC-V61-198 (or a future M2.5/M4-class DEC)
5. If the death mode reveals a new cross-cutting pattern → add to
   "Cross-cutting patterns observed" above

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision; declares
  V-series complementary to F-series)
- `solver_convergence_playbook.md` — decision tree (S1-S10 mapped
  from V3-V13)
- `workbench_persona_findings.md` — F-series companion index
- `~/Desktop/apu-bay-ventilation/evidence/v13_post_v5_183632/REPORT.md`
  — V3-V13 audit trail
