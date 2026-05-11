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
| Status | **closed · field-validated** — A2 advisor landed 2026-05-08 (commit `a09ae0a`). 11 unit tests + first **industrial cross-topology field validation** by case_003 sub-session 2026-05-08: D1 (0.35 mm Z-axis gap between two CadQuery axis-aligned planar boxes `root_mount_pad` ↔ `root_mount_cover`) detected with `bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`, `normal_dot=1.0`, matched face area 3.48e+07 mm² (pad's top face). Confirms `_run_shared` design is correct: it relies on `find_face_facing_target` (normal-only), NOT on `faces_match_shared` / `bbox_overlap_fraction` (which would zero-out on planar-box face bboxes whose volume is 0). Note: this contradicts the spirit of V19 (case_005 reported A2 false negative on D1-class flange gap); see V21 for the divergence-investigation finding. |
| Reference advisor | `ui/backend/services/geometry_ingest/virtual_interface_detector.py` |
| Reference cases | APU bay `apu_intake` (body_2 ↔ body_4, curved CATIA non-manifold); case_003 root_mount_pad ↔ root_mount_cover (planar CadQuery boxes, Z-axis gap); case_004 nacelle_body ↔ nacelle_service_cover (planar CadQuery boxes, Y-axis gap, rotating-machinery topology, 2026-05-08) |
| Lesson | Industrial CAD exports are noisy. Geometric heuristics are more robust than topological equality on real-world data. V2 lesson explicitly preserved in advisor docstring: do NOT add `isSame()` fast-path (reintroduces the bug). **Cross-topology validity confirmed across 3 cases 2026-05-08**: case_002a (curved CATIA non-manifold), case_003 (planar CadQuery Z-axis gap), case_004 (planar CadQuery Y-axis gap, rotating-machinery topology) — all PASS via `_run_shared`. The `_run_shared` algorithm's normal-direction-only matching is the right primitive for axis-aligned planar geometry. case_005 V19 FAIL surfaces a curved-flange-geometry scope gap; per V22 (case_004), V21 cross-case investigation now has 3 PASS cases on the axis-aligned-planar regime, weighting V21's hypothesis toward "case_005-failure is curved-geometry-specific, not all D1-class" |

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
| Fix | (1) Bump to `[2,3]` (10 mm). (2) Use `refinementRegions` with a slab. (3) Accept as v1 simplification (APU bay path: 6/32 patches lost, ventilation result unaffected). (4) **Pre-meshing advisor warns** — `ui/backend/services/geometry_ingest/thin_wall_advisor.detect_thin_wall_patches_at_risk` flags any patch where bbox-min is < 2× effective cell size at assigned level; landed 2026-05-07 driven by case_002b inheritance |
| Status | `[VALIDATED 2026-05-08 4-of-4]` (advisor landed; cross-topology consistency: 4-of-4 across (curved CATIA shell, planar CadQuery aero, rotating-machinery aux, ship-hydro above-WL transom)) — pre-meshing path warns; case-local accept remains legitimate once warned. case_007 ship-hydro 0.80 mm transom plate flagged `severity=critical` with `cells_per_thickness=0.044`, `recommended_level_max=8` — same monotonic behavior as cases 002a/003/004. |
| Reference cases | case_002a V10 (original, curved Frame patches); case_002b CHT v1 (inherited unchanged → triggered advisor extraction); case_003 D8 (first planar-plate validation 2026-05-08); case_004 D8 yaw_sensor_shim (rotating-machinery aux instrumentation, 0.75 mm planar shim, 2026-05-08); **case_007 D8 stern_transom_plate_thin (ship-hydro above-waterline auxiliary plate, 0.80 mm, 2026-05-08)** |
| Lesson | Refinement-level selection on thin walls is a pre-meshing decision that cannot be recovered post-meshing without re-running sHM. **Pillar 2 example**: a finding that recurred across two case threads on the same physical geometry is a signal to land a main-project advisor, not just to document. Advisor uses bbox-min heuristic (exact for axis-aligned plate/beam; lower-bound for curved shells) — case_003 confirmed both regimes flag correctly. **4-of-4 cross-topology consistency (2026-05-08)**: curved CATIA Frame (002a/b), planar CadQuery aero plate (003), rotating-machinery aux shim (004), ship-hydro above-WL transom plate (007) — all flag at consistent severity progression. The bbox-min heuristic robustness across these four topologies is now strong enough to count as a validated advisor pillar; further cases extend the evidence but the structural finding is settled |

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

### V14 · CHT post-processing reports `T = ±1e+300` for solid regions, but no time directories were ever written

| field | value |
|---|---|
| Surface | post-processing / final-time-frame inspection of multi-region case |
| Engineer symptom | `report_v1.md` of case_002b CHT v1 stated "T_min/T_max per region: solid_outer 1e+300 / -1e+300, ..." across all 6 solid regions; appearance of catastrophic divergence |
| Root cause | The chtMultiRegionSimpleFoam solver crashed mid-Time=1 (setup-time issue, exact mechanism unclear from truncated log; viewFactor radiation suspected). **No time directory beyond `0/` was ever written.** When 11_post.py iterated time directories looking for solid T fields, OpenFOAM's "field not found" path returned the sentinel `±std::numeric_limits<double>::max()` (~ ±1.8e+308 / displayed as ±1e+300). The "divergence" was an interpretation bug — there was no run to diverge from |
| Fix | Verify time directories exist before diagnosing solid-region divergence: `ls case/[0-9]*` should show ≥ 2 entries (`0/` plus at least one written step). For the underlying setup-time crash: drop radiation for v2 baseline (matches case_002a v1 pattern of "v1 simplification then restore later") |
| Status | **closed** (interpretation bug captured; v2 norad path bypasses the original setup-time crash) |
| Reference case | case_002b CHT v1 → v2 norad |
| Lesson | When a multi-region CFD post-processor reports physically impossible field values (e.g. `T = ±1e+300`), **always check whether time directories were actually written first**. OpenFOAM's missing-field sentinel can masquerade as a divergence signal. Post-processing tooling should fail loudly when asked to read fields from a run that produced no time output, instead of silently returning sentinels |

### V15 · CHT fluid-side `limitTemperature` clamping 3-5% of cells per iteration (V5 pattern crosses solver families)

| field | value |
|---|---|
| Surface | OpenFOAM compressible thermophysics + multi-region solver; chtMultiRegionSimpleFoam fluid sub-solver |
| Engineer symptom | Solver runs without crashing; per-iter log shows `limitTemperature limitT Lower limited 43308 (3.28%) of cells with min limit 280; Upper limited 27233 (2.06%) cells with max limit 1100`. Percentage rises from 0% at iter 1 to 5%+ by iter 67. The clamp is doing real work, not occasional intervention |
| Root cause | Same root pattern as V5 (compressible ρ/T runaway under strong gradients). Fluid-region energy equation in chtMultiRegionSimpleFoam is structurally identical to buoyantSimpleFoam's: pressure-velocity-density coupling on a fluid cell zone. Multi-region wrapping does not change the fluid-internal numerics. With strong T gradients (873 K APU body wall heat sources + 328 K freestream + buoyancy) and steady-state SIMPLE relaxation, fluid cells near hot patches will continually overshoot the thermophysics range without the clamp |
| Fix | Same fix family as S5 (compressible ρ runaway): (1) keep `fvOptions limitTemperature` clamp; (2) lower URF on `h` from 0.40 → 0.20; (3) v2 simplification path = also drop kωSST → laminar (matches case_002a V3 → laminar fallback); (4) long-term v3 = transient `chtMultiRegionPimpleFoam` to let physical time damp the gradient |
| Status | **partial** — currently mitigated by clamps; structural fix deferred to v3 transient or v3 restart-with-radiation path |
| Reference case | case_002b CHT v2 norad |
| Lesson | **V-series findings inherit across solver families** when the fluid-internal numerics are shared. case_002b CHT inherits V5, V6, V7 from case_002a buoyantSimpleFoam because chtMultiRegionSimpleFoam wraps the same fluid-side energy/momentum solver. The corpus should index by **fluid-side numerics class** (compressible-buoyant-RANS, incompressible-RANS, compressible-shock, etc.) not by solver name. New V-findings emerge from multi-region-specific surfaces (region pairing, faceZone, extrusion); fluid-internal V-findings are inherited |

### V16 · Codex `cq.Compound.makeCompound([Face,...])` STEP export fragments through FreeCAD as N standalone Part::Feature objects

| field | value |
|---|---|
| Surface | Codex case-design CAD export pattern; FreeCAD STEP loader; defect-manifest verification command |
| Engineer symptom | Defect manifest declares `expected_face_count: 102400` for `throat_liner_overdense` and provides verification command `len(o['throat_liner_overdense'].Shape.Faces)`. After STEP roundtrip via FreeCAD `Import.insert()`, the call returns **1**, not 102,400. The doc has 102,425 objects total (8 named bodies + 102,400 numbered `throat_liner_overdense001..throat_liner_overdense102400`) — each triangle face arrived as its own Part::Feature object |
| Root cause | Codex's `build_overdense_liner()` generated 102,400 standalone `cq.Face` objects and packed them via `cq.Compound.makeCompound(faces)`. cadquery's STEP exporter emits each face as a separate top-level entity (no parent solid wrapping the compound). FreeCAD's STEP loader correctly creates one Part::Feature per top-level entity. The verification command pattern (single-object `Shape.Faces`) was written assuming a single `Solid` wrapping the over-dense triangulation |
| Fix | (1) **Sub-session workaround**: aggregate by label prefix — sum `Shape.Faces` across all `throat_liner_overdense*` objects; this returns the correct over-density measurement (102,401 objects × 2 sub-faces = 204,800 in case_005). (2) **Upstream Codex CAD pattern**: emit a single `cq.Solid` (or `cq.Shell`) wrapping the over-dense triangulation, OR document that the verification command must use prefix aggregation. (3) **Bypass for downstream pipeline**: parametric trimesh regeneration for STL extraction (case_005 `01_extract_stl.py`) — sidesteps the issue entirely for the meshing pipeline |
| Status | **partial** — case-local workaround in case_005; future Codex case-design protocol revision needed (recommendation: update `codex_case_design_protocol.md` to require "single Solid or single Compound wrapping the over-density" for D2-class defects) |
| Reference case | case_005_rae_m2129_sduct (2026-05-08) |
| Lesson | Defect-manifest verification commands must match the actual STEP-roundtrip structure, not the generation-side intent. When a generator produces N entities and the importer faithfully creates N entities, single-object verification underreports by factor N. Future case-design prompts should specify both the **face count** AND the **structural form** (one Solid with N faces vs. N solids with 1 face each) |

### V17 · A3 advisor (`geometry_surgery.decimate_to_tier`) lacks redundancy/overlay-detection logic

| field | value |
|---|---|
| Surface | Main-project advisor `ui/backend/services/geometry_ingest/geometry_surgery.py`; advisor scope vs. industrial-CAD pre-meshing semantic |
| Engineer symptom | A3 was **landed** (extracted from APU bay v14 as artifact A3 per DEC-V61-198, 2026-05-07). Its public API is `decimate_to_tier(mesh, tier)` + `axial_stretch(mesh, spec)` + `apply_surgery(meshes, tiers, stretches)`. case_005 D2 (`throat_liner_overdense`) is a 102,400-triangle wall overlay offset 0.15 mm INTO the solid side of `duct_wall_reference` — i.e., it's a redundant duplicate of the duct wall, not a "needs-decimating" body. A3 has no API surface to recommend "DROP" vs "DECIMATE" — calling `decimate_to_tier` on the overlay produces a clean 8k-25k face mesh that is then accepted by sHM as a wall body, leaving a redundant wall surface in the meshed case |
| Root cause | A3's design scope was tied to APU bay v14's specific geometry-surgery problem set (over-dense CATIA exports + thin-shell axial-gap closure). It treats every input as "needs-decimation"; there is no upstream classification step. The toy-case bias is in *advisor scope*, not in *parameter values* — TIER_APU_BODY / TIER_THIN_SHELL / TIER_STRUCTURE presets all clamp to `max_faces ≤ 15000`, which works fine on industrial 102k-face input |
| Fix | (1) Add `classify(mesh, context) -> "drop" \| "decimate" \| "preserve" \| "repair"` upstream of `decimate_to_tier`. (2) Add `detect_redundant_overlay(mesh_a, mesh_b, tolerance_mm)` helper — heuristics: Hausdorff distance < tolerance + signed-distance check vs neighboring named bodies + shell-offset normal alignment. (3) Document A3 contract: decimation alone is not sufficient for industrial CAD pre-meshing; the engineer must classify before calling `decimate_to_tier`. (4) **Sub-session workaround**: case_005 `01_extract_stl.py` simply does not generate the overlay surface — manual enactment of the engineering-correct decision |
| Status | **open** — A3 first industrial falsification surfaces the gap; main-project sub-DEC under DEC-V61-198 recommended once a 2nd case (case_004 D8 or case_007 D8 likely) surfaces the same scope-narrowness pattern |
| Reference case | case_005_rae_m2129_sduct A3 falsification (2026-05-08, evidence/v1_a3_falsification.json) |
| Lesson | When a landed advisor's "first industrial falsification" returns PARTIAL because Q1+Q2 (does it run? does it preserve geometry?) PASS but Q3 (does it warn / classify correctly?) FAILs, the advisor's *scope* is too narrow, not its parameters. Toy-case bias can hide in the *absence* of a classification step rather than the *values* of a threshold. **A3's first industrial falsification was the entire reason case_005 was first dispatched per the case_proposal_queue** — and that signal is now captured |

### V19 · A2 advisor (`virtual_interface_detector`) lacks sub-mm gap-as-defect detection — V2-pattern only

| field | value |
|---|---|
| Surface | Main-project advisor `ui/backend/services/geometry_ingest/virtual_interface_detector.py`; advisor scope vs. D1-class defect signature (sub-mm gap between bodies that should share an interface) |
| Engineer symptom | A2 was landed at commit a09ae0a as the V2 finding's productized form (geometric face matching for shared interfaces on non-manifold STEP exports). case_005 D1 (`inlet_flange_ring` + `inlet_flange_cover` separated by 0.35 mm axial gap) is a defect manifest entry whose `expected_advisor_to_catch: virtual_interface_detector_pending_A2` implies A2 should detect this. Falsification result: A2's `faces_match_shared` returns `False` for the two flange faces — correctly per its bbox-overlap + area-match + opposing-normals heuristic, because the faces are 0.35 mm apart in x and their thin x-extent bboxes do not overlap |
| Root cause | A2's design scope is the V2 pattern: detecting interfaces where two bodies SHARE a plane and the BREP `isSame()` would have failed due to non-manifold STEP export noise. The heuristics (bbox overlap, area match, opposing normals) are exact for V2 — the bodies are in CONTACT. They are NOT designed for D1 — bodies that SHOULD have been shared but are separated by a sub-mm gap. The toy-case bias is in advisor scope (V2-only), not in parameter values. Same shape as V17 (A3 advisor scope gap), different advisor — case_005 surfaces a 2-of-2 pattern of "scope-narrowness bias" in landed advisors |
| Fix | (1) Add `should_have_been_shared(face_a, face_b, max_gap_mm)` helper: if normal_dot < -0.5 AND area_diff_fraction < 0.05 AND axial-distance-between-centroids < threshold AND bbox-with-x-extension overlap > 0.8 → flag as D1-class defect candidate. (2) Add `detect_unintended_gap(face_a, face_b, max_gap_mm) -> bool` upstream of `faces_match_shared`. (3) Document A2 contract: it detects shared interfaces (V2 pattern), not gap-as-defect (D1 pattern); the engineer must run `detect_unintended_gap` separately. (4) **Sub-session workaround for case_005**: D1 verified manually via FreeCAD `distToShape(...)[0]` (returns 0.35 mm exact) — see `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_defect_verification.json`. The two flange bodies were dropped from sHM input via `01_extract_stl.py` regardless (case_002a-style v1 simplification — flanges are external upstream of throat) |
| Status | **superseded by V25 (2026-05-08 v2 disambiguation)** — original mechanism diagnosis was code-path-incorrect (see V21 closure); the conclusion "A2 cannot signal D1" survives but in a sharper form per V25 (silent-placeholder semantic). Compounded with V17 (A3 scope gap) → main-project sub-DEC under DEC-V61-198 recommended for "advisor-scope-expansion" arc covering both A2 (D1 pattern, V25-shape) and A3 (D2 redundancy pattern) |
| Reference case | case_005_rae_m2129_sduct A2 falsification (2026-05-08 v1, evidence/v1_a2_falsification.json); V21 disambiguation (2026-05-08 v2, evidence/v2_a2_run_shared.json) |
| Lesson | When the kickoff prompt described A2 as "pending" but the codebase shows A2 has been landed, **always verify the codebase before acting on the kickoff narrative**. The kickoff text was stale — A2 is landed for the V2 pattern. case_005 then surfaces the *next* gap in A2's scope: D1's gap-as-defect signature is a different scope axis from V2's shared-interface signature. **Followup (V21 disambiguation 2026-05-08 v2)**: V19 v1 used `faces_match_shared` (lower-level helper) and got `matched=False` due to bbox-volume-zero edge case on planar geometry — but the public API `detect_virtual_interfaces -> _run_shared` instead returns `matched=True` with hardcoded placeholder fields (`bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`) that hide the 0.35 mm gap. The advisor's API surface cannot distinguish "shared" from "should-be-shared-but-isn't" — see V25. **Lesson refinement**: sub-sessions invoking advisors should specify which entry-point was used; the lower-level helpers (`faces_match_shared`, `bbox_overlap_fraction`) have different (often stricter) behavior than the public orchestrator (`_run_shared`) |

### V25 · A2 advisor (`_run_shared`) cannot distinguish "shared interface" from "should-have-been-shared-but-isn't" — silent placeholder semantic

| field | value |
|---|---|
| Surface | A2 advisor public API `detect_virtual_interfaces -> _run_shared`; `DetectedInterface` result schema; cross-case advisor PASS interpretation |
| Engineer symptom | `_run_shared` (lines 179-204 of `virtual_interface_detector.py`) returns a `DetectedInterface` with `matched=True` whenever it finds a face on either body whose normal aligns with the centroid-direction. The result fields `bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0` are **hardcoded placeholders** (line 200-201), not measurements. The actual inter-face gap distance is never computed and never returned. case_005 D1 (0.35 mm flange gap, V21 disambiguation 2026-05-08 v2): `_run_shared` returns `matched=True` for both orderings (ring↔cover and cover↔ring), `body_owner='inlet_flange_ring'` or `'inlet_flange_cover'`, hardcoded `bbox_overlap_fraction=1.0`. Identical positive output as case_003 (clean 0.35mm gap, reported as PASS) and case_004 (clean 0.30mm gap, reported as PASS). All three cases — case_003 D1 + case_004 D1 + case_005 D1 — produce the SAME result shape from `_run_shared`. The advisor cannot tell the engineer whether the gap is 0 mm (clean shared interface) or 0.35 mm (defective separation). |
| Root cause | `_run_shared`'s contract is "find a candidate facing-face on each body when the engineer SAYS via InterfaceSpec(mode='shared') that they SHOULD share an interface" — this is a confirmation step for the V2 pattern (BREP `isSame()` failed on non-manifold STEP, but the bodies are in geometric contact and the engineer needs to retain that interface as a shared OpenFOAM patch). It was NOT designed to detect the COMPLEMENTARY case: bodies the engineer SHOULD share but accidentally didn't (D1 sub-mm gap defect). The result schema reflects the V2 design intent: matched=True/False is enough to drive the patch-emission code; the geometric measurements (`bbox_overlap_fraction`, `area_diff_fraction`, `normal_dot`) are only meaningful in the `_run_endcap` path — for `_run_shared` they are stub placeholders. Reading the code, the two `1.0` and `0.0` literals on lines 200-201 are documentation-via-default, not computed quantities |
| Fix | (1) **A2 v2 API extension**: add `inter_face_gap_mm: float | None` field to `DetectedInterface`; populate from `||fa.centroid - fb.centroid||` projected onto the centroid-direction (or use the perpendicular distance between the two facing-face planes) when both fa and fb are non-None. (2) Add `should_have_been_shared_with_unintended_gap(detected, max_gap_mm) -> bool` classifier downstream of `detect_virtual_interfaces`: returns True when `matched=True` AND `inter_face_gap_mm > 0` AND `inter_face_gap_mm < max_gap_mm`. (3) Compute and return real `bbox_overlap_fraction` / `area_diff_fraction` measurements in `_run_shared` (currently placeholders) so cross-case PASS reports can be compared on actual measurements, not on positive-vs-negative verdict alone. (4) Document A2 contract: "matched=True does NOT imply gap=0; the engineer must check `inter_face_gap_mm` separately." (5) **Sub-session implication**: case_003 and case_004 sub-sessions reported A2 PASS as positive evidence the advisor "works" — under V25, those PASSes confirm only that `find_face_facing_target` runs and finds candidate faces. They do NOT field-validate A2 as a gap-defect detector, because A2 has no gap-defect detector. **Recommend main session re-interpret case_003 + case_004 reference profiles** to clarify A2's PASS = "advisor algorithm runs cleanly + finds facing-face candidates on axis-aligned bodies" (true), NOT "advisor detects sub-mm gap as defect" (the latter requires V25's API extension that is not yet implemented) |
| Status | **open** — first sourced 2026-05-08 v2 in case_005 V21 disambiguation. Not visible from case_003 / case_004 alone because their PASS reports only printed `matched=True` (which IS the placeholder output). Visible from V21 cross-case investigation when case_005 v1 FAIL provoked re-examination of the public API. Expected resolution: A2 v2 API extension as the first deliverable of the advisor-scope-expansion sub-DEC under DEC-V61-198 |
| Reference case | case_005_rae_m2129_sduct V21 disambiguation (2026-05-08 v2, `evidence/v2_a2_run_shared.json`); cross-case implication for case_003 + case_004 D1 PASSes (re-interpretation needed by main session) |
| Lesson | When an advisor's PASS report relies on a single boolean (matched=True), and the geometric measurement fields surrounding the boolean are HARDCODED PLACEHOLDERS rather than computed quantities, **the PASS does not validate what the engineer thinks it validates**. case_003 PASS confirmed "_run_shared finds facing-face candidates on axis-aligned planar boxes"; that's a real signal. It did NOT confirm "A2 detects sub-mm gap as defect" because A2's API has no surface for that signal. **Pillar 2 reinforcement**: case_005 V21 disambiguation surfaces a finding that affects how case_003 + case_004 PASSes should be interpreted — one industrial case can retro-correct multi-case sediment when it tests a code path the others missed. **Pattern 5 corollary**: V19's v1 verdict (PARTIAL) was directionally correct on the conclusion ("A2 doesn't catch D1") even though the mechanism diagnosis was wrong. v1 simplification's robustness depends on the conclusion being directionally correct; subsequent disambiguation can sharpen the mechanism without invalidating the v1 directional signal |

### V18 · Compressible-RANS pseudo-steady mass imbalance under SIMPLE + totalPressure inlet + coarse mesh

| field | value |
|---|---|
| Surface | rhoSimpleFoam compressible SIMPLE algorithm; totalPressure inlet ↔ fixedValue/waveTransmissive outlet coupling; coarse-mesh BC settling |
| Engineer symptom | Solver runs 0-500 iter without crashing. Tmin/Tmax bounded (255/389 K), no NaN, no SIGFPE, no V3-V7 patterns. **But**: residuals oscillate (Ux initial residual ~0.1-0.3 throughout, p ~0.005 throughout, no monotonic decrease). Cumulative continuity error grows (130,957 by iter 500). `surfaceFieldValue` reports phi_inlet = -1.51 kg/s, phi_outlet = +4.36 kg/s — **3× asymmetric mass flow**. Engineering metrics also off (AIP Mach 0.18 vs 0.40-0.60 target; PR=0.955 vs 0.839 nominal; DC60=0.351 vs ~0.10-0.20 typical) |
| Root cause | SIMPLE algorithm with totalPressure inlet + fixedValue p outlet, started from non-zero but rough initial U (case_005: 100 m/s axial), struggles to establish the inlet→outlet pressure ratio in a single relaxation pass per iteration. Compressible momentum equation lags the pressure update (URF p=0.20, U=0.50, e=0.20), and the coarse mesh (52k cells, no prism layers, 1,688 concave cells in the S-curve transition) does not have enough resolution to enforce wall-bounded boundary layer. Mass conservation does not lock in within 500 iter — the BC chain is in transient balance, not steady. Pattern 6: this is **compressible-RANS specific** (case_005 numerics-class root); not inherited from V13 (compressible-buoyant-RANS pseudo-steady) because the mechanism is different — V13's loop is p ↔ ρ ↔ U ↔ T (buoyancy-driven feedback), V18's loop is just p ↔ ρ ↔ U with the totalPressure-inlet enforcement struggling against the resistance of the unconverged interior |
| Fix | See playbook S13. Three options: (1) `potentialFoam -writePhi -initialiseUBCs` warm start (cheap); (2) lower URF further (p=0.10, U=0.30) + longer iter budget (2000-5000); (3) switch to rhoPimpleFoam transient (Codex's v2 fallback). For all three: refine mesh + add prism layers to give the BCs a properly-resolved interior to settle against. v1 case_005 chose path (2) only partially (URF already at 0.20, iter budget capped at 500) — V13-pattern v1 simplification, accept and document |
| Status | **playbook (S13) — sharpened by case_005 v2 evidence (2026-05-08 afternoon): URF-only path is INSUFFICIENT** |
| Reference case | case_005_rae_m2129_sduct v1 (2026-05-08 morning); **case_005 v2 (2026-05-08 afternoon, evidence/v2_final/REPORT.md)** |
| Lesson | Compressible-RANS pseudo-steady oscillation has the same coarse symptom as compressible-buoyant-RANS V13 (residuals oscillate, continuity error doesn't reach zero) but a different mechanism (BC-chain transient instead of buoyancy-coupled feedback). The S-family decision tree should NOT collapse "compressible pseudo-steady" into one entry; document the distinct entry point per numerics class. v1 simplification (Pattern 5) is legitimate — case_005 v1 baseline is the case_002a v13 analogue for compressible-RANS root. **v2 sharpening (2026-05-08 afternoon)**: case_005 v2 ran with URF.p=0.10 (v1: 0.20), URF.U=0.30 (v1: 0.50), iter 2000 (v1: 500), Sutherland transport. Result: Ux Initial residual dropped 30-70× (0.2-0.5 → 0.007-0.008), DC60 improved (0.351 → 0.264), but **inlet/outlet mass imbalance preserved at 2.8× (vs v1's 2.9×)**. URF damping made the SOLVER converge cleanly but the BC chain (totalPressure inlet + fixedValue outlet on coarse mesh) preserves the mass imbalance structurally. **Implication**: S13 path 2 (lower URF + extend iter) is necessary but NOT sufficient when totalPressure-inlet is the source — must combine with path 1 (potentialFoam warm-start) OR path 3 (rhoPimpleFoam transient) OR mesh refinement (prism layers + finer wall resolution). This is a **Pattern 5 v2 falsification of the implicit "URF-only might work" hypothesis** — v2 tested it and it didn't. The sediment value of v2 is the falsification, not convergence |

### V20 · Tier-1 STEP unit-context lost on cadquery roundtrip; defect dimensions absolute-mm collide with airframe at unknown scale

| field | value |
|---|---|
| Surface | Codex case-design CAD generation pattern; Tier-1 reference geometry import via `cadquery.importers.importStep`; bbox-derived domain sizing |
| Engineer symptom | case_003 build_cad.py reads HLPW6 CRM-HLS reference STEP and computes `bb = airframe.BoundingBox()` then derives downstream dimensions (defect placement, domain extent, aux-fixture box sizes) from `bb.xlen` etc. After STEP roundtrip via FreeCAD, the airframe semi-span loads as ≈ 91,440 mm = 91 m (real CRM-HLS half-span ≈ 30 m). The 25.4× ratio strongly suggests the published HLPW6 STEP is in INCH units that were treated as mm somewhere in the cadquery / FreeCAD chain. Defect dimensions (`DEFECT_GAP_MM = 0.35`, `THIN_PLATE_THICKNESS_MM = 0.80`) are hard-coded in absolute mm; they survive correctly (FreeCAD `distToShape = 0.35`, plate bbox-min = 0.80) but are at 1/25.4× their intended **relative-to-airframe** scale |
| Root cause | (1) cadquery's `importStep` does not surface the source STEP's `LENGTH_UNIT` declaration to user code — bbox extents come back in raw model units. (2) Downstream Codex script multiplies bbox-derived spans by chord-fraction defaults (e.g., `DEFAULT_CHORD_FRAC = 0.12` for root-pad length) without verifying the source unit. (3) Defect dimensions are absolute (mm), so they don't scale with the (unknowingly inches) airframe. Net: a self-consistent assembly at the wrong relative scale. (4) For Tier-1 NASA/AIAA STEP, INCH is common; project does not currently have a unit-detection / unit-rationalization pre-pass |
| Fix | (1) **Sub-session workaround for case_003**: defer CFD run; document scale issue. Defect verification + advisor field-validation are unit-independent (they operate on absolute mm features), so the v1 pause does not invalidate the V2/V10 field-validation outcomes. (2) **Main-project A1 extension**: when extracting `cad_ingest_freecad.py` (V1's productized form), include unit-detection — call `getUnit()` on the STEP entity tree, log declared unit, optionally rescale to mm. (3) **Codex case-design protocol revision**: require `--source-units` arg to build_cad.py, with `--source-units inch` triggering 25.4× rescale before adding defects. (4) **Defect-manifest schema extension**: add `units_in_step` field to parts_manifest.yaml (already present!) and validate it against actual loaded geometry before defect injection |
| Status | **open** — sub-session paused at v1 advisor-validation; CFD-blocking until scale resolution. Recommended sub-DEC under DEC-V61-198: A1 extraction with embedded unit detection (compounded with case_003 evidence) |
| Reference case | case_003_crm_hls_boundary_layer v1 (2026-05-08) |
| Lesson | Tier-1 reference geometry has implicit unit conventions (NASA STEP often inches; CATIA OEM exports often mm; ESI-CFD-prepared STEP often mixed). Codex's case-design template assumed source-unit = mm without verification. The defects in this case were correctly injected at absolute mm but the airframe is at unknown relative scale. **Pattern 4 echo**: this is a configuration-time check that should fire BEFORE CAD assembly, not a runtime check after STEP roundtrip. Future cases sourcing from NASA/AIAA Tier-1 must validate `LENGTH_UNIT` declaration in source STEP before relying on bbox-derived numbers |

### V21 · A2 advisor field-behavior contradiction across cases — case_003 PASS vs case_005 V19 FAIL on D1-class sub-mm gap

| field | value |
|---|---|
| Surface | A2 advisor cross-case behavior; advisor scope-vs-implementation trace |
| Engineer symptom | case_005 reported A2 false negative on D1 (V19: "A2's `faces_match_shared` returns `False` for the two flange faces — correctly per its bbox-overlap + area-match + opposing-normals heuristic, because the faces are 0.35 mm apart in x and their thin x-extent bboxes do not overlap"). case_003 sub-session 2026-05-08 ran the same advisor on a structurally analogous defect (0.35 mm Z-axis gap between two stacked planar boxes) and got matched=True with bbox_overlap_fraction=1.0. The disagreement is **structural**, not parametric |
| Root cause | Reading `_run_shared` source: the algorithm does NOT call `faces_match_shared` or `bbox_overlap_fraction` at all. It uses `find_face_facing_target` which only checks `normal · target_dir ≥ dot_min` (default 0.5) and picks the largest-area facing face. The bbox-overlap concern V19 cites is irrelevant to the actual code path. Two possible explanations: (a) case_005 invoked A2 via a different entry-point (e.g., `faces_match_shared` directly, or a wrapper pre-filter), making V19's diagnosis correct for that path but not for `_run_shared`; (b) case_005's flange geometry has face normals not aligned with the gap axis (e.g., flange faces are not flat-perpendicular to the gap direction, so `normal_dot < 0.5` against `ab_dir`), causing `find_face_facing_target` to return None — which IS a real scope gap but not the one V19 documents. Sub-session cannot disambiguate without case_005 sandbox access |
| Fix | (1) Main session reproduces case_005 D1 falsification via `_run_shared` (not `faces_match_shared`) and verifies which finding-type holds. (2) If V19 is correct (bbox-overlap path), refactor V19 to specify which entry-point fails, since `_run_shared` is unaffected. (3) If case_003 path holds (centroid-direction-based dot-product test sufficient), V19 may be partially false — flag for case_005 sub-session re-run with explicit `_run_shared` invocation. (4) Either way, A2 may need a dedicated `should_have_been_shared(body_a, body_b, max_gap_mm)` helper exposing gap-distance as an output field — currently `_run_shared` returns `matched=True` without surfacing the inter-face gap distance, so a "matched but with 0.35 mm gap" signal isn't visible to the engineer |
| Status | **closed · disambiguated 2026-05-08 v2** — case_005 sub-session re-ran D1 falsification via `detect_virtual_interfaces` + `_run_shared` (the public API used by case_003); both spec orderings return `matched=True` symmetrically. **Hypothesis (a) of V21 confirmed**: case_005 v1 invoked `faces_match_shared` (lower-level helper) directly; the public API does NOT exhibit the bbox-overlap rejection. **Hypothesis (b) refuted**: flange-ring axial-end faces ARE axis-aligned planar (normal·x_axis=±1.0); `find_face_facing_target` selects them correctly. V22's "curved-geometry-specific" hypothesis is partially refuted — see V22 closure note. **The new finding promoted to V25**: even with `_run_shared`'s matched=True, the result hides the gap-magnitude (hardcoded placeholder fields), so the SHAPE of A2's scope gap is "silent placeholder semantic" not "code-path failure" |
| Reference cases | case_003 (PASS, planar-box Z-axis gap, 2026-05-08); case_005 v1 FAIL via `faces_match_shared` (V19, 2026-05-08); case_005 v2 PASS via `_run_shared` public API (V21 closure, 2026-05-08, evidence/v2_a2_run_shared.json) |
| Lesson | When two industrial cases produce contradictory advisor outcomes on structurally similar defects, **the advisor's actual code path matters more than its conceptual scope**. V19's diagnosis of "bbox-overlap fails on thin-extent bboxes" applies to `faces_match_shared` but NOT to `_run_shared` (the public API surface). Sub-sessions should specify in their V-finding which entry-point was invoked. **V21 closure deepens the lesson**: even after disambiguation, the public-API PASS does not actually field-validate the advisor as a gap-defect detector; both case_003 PASS and case_005 v2 PASS demonstrate only that `find_face_facing_target` runs cleanly. The defect-detection capability the cases were meant to exercise is **not implemented** in A2 (V25). The cross-case investigation that V21 provoked is what surfaced this — V21 is the meta-finding whose closure is V25 |

### V22 · A2 advisor field-validation on rotating-machinery topology (case_004) — 3rd PASS, weights V21 toward case_005-specific failure

| field | value |
|---|---|
| Surface | A2 advisor `_run_shared` cross-topology field validation; rotating-machinery + axis-aligned planar boxes + Y-axis sub-mm gap |
| Engineer symptom | case_004 D1 = 0.30 mm Y-axis gap between `nacelle_body` (1.8 m × 0.9 m × 0.82 m axis-aligned box) and `nacelle_service_cover` (0.62 m × 0.035 m × 0.32 m axis-aligned box). FreeCAD `distToShape` ground truth = 0.30000 mm exact match. A2 `_run_shared` invoked via the public `detect_virtual_interfaces` API on the (nacelle_body, nacelle_service_cover) pair: `matched=True`, `body_owner='nacelle_body'`, `face area = 1.476e6 mm²`, `normal_dot = 0.969`, `bbox_overlap_fraction = 1.0` (synthetic, _run_shared sets to 1.0), `area_diff_fraction = 0.0`. **Same shape as case_003's PASS, NOT case_005 V19's FAIL** |
| Root cause | `_run_shared` uses `find_face_facing_target` (normal-direction-only test). For axis-aligned planar boxes with face normals perfectly aligned with the gap direction (case_003 Z-axis, case_004 Y-axis), the test always succeeds. case_005 flange geometry must have face normals not aligned with the gap axis (curved flange-ring geometry → faces fan around perimeter, dot products mostly < 0.5 against the axial gap direction). V21 cross-case investigation now has 3 cases of evidence: (a) case_003 axis-aligned Z-axis box gap → PASS; (b) case_004 axis-aligned Y-axis box gap → PASS; (c) case_005 flange-ring X-axis gap → FAIL. Pattern: A2 `_run_shared` is reliable for **axis-aligned planar geometry** with face normals aligned to gap axis; unreliable for **curved geometry** like flange rings |
| Fix | (1) Restrict V21 "open" status: refactor V21 entry to mark `case_003 path = correct for axis-aligned planar`; A2 `_run_shared` is correct API for that topology class. (2) For case_005-class flange-ring geometry, A2 needs additional helper — exact recommendation now feasible: `find_face_facing_target` should pre-filter candidate faces by **bbox alignment with gap axis** before applying normal-dot test; current behavior selects largest-area face globally even if its normal points away from the gap axis. (3) Document A2 contract: "axis-aligned planar geometry with face normals aligned to gap axis = strongest case; flange/curved geometry = weakest case." (4) **Sub-DEC under DEC-V61-198** for advisor-scope-expansion arc (compounded with V17 + V19 + V21): now 3 industrial cases (003 + 004 PASS, 005 FAIL) provide enough signal to scope an A2-v2 implementation distinguishing `_run_shared_axis_aligned` from `_run_shared_curved` paths |
| Status | **closed · field-validated** (3rd cross-topology PASS for `_run_shared` algorithm path); V22's hypothesis "case_005 failure is curved-geometry-specific" was **refuted by V21 disambiguation 2026-05-08 v2** — case_005 flange-ring axial-end faces ARE axis-aligned planar (normal·x=±1.0), `_run_shared` matches them via `find_face_facing_target`, and the v1 case_005 FAIL was code-path-specific (used `faces_match_shared` lower-level helper). Real classification of `_run_shared` scope: works on **axis-aligned planar bodies whose face normals align with the centroid-direction**; case_005 flange-ring qualifies. **The shared finding across all 3 cases (V22 + V21 closure + V25)**: matched=True is the SAME placeholder output regardless of actual gap distance — no PASS in this set field-validates A2 as a gap-defect detector. case_004 V22 PASS confirms `_run_shared` runs cleanly on rotating-machinery axis-aligned bodies; it does NOT confirm A2 distinguishes 0.30 mm gap from 0 mm gap |
| Reference case | case_004_nrel_phase_vi_mrf v1 advisor-validation 2026-05-08 (`evidence/v1_<ts>/defect_verification.json`); cross-link to V21 closure + V25 |
| Lesson | Cross-topology field validation accumulates evidence quickly. With 3 cases on the same advisor (3 = small but informative sample), **the structural axis of the failure is now observable**: `_run_shared` runs cleanly on axis-aligned planar bodies (case_003 + case_004 + case_005 v2-disambiguation all PASS); the v1 case_005 FAIL was a different invocation path. Pattern 6 application: V22's bifurcation hypothesis ("axis-aligned PASS / curved FAIL") was a reasonable hypothesis with case_004 evidence alone but is refuted by V21 disambiguation — case_005 IS axis-aligned at the relevant flat annular ends. **Pillar 2 reinforcement**: each industrial case adds another point to the advisor falsification surface; subsequent cases (here case_005 v2 disambiguation) can RETRO-correct the hypothesis structure without invalidating the field-validation outcome. **The honest reading of V22**: it confirms `_run_shared` returns matched=True on axis-aligned bodies — and that's exactly what V25 says hides the actual gap-defect detection gap |

### V23 · thin_wall_advisor field-validation on rotating-machinery aux hardware (case_004) — first cross-topology to case_002a/b

| field | value |
|---|---|
| Surface | thin_wall_advisor cross-topology field validation; rotating-machinery + auxiliary instrumentation thin shim |
| Engineer symptom | case_004 D8 = 0.75 mm thick `yaw_sensor_shim` (axis-aligned 0.32 m × 0.00075 m × 0.22 m box). FreeCAD `BoundBox.{X,Y,Z}Length min` ground truth = 0.75000 mm exact match. thin_wall_advisor invoked at 3 refinement-level scenarios with `background_cell_size = 400 mm`: levels (1,2)/(2,3)/(3,4) all return `severity=critical` with `cells_per_thickness = 0.0075/0.0150/0.0300` and unanimous `recommended_level_max = 11`. Advisor consistent across all 3 level scenarios (escalating thinness → escalating recommendation, monotonic) |
| Root cause | thin_wall_advisor uses bbox-min as thinness estimator (V10 lesson: exact for axis-aligned plate/beam, lower-bound for curved shells). yaw_sensor_shim is axis-aligned (Codex's `make_box` from cadquery), so bbox-min = 0.75 mm is exact. Effective cell size at level 4 = 25 mm = 33× thicker than the shim → `cells_per_thickness ≈ 0.03` → critical. The recommended_level_max=11 implies effective cell size ≈ 0.2 mm — practical only with `refinementRegions` slab approach, not raw surface levels |
| Fix | (1) Accept advisor warning + adopt v1 simplification path (V10 Pattern 5): drop `yaw_sensor_shim` from sHM input STL or set `refinement: [0, 0]` to skip the patch — defect existence is verified upstream (advisor PASS) and downstream impact on rotor thrust/torque is null (shim is on tower-base, far from rotor disk). (2) For cases where the thin patch matters to the flow (e.g., case_007 transom plate above WL), use refinementRegions slab approach. (3) **Cross-topology consistency confirmed**: case_002a (curved CATIA Frame, 50 mm thick) → flagged; case_003 (planar CadQuery thin_access_plate, 0.80 mm) → flagged; case_004 (rotating-machinery aux yaw shim, 0.75 mm) → flagged. The bbox-min heuristic generalizes across (curved, planar-aux-aero, planar-aux-instrumentation) topologies |
| Status | `[VALIDATED 2026-05-08 4-of-4]` (cross-topology consistency now 4 cases: case_002a + case_003 + case_004 + **case_007**; **no behavioral divergence across topologies**) |
| Reference case | case_004_nrel_phase_vi_mrf v1 advisor-validation 2026-05-08; **case_007_kcs_ship_vof v1 advisor-validation 2026-05-08 (`evidence/v1/advisor_exercise.json`, transom plate 0.80 mm, severity=critical, cells_per_thickness=0.044)** |
| Lesson | thin_wall_advisor's bbox-min thinness estimator is robust across very different industrial topologies (CATIA curved frame, CadQuery planar plate, rotating-machinery aux shim, **ship-hydro above-waterline transom plate**). The advisor passes Pattern 6 inheritance criterion — same algorithm, same outcome across solver classes (buoyantSimple/CHT/MRF/multiphase-VOF). Recommended_level_max scales monotonically with assigned level (case_004 (1,2)→11, case_007 (1,2)→8 with larger background cell). **4-of-4 cross-topology validation closes this advisor's correctness arc**; future cases extend evidence but no longer change the conclusion |

### V24 · V16 fragmentation pattern reproduction in case_004 (rotating-machinery topology)

| field | value |
|---|---|
| Surface | Codex case-design CAD pattern; `cq.Compound.makeCompound([Solid_a, Solid_b])` STEP-roundtrip fragmentation; FreeCAD body-construction frame artifacts |
| Engineer symptom | case_004 build_cad.py uses `cq.Compound.makeCompound([hub, nose])` for `hub_spinner` and `cq.Compound.makeCompound([top, bottom, side_pos, side_neg])` for `tunnel_walls`. After STEP roundtrip via FreeCAD `Import.insert`, the 12-body manifest produces **40 objects in the FreeCAD doc**: (a) 12 expected-named bodies; (b) `hub_spinner` fragmented into 3 objects (hub + nose + parent compound named `hub_spinner002`); (c) `tunnel_walls` fragmented into 5 objects (4 plates + parent compound named `tunnel_walls004`); (d) parent assembly `case_004_nrel_phase_vi_mrf` with 218 faces; (e) **21 spurious FreeCAD body-construction frames** (X-axis, Y-axis, Z-axis, XY-plane, XZ-plane, YZ-plane, Origin) with sentinel bboxes ≈ 1e92 mm. Pattern is **identical** to case_005 V16 (where `cq.Compound.makeCompound([Face,...])` produced 102k+ fragments) but here Solid-of-Solid Compound produces fewer fragments (3 + 5 = 8 fragments + 21 datum) |
| Root cause | Same as V16 (case_005). cadquery's STEP exporter emits each member of a Compound as a separate top-level entity. FreeCAD's `Import.insert` faithfully reconstructs one Part::Feature per top-level entity (V16 root cause confirmed). Additional finding (NEW for V24, not in V16): **FreeCAD also emits body-construction frame objects** (X-axis, XY-plane etc. with sentinel-bbox ≈ 1e92 mm) — these are FreeCAD's "Body" datum frames preserved through the STEP roundtrip. They have 0 faces or 1 face (degenerate) and infinite extent; sub-session pre-filter must drop them or fail badly when computing global bbox. case_005's V16 did not surface this because its CAD pattern (cq.Compound of cq.Face, no cq.Solid hierarchy) doesn't trigger FreeCAD's "Body" detection; case_004's mixed Compound-of-Solid does |
| Fix | (1) **Sub-session workaround for case_004**: when iterating bodies for advisor input, filter to known-named-bodies set; **do NOT** include `hub_spinner001/002`, `tunnel_walls001-004`, parent assembly, or any datum frame (X-axis*, XY-plane*, etc.). (2) **Codex case-design protocol revision** (compounded with V16): require single-Solid output for "logical bodies that should be treated as one OpenFOAM patch." For `hub_spinner` use `cq.Solid.fuse([hub, nose])` (boolean fuse) instead of `cq.Compound.makeCompound`; for `tunnel_walls` either fuse the 4 plates OR (cleaner) keep them as 4 separately-named patches `tunnel_top/tunnel_bottom/...` and let sHM extract them individually. (3) **Main-project A1 extension**: when `cad_ingest_freecad.py` extracts to STL per-body, post-filter bodies with `n_faces == 0` AND/OR with infinite-bbox detection (any dimension > 1e9 mm = sentinel) AND/OR detect parent-compound naming pattern (`<base><suffix_001..N>` with sibling parent `<base>` having same bbox as union of suffixed). (4) **Defect-manifest verification command revision**: the existing FreeCADCmd one-liner uses `o['<body>']` — works because FreeCAD preserves the user-named primary body label in the dict; the auxiliary fragments use `<body>NNN` suffixed labels and are siblings, not children, of the primary |
| Status | **partial** — case-local workaround possible (hard-coded label allowlist for advisor input); compounded with V16 → main-project A1 extension scope clearer (compound-fragmentation handling + datum-frame filtering, both observable from case_004 evidence alone) |
| Reference cases | case_005_rae_m2129_sduct V16 (cq.Compound of cq.Face, faces-only fragmentation, 2026-05-08); case_004_nrel_phase_vi_mrf V24 (cq.Compound of cq.Solid, additional datum-frame fragmentation, 2026-05-08) |
| Lesson | V16 was first signal; V24 is second-case confirmation that `cq.Compound.makeCompound` is unreliable for "I want this to be one body." Pattern is now strong enough to retire the pattern from the Codex case-design protocol — recommend `cq.Solid.fuse(...)` or distinct named bodies. Additional case_004 surface: FreeCAD body-datum frames must be filtered. **Pillar 2 escalation**: 2 cases on the same Codex CAD pattern crystalize the protocol revision. **Pattern 6 reinforcement**: V16 inheritance applies wherever Codex uses `cq.Compound.makeCompound` regardless of solver class — this is a **CAD-ingest-side finding** (not a fluid-numerics finding), inherits across all numerics classes |

### V26 · Codex CAD generator off-by-half-width on `centered=True` cq.Workplane.box() origin

| field | value |
|---|---|
| Surface | Codex case-design CAD pattern; cadquery `cq.Workplane.box(W, H, D, centered=True)` semantics |
| Engineer symptom | case_006 D1 ground-truth verification (FreeCAD `distToShape(pad, cover)`) returned **22.35 mm** instead of the manifest's claimed **0.35 mm**. Codex's `build_cad.py` placed the `cover` body at origin `pad_x + 22.0 + GAP + 22.0`, producing a 22.35 mm edge-to-edge gap. The intended formula is `pad_x + 22.0 + GAP` for two centered=True boxes (each centered on its origin → extends ±11 mm), where the 22.0 represents pad_half_width + cover_half_width = 11+11 |
| Root cause | Codex wrote the formula as if both boxes were `centered=False` (origin at LE) but called them with `centered=True` (origin at centroid). With centered=True, going from one box's center to the next requires `(this_half_width + gap + next_half_width)`, not `(full_width + gap + full_width)`. Codex's mental model conflated "box-width-as-step" with "centroid-to-centroid distance" — analogous to V16's "Compound-of-Faces vs single-Solid" mental-model bug, but a different mechanism |
| Fix | (1) **Sub-session local fix** (applied 2026-05-08): one-line edit in `build_cad.py` removed the second `+ 22.0`; FreeCAD distToShape post-fix = 0.35 mm exact. (2) **Codex case-design protocol revision** (compounded with V16+V24): require Codex to **declare verification dimensions and tolerance ranges in `defect_manifest.yaml`** (as Codex case_006 did declare 0.35 mm but did not verify the script produces it). Add a "post-build CAD self-check" step where Codex must run the build script and verify the defect dimensions before marking the deliverable complete. (3) Update `codex_case_design_protocol.md` defect-injection examples to show the centered=True semantics explicitly with comments |
| Status | **partial** — case-local fix-in-place applied; protocol revision pending. Compounded evidence: 3 Codex CAD bugs in 2 cases (V16 case_005 cq.Compound-of-Faces, V24 case_004 cq.Compound-of-Solids, V26 case_006 centered=True formula) → protocol revision overdetermined |
| Reference case | case_006_onera_m6_transonic v1 build (2026-05-08); evidence: pre-fix `distToShape` = 22.35 mm, post-fix = 0.35 mm exact |
| Lesson | Codex CAD generators have a recurring class of mental-model bugs that produce structurally-correct-but-numerically-wrong defects. The sub-session's first action on any Codex CAD output must be ground-truth verification (FreeCAD distToShape + BoundBox.min). Updating `codex_case_design_protocol.md` to require Codex to self-verify is the highest-leverage protocol fix |

### V27 · rhoCentralFoam fixed deltaT yields catastrophic Co at first iter; adjustTimeStep mandatory

| field | value |
|---|---|
| Surface | rhoCentralFoam controlDict; explicit central-upwind time integration |
| Engineer symptom | First-iter mean Courant Number = 674.83, max = 69,440.73 with `deltaT 1.0` and `adjustTimeStep no`. Solver did not crash immediately (rhoCentralFoam's `diagonal` solver tolerates Co arbitrarily because each cell time-step is local), but produced numerical garbage and aborted on a downstream `DILU preconditioner` error before any flow could establish |
| Root cause | rhoCentralFoam uses an **explicit** central-upwind flux scheme. The CFL stability limit is `Co = (|U| + a) * dt / dx` where a is the local sound speed. With wing-wall cells of 31 mm, U≈285 m/s, a≈340 m/s, the stable dt is 31mm / 625 m/s ≈ 50 microseconds. A fixed `deltaT 1.0` produces dt 20,000× too large. The user-side trap: rhoCentralFoam's controlDict is structurally similar to other compressible solvers (rhoSimpleFoam, rhoPimpleFoam) where a fixed dt is reasonable; novice users assume the same here |
| Fix | (1) **Always set `adjustTimeStep yes`** with `maxCo 0.5` (or 0.3 for shock cases) in rhoCentralFoam controlDict. (2) Set initial `deltaT 1e-6` (1 microsecond) — gives sub-iteration to compute Co from CFL and self-adjust. (3) Codify in **S15 (NEW)** of `solver_convergence_playbook.md` |
| Status | **playbook** — codified as S15 root case |
| Reference case | case_006_onera_m6_transonic v1 first solver run (2026-05-08, before fix) |
| Lesson | First time the project ran a density-based explicit solver. The `adjustTimeStep yes` requirement is rhoCentralFoam-specific and easy to overlook; main project's controlDict template must default this on for any density-based solver class |

### V28 · rhoCentralFoam fvSolution: DILU preconditioner unavailable for symmetric matrices

| field | value |
|---|---|
| Surface | rhoCentralFoam fvSolution; symmetric matrix solver setup |
| Engineer symptom | Solver runtime error after iter 1: `Unknown symmetric matrix preconditioner type DILU. Valid: 6(DIC FDIC GAMG diagonal distributedDIC none)`. The case_005 fvSolution template (which case_006 inherited as starting point) used `PBiCGStab + DILU` for U/e/k/omega — works for rhoSimpleFoam but fails for rhoCentralFoam |
| Root cause | rhoCentralFoam wraps U/e/k/omega in a different lduMatrix path that maps to symmetric solver registry. DILU (Diagonal Incomplete LU) is for asymmetric matrices; symmetric matrix path requires DIC (Diagonal Incomplete Cholesky) or one of the explicit-iteration smoothers. The matrix symmetry classification is a property of the solver/equation form, not user-configurable |
| Fix | (1) **Use `smoothSolver + symGaussSeidel`** for U/e/k/omega in rhoCentralFoam (canonical from OpenFOAM tutorial set tutorials/compressible/rhoCentralFoam/biconic25-55Run35). (2) Keep `diagonal` for ρ/ρU/ρE (these are direct-update, not iterative). (3) Codify in S15 |
| Status | **playbook** — codified as S15 |
| Reference case | case_006_onera_m6_transonic v1 first solver run (2026-05-08) |
| Lesson | Codex's deliverable did not specify fvSolution choices. The case_005 inheritance was a natural assumption but wrong — case_005 is rhoSimpleFoam (pressure-based, asymmetric matrices for U), case_006 is rhoCentralFoam (density-based, symmetric matrix path). Inheritance across solver classes is risky; main project should provide rhoCentralFoam-canonical fvSolution template |

### V29 · OpenFOAM ESI lacks `characteristicPressureInletOutletPressure`/`characteristicVelocityInletOutletVelocity` BC types

| field | value |
|---|---|
| Surface | OpenFOAM 0/* boundary condition catalog; openfoam-default:2312 (ESI fork) BC type registry |
| Engineer symptom | Solver runtime error: `file: 0/p/boundaryField/...characteristicPressureInletOutletPressure not found in valid types`. Codex's parts manifest specified these BC types per the AGARD-style transonic far-field convention; they exist in foam-extend but NOT in opencfd/openfoam-default:2312 (the project's default Docker image) |
| Root cause | The `characteristic*` BC family is a foam-extend / older OpenFOAM-1.7 era feature. OpenFOAM ESI (since v3+) replaced them with `freestream` (auto-direction-detecting based on flow), `freestreamPressure`, and `waveTransmissive` for upwind/downwind. Codex's training data appears to mix foam-extend and ESI BC names. The naming is so similar that catching the mismatch requires either (a) running the case OR (b) cross-checking against the actual OpenFOAM image's BC registry |
| Fix | (1) **Substitute canonical OpenFOAM ESI BC family**: U → `freestream` with `freestreamValue uniform (Ux Uy Uz)`; p → `freestreamPressure` with `freestreamValue uniform p_inf`; T → `freestream` with `freestreamValue uniform T_inf`. (2) Add a **BC-name compatibility check** to `codex_case_design_protocol.md`: validate every `parts_manifest.yaml.parts.*.bc.<field>` against the actual OpenFOAM image's BC registry (e.g., via `foamHelp boundary -listAll | grep <type>`) **before** dispatch. Sub-session can fast-fail on dispatch invalid types |
| Status | **partial** — case-local fix-in-place applied; protocol enhancement pending |
| Reference case | case_006_onera_m6_transonic v1 first solver run (2026-05-08) |
| Lesson | This is the second Codex BC-protocol-mismatch finding (V29). First was V11/V19 about per-field BC consistency. Now adds: BC type names themselves can be wrong-fork (foam-extend vs ESI). Compounded with V26 (CAD formula) + V31 (advisor mapping): Codex case-design needs a **declarative-and-verified** protocol revision, not just doc updates |

### V30 · thin_wall_advisor extreme-thinness field-validation: 0.18 mm sliver flagged critical at all reasonable refinement levels

| field | value |
|---|---|
| Surface | `ui/backend/services/geometry_ingest/thin_wall_advisor.detect_thin_wall_patches_at_risk` |
| Engineer symptom | case_006 D4 (0.18 mm sliver body `tip_cap_sliver`, 8-triangle sliver mesh) tested across 3 refinement levels with 50 mm bg cell. Results: level [1,2] → cells_per_thickness=0.014, severity=critical; level [2,3] → 0.029, critical; level [3,4] → 0.058, critical. Recommended_level_max=10 in all cases (level 10 = 0.05 mm cell ≈ 3.69 cells per thickness). At level 10, mesh would be O(10⁹) cells — mathematically correct, practically infeasible |
| Root cause | thin_wall_advisor's algorithm correctly identifies the patch as far-below-resolvable. A 0.18 mm sliver in a transonic external case (where reasonable bg cell is meters) is fundamentally outside the regime sHM can preserve at any practical refinement. The advisor surfaces this without false positives or negatives — the fundamental geometry-physics tension is real |
| Fix | (1) **Sub-session accepts patch loss** (per S8 fix #3 v1 simplification): tip_cap_sliver does not exist post-sHM. (2) **Advisor message enhancement candidate**: when `recommended_level_max ≥ 8` (mathematically infeasible — would produce > 256× refinement vs bg, i.e., O(10⁷)+ cells), add a "PATCH LOSS UNAVOIDABLE" warning telling the engineer the only viable strategies are (a) accept loss, (b) re-design CAD to merge the sliver into a parent body, or (c) ignore the defect at the case scale. This makes V31's "Codex's mapping is wrong" finding even sharper — Codex pointed at geometry_surgery (which can't help: face count too small to decimate); thin_wall_advisor catches it but the only resolution is patch deletion. (3) Update thin_wall_advisor docstring to cite case_006 V30 as the extreme-thinness reference |
| Status | **closed · field-validated** — extends V10 (thin_wall_advisor 1st landing) and V23 (cross-topology to rotating-machinery) to the extreme-thinness regime. **5-case cross-topology now**: case_002a/b CATIA Frame curved (50 mm) + case_003 planar (0.80 mm) + case_004 rotating-machinery aux (0.75 mm) + case_006 wing-tip aerodynamic edge (0.18 mm). Spans 3 orders of magnitude in thickness without behavioral divergence |
| Reference case | case_006_onera_m6_transonic v1 advisor exercise (2026-05-08); evidence at `evidence/v1/d4_advisor_exercise.md` |
| Lesson | thin_wall_advisor remains the cleanest A1-A5 sediment. Cross-topology scope now confirmed at 4 industrial cases, all pass. Recommended_level_max output is monotonically correct but practically infeasible at extreme thinness — adding a "patch loss unavoidable" UX hint when the recommendation crosses ~level 8 would prevent engineer confusion |

### V31 · Codex defect→advisor mapping incorrect for D4 (sub-mm sliver); should be thin_wall_advisor not geometry_surgery

| field | value |
|---|---|
| Surface | `codex_case_design_protocol.md` defect→advisor mapping table; Codex case-design output |
| Engineer symptom | case_006 `defect_manifest.yaml` mapped D4 (0.18 mm sliver) to `expected_advisor_to_catch: geometry_surgery.decimate_to_tier`. Sub-session exercise per kickoff Hard Guardrail (try thin_wall_advisor first): geometry_surgery silently no-op'd (sliver face count = 8, well under min_to_decimate=8000); thin_wall_advisor fired critical at all levels (V30) |
| Root cause | Codex's defect-injection vocabulary uses "sliver" for both: (a) D2-class over-dense triangulation slivers (case_005's D2: 102k+ tri faces from cq.Compound-of-Faces) where geometry_surgery.decimate_to_tier IS the correct catch; (b) D4-class sub-mm sliver bodies (case_006's D4: 8-tri 0.18 mm body) where thin_wall_advisor IS the correct catch. The defect-name "sliver" overloaded the mapping |
| Fix | (1) **Update `codex_case_design_protocol.md` defect→advisor table**: D2 (over-dense triangulation, 1k-1M+ faces) → geometry_surgery.decimate_to_tier; D4 (sub-mm sliver bodies, 1-100 faces) → thin_wall_advisor.detect_thin_wall_patches_at_risk; D8 (thin shell ≥0.5 mm) → thin_wall_advisor with severity=warning. Make the discriminator explicit: face count + bbox-min thickness. (2) Update Codex case-design prompts to require declaring **which numerical regime** the defect lives in (over-dense vs sub-mm) so it picks the right advisor |
| Status | **open** — protocol revision required; sub-session corrected mapping locally for case_006 evidence purposes |
| Reference case | case_006_onera_m6_transonic v1 dual-advisor exercise (2026-05-08); evidence at `evidence/v1/d4_advisor_exercise.md` |
| Lesson | Codex case-design defect→advisor mapping is the FIRST place sub-sessions hit Codex-knowledge-gap on advisor capabilities. Compounded with V26 (CAD formula bug), V29 (BC name foam-extend-vs-ESI mismatch): Codex's case-design protocol needs at minimum 3 enhancements: self-verify CAD dimensions + canonical BC names + correct advisor mapping for defect classes. All three feed into one `codex_case_design_protocol.md` revision sub-DEC |

### V32 · Tier-1 NASA Glenn HTTP 500 + corporate SSL cert chain double-blocker; airfoil-proxy substitution required

| field | value |
|---|---|
| Surface | CAD-source availability; Tier-1 reference geometry caching |
| Engineer symptom | case_006 `build_cad.py` tries to fetch ONERA D-section airfoil coordinates from `https://www.grc.nasa.gov/WWW/wind/valid/m6wing/foilmod.txt`. Two failures stack: (a) NASA Glenn returns HTTP 500 — same persistent issue as case_005 V20 documented; (b) the local environment has a corporate SSL proxy with self-signed cert chain that blocks Python's urllib SSL verification (`SSL: CERTIFICATE_VERIFY_FAILED self-signed certificate in certificate chain`) even for sources that DO work. Net: no Tier-1 source path is reachable from this sub-session |
| Root cause | Two independent failures in the source-availability stack: (1) NASA Glenn archive infrastructure issue (out of sub-session scope); (2) corporate SSL proxy that doesn't trust standard CA roots, blocking ALL HTTPS fetches that don't use a custom-CA-aware HTTP client. Combined, no path from `build_cad.py`'s `urllib.request.urlopen` to any external resource works |
| Fix | (1) **Sub-session local fix**: bake an ONERA-D **proxy** airfoil — NACA 0010 (10% symmetric, max thickness at x/c=0.30, closest open analogue to ONERA D) — into `inputs/cache/onera_d_proxy_naca0010.txt` and use `CASE006_FOILMOD_PATH` env var to point build_cad.py at it. (2) Document the **lambda-shock x/c displacement caveat** in v1 REPORT (NACA 0010 differs from ONERA D in rooftop region x/c=0.30-0.60 → lambda x/c may shift 5-15%). (3) **Bundle with V20 in A1 extraction sub-DEC**: include offline-cache support + airfoil-proxy-substitution path in `cad_ingest_freecad.py`. Allow the airfoil-cache file to be checked into `.planning/cad_cache/` per the script's `CACHE_DIR = DEFAULT_REPO_ROOT / ".planning" / "cad_cache"` convention. (4) Bigger-picture: the Tier-1 source resilience is a recurring theme (case_005 NASA Glenn, case_006 NASA Glenn, anticipated case_009 Sandia TUD); main session should consider per-case Tier-1 mirror caching as a strategic action |
| Status | **open** — case-local fix applied; structural fix in A1 extraction sub-DEC scope |
| Reference case | case_006_onera_m6_transonic v1 build (2026-05-08); evidence: `inputs/cache/onera_d_proxy_naca0010.txt` (proxy), build_cad.py output mentioning the proxy substitution |
| Lesson | The project's Tier-1 source pipeline is brittle to upstream infrastructure issues. Sub-session pragmatic substitution (airfoil proxy) is acceptable for v1 with explicit caveats, but inflates the v1 finding budget — N=2 cases (005 + 006) on the same NASA Glenn infrastructure issue suggests time to consider a project-side Tier-1 mirror cache strategy |

### V33 · A2 advisor `_run_shared` cross-topology PASS on ship-hydro topology (case_007) — 4th algorithm-path PASS; gap-detection still pending V25 fix

| field | value |
|---|---|
| Surface | virtual_interface_detector public API on ship-hydro half-domain rudder/hub geometry |
| Engineer symptom | case_007 D1 = 0.35 mm axial gap between `rudder_hub_fairing` (CadQuery box) and `rudder_reference` (extruded foil polyline). OCC `BRepExtrema_DistShapeShape` ground truth = 0.3500 mm exact. `detect_virtual_interfaces` invoked via public API on both spec orderings (`rudder_hub__rudder_reference_interface` + `rudder_reference__rudder_hub_interface`) returns matched=True symmetrically with `owner=rudder_reference`, `face_area ≈ 5.93×10³ mm²`, `normal_dot=0.514`. The chosen face is one of the larger side faces of the rudder polygon-extrusion (NOT the leading-edge face perpendicular to the gap direction), confirming `find_face_facing_target` ranks by area and the rudder geometry has multiple faces with positive projection on the centroid-direction |
| Root cause | Same root as V21 closure / V25: `_run_shared` returns matched=True with HARDCODED placeholder fields `bbox_overlap_fraction=1.0` / `area_diff_fraction=0.0` (lines 200-201 of `virtual_interface_detector.py`). The 0.35 mm gap is invisible to the result schema. case_007 is the 4th cross-topology PASS for the algorithm-runs-cleanly behavior (003 planar-aero-box + 004 rotating-machinery-axis-aligned + 005-v2 axial-end-flange-ring + 007 ship-hydro mixed-foil-and-box), but the silent-placeholder semantic means **none** of the four PASSes field-validate A2 as a gap-defect detector |
| Fix | (1) **No new fix surfaces from case_007 — V25's prescribed A2-v2 API extension still pending**: add `inter_face_gap_mm` field, populate from face-plane perpendicular distance, return real `bbox_overlap_fraction`/`area_diff_fraction` measurements. (2) Sub-session sediment: case_007 increases evidence weight for the V25 sub-DEC ratification — 4 industrial cases on 4 different topologies, all matched=True, none distinguishable from each other on actual gap distance. (3) **Cross-topology robustness on the algorithm-path side IS settled** at 4-of-4: `find_face_facing_target` selects a candidate face on (planar boxes / axial-end annular planar / mixed foil-extrusion + box) without crashing or returning false-negative-by-bug. (4) **Engineer guidance**: until A2-v2 lands, treat A2 PASS as "the geometry has plausible facing faces between the named bodies" — NOT as "gap is small enough to mesh as shared interface" |
| Status | `[QUESTIONABLE 2026-05-08]` per V25 — algorithm-path cross-topology consistency confirmed at 4-of-4; gap-detection capability awaits A2-v2 |
| Reference case | case_007_kcs_ship_vof v1 advisor-validation 2026-05-08 (`evidence/v1/advisor_exercise.json`); both spec orderings tested |
| Lesson | The 4-case algorithm-path consistency is genuine evidence on the side that V21 disambiguation closed. The 0.35 mm gap-detection capability is genuinely missing on the side that V25 documents. Sub-sessions should NOT collapse these two into "A2 is field-validated"; the precise reading is "`_run_shared` works on the topologies tested; the result schema does not surface gap distance, so gap-defect detection is upstream-incompatible." case_007 sediment continues the V25-aware framing: the 4-of-4 cross-topology PASS strengthens the algorithm side without weakening the V25 finding |

### V34 · snappyHexMesh free-surface band + near-hull box compounding saturates `maxGlobalCells` before reaching surface body refinement (case_007)

| field | value |
|---|---|
| Surface | snappyHexMesh refinementRegions cell-budget saturation; ship-hydro half-domain default refinement |
| Engineer symptom | case_007 v1 first sHM attempt: `castellatedMeshControls.maxGlobalCells = 6000000`, `free_surface_band` slab refinementRegion `level=3` over `(-14.5572 0 -1.5)` to `(21.8358 10.9179 0.5)` (4.5 m thick × full half-domain x and y), `near_hull_box` refinementRegion `level=4` over a 9 m × 1.2 m × 0.9 m volume around the hull. After 5 shell-refinement iterations, sHM logged `No cells marked for refinement since reached limit 6000000` — the slab + box volume × 8^level exceeded the budget BEFORE surface-body refinement (hull `level=(3,5)`, rudder `level=(4,6)`) had any opportunity to refine the actual ship surfaces. Net mesh: 10.9M cells of slab refinement; 0% of the budget went to ship surfaces |
| Root cause | sHM's refinementRegions are processed in a shell-refinement phase BEFORE refinementSurfaces' surface refinement phase. When the slab volumes are large (free-surface band over the full half-domain x extent = ~36 m × 11 m × 4.5 m = 1782 m³), and the level multiplier is high (level=3 → 8³ = 512× background cell density inside the slab), the cell budget can be consumed entirely before the surface phase begins. **Compounding factor**: half-domain ship-hydro cases have very wide aspect ratios (Lx ≈ 36 m vs Lz ≈ 11 m), so the slab volume is unusually large relative to the geometry of interest |
| Fix | (1) **Sub-session smoke-grade fix**: drop free_surface_band level from 3 to 1, near_hull_box from 4 to 2, surfaces from (3-5)/(4-6) to (1-2)/(2-3). Smoke mesh ran in ~minutes within `maxGlobalCells = 2.5M`. (2) **Production v2 fix**: tighten the free_surface_band slab to ±draft/4 around `z=0` (1.5 m thick instead of 4.5 m thick) AND restrict its x extent to ±2*Lpp around the hull (15 m instead of 36 m), reducing slab volume by ~7×. Then level=3 fits in the budget. (3) **Sediment artifact candidate**: pre-meshing advisor `free_surface_refinement_advisor` that estimates total cell count from sum-over-refinementRegions (volume × 8^level) + sum-over-refinementSurfaces (area / cell_size² × 8^(2*level)) and warns when the projected sum > 0.7 * maxGlobalCells before any surface phase begins. Same shape as `thin_wall_advisor` (V10 / V23) but for free-surface CFD. (4) **Doc fix**: update kickoff-template ship-hydro section to recommend draft-thick (not domain-thick) free-surface bands |
| Status | **partial** — case-local fix applied; pre-meshing advisor candidate identified, awaiting 2nd multiphase case to confirm pattern recurs (V10's extraction trigger pattern) |
| Reference case | case_007_kcs_ship_vof v1 mesh-only run 2026-05-08; first-attempt cell-saturation evidence captured in `~/Desktop/case_007_kcs_ship_vof/evidence/v1/REPORT.md` § "v1 sHM cell-budget saturation"; smoke-pass log at `case/log.snappyHexMesh` |
| Lesson | sHM cell budget is non-monotonic across phases: refinementRegions can starve refinementSurfaces if the slab volumes are too large. Free-surface CFD is especially prone because the slab's "natural" extent is the full domain footprint, not the hull-of-interest extent. **Pillar 2 candidate**: this is the multiphase analog of V10 — a pre-meshing decision that's invisible until sHM runs and exhausts the cell budget. A pre-meshing volumetric advisor would catch it in seconds. **Pattern 6 connection**: case_007 is the multiphase-VOF root, so this finding does NOT inherit from prior numerics classes — it's genuinely new sediment for the multiphase axis. Future multiphase cases (none currently planned in the 003-010 set, but the harness will encounter VOF again) should test whether the same advisor catches their case before sHM runs |

### V35 · interFoam + kOmegaSST requires `wallDist { method ...; }` in fvSchemes; apu-bay-derived templates omit it (multiphase-VOF root)

| field | value |
|---|---|
| Surface | OpenFOAM-2312 fvSchemes — `kOmegaSST` and other RAS models that consume wall distance fields |
| Engineer symptom | case_007 v1 first interFoam start: solver passes `Selecting RAS turbulence model kOmegaSST`, then immediately `FOAM FATAL IO ERROR: Entry 'method' not found in dictionary "/case/system/fvSchemes/wallDist"`. The fvSchemes template inherited from apu-bay's buoyantSimpleFoam shape has no `wallDist` block; OF-2312 requires one when any RAS model needs `y_wall` |
| Root cause | apu-bay's fvSchemes targets buoyantSimpleFoam + chtMultiRegionSimpleFoam, where the wall distance method defaults are accepted via the older fallback path. Newer OF versions (≥ v2306) require an explicit `wallDist { method meshWave; }` (or `Poisson`, `advectionDiffusion`) block when any consumer of `y_wall` is selected. interFoam itself does not need wall distance, but `kOmegaSST` does, so the requirement appears at the turbulence-model selection step, not at the solver step |
| Fix | (1) **Sub-session local fix**: add `wallDist { method meshWave; }` to `templates/system/fvSchemes` and re-stage to `case/system/fvSchemes`. interFoam restart succeeded. (2) **Main-project structural fix**: extend the harness' fvSchemes template family with a default `wallDist` block when the case manifest selects any RAS model. Should be a per-numerics-class default (multiphase-VOF + kOmegaSST → meshWave; compressible-buoyant + kEpsilon → meshWave or Poisson). (3) **Sediment artifact candidate**: `fvSchemes_wallDist_advisor` that flags any case with RAS turbulence enabled but no `wallDist` block, before the case is dispatched to the solver |
| Status | **partial** — case-local fix applied; structural fix is a 1-line default in the fvSchemes writer, easy to land but should wait for 2nd multiphase or 2nd OF≥v2306 case to confirm pattern recurs (V10's extraction trigger pattern) |
| Reference case | case_007_kcs_ship_vof v1 first interFoam attempt 2026-05-08; evidence in `evidence/v1/REPORT.md` § "interFoam smoke run" |
| Lesson | The apu-bay fvSchemes template is a v1-era inheritance from compressible-buoyant numerics; multiphase-VOF + kOmegaSST exposes a missing block. **Pattern 6 nuance**: even when the *fluid-internal numerics* differ across solver classes, the fvSchemes template is shared infrastructure — so missing-block bugs surface unpredictably when a new solver class is exercised on the inherited template. The harness should treat fvSchemes as a per-solver-class template, not a per-case copy-and-edit. apu-bay's choice was reasonable for case_002a/b's scope; case_007 surfaces the limitation. **Compounded with V11 / V34**: each new solver class is finding fvSchemes / fvSolution / 0.orig template gaps. A per-class default registry is overdue |

### V36 · A2 advisor `_run_shared` cross-topology PASS on incompressible-RANS-Lagrangian airfoil-mount topology (case_008) — 5th algorithm-path PASS; gap-detection still pending V25 fix

| field | value |
|---|---|
| Surface | virtual_interface_detector public API on incompressible-RANS-Lagrangian airfoil-mount topology (clean GLC305 + auxiliary defect-bearing mount hardware) |
| Engineer symptom | case_008 D1 = 0.35 mm vertical gap between `root_mount_pad` (planar CadQuery box, 55×8×20 mm) and `root_mount_strut` (planar CadQuery box, 38×14×16 mm) at airfoil aft-root mount location (x/c=0.72, z/c=−0.88). Manual ground truth via face-coordinate arithmetic (mirroring `scripts/build_cad.py`): `pad_bottom_y − strut_top_y = 0.3500 mm` exact match to claimed 0.35 mm. `detect_virtual_interfaces` invoked via public API on `mode='shared'` spec returns matched=True with `body_owner=root_mount_pad`, chosen face area = 1100 mm² (the pad's −y bottom face), `normal_dot=+1.0`, `bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`, `diagnostic="shared face on 'root_mount_pad' (area=1.1e+03)"` |
| Root cause | Same root as V21 closure / V25 / V33: `_run_shared` returns matched=True with HARDCODED placeholder fields `bbox_overlap_fraction=1.0` / `area_diff_fraction=0.0` (`virtual_interface_detector.py:200-201`). The 0.35 mm gap is invisible to the result schema. case_008 is the 5th cross-topology algorithm-path PASS (003 planar-aero-box-Z-axis-gap + 004 rotating-machinery-Y-axis-gap + 005-v2 axial-end-flange-ring + 007 ship-hydro mixed-foil-and-box + 008 incompressible-Lagrangian airfoil-mount-axis-aligned-Y-axis-gap). The silent-placeholder semantic means **none of the five PASSes field-validate A2 as a gap-defect detector**; they validate `find_face_facing_target` ranks a face cleanly across all five topologies |
| Fix | (1) **No new fix surfaces from case_008 — V25's prescribed A2-v2 API extension still pending**: add `inter_face_gap_mm` field, populate from face-plane perpendicular distance, return real `bbox_overlap_fraction`/`area_diff_fraction` measurements. (2) Sub-session sediment: case_008 increases evidence weight for the V25 sub-DEC ratification — 5 industrial cases on 5 different topologies, all matched=True, none distinguishable from each other on actual gap distance. (3) **Cross-topology robustness on the algorithm-path side IS settled at 5-of-5**: `find_face_facing_target` selects a candidate face on (planar boxes / axial-end annular planar / mixed foil-extrusion + box / axis-aligned-Y-axis-gap) without crashing or returning false-negative-by-bug. (4) **Engineer guidance (unchanged from V33)**: until A2-v2 lands, treat A2 PASS as "the geometry has plausible facing faces between the named bodies" — NOT as "gap is small enough to mesh as shared interface" |
| Status | `[QUESTIONABLE 2026-05-08]` per V25 chain — algorithm-path cross-topology consistency confirmed at 5-of-5; gap-detection capability awaits A2-v2 |
| Reference case | case_008_glc305_irt_lagrangian v1 advisor-validation 2026-05-08 (`~/Desktop/case_008_glc305_irt_lagrangian/evidence/v1/a2_advisor_output.json`); spec orderings: `root_mount_pad__root_mount_strut_interface` `mode='shared'` |
| Lesson | The 5-case algorithm-path consistency is now overwhelming evidence on the side that V21 disambiguation closed. The 0.35 mm gap-detection capability is genuinely missing on the side that V25 documents. Sub-sessions should NOT collapse these two into "A2 is field-validated"; the precise reading is "`_run_shared` works on every topology tested; the result schema does not surface gap distance, so gap-defect detection is upstream-incompatible." case_008 sediment continues the V25-aware framing: the 5-of-5 cross-topology PASS strengthens the algorithm side without weakening the V25 finding. **Pattern 6 corollary**: case_008 is the incompressible-RANS-Lagrangian root, and the algorithm-path PASS on its airfoil-mount topology adds further weight that A2's `find_face_facing_target` is fundamental geometry-plumbing — independent of fluid solver class — so A2-v2 only needs to add capability on top of a stable algorithm-path base |

### V37 · thin_wall_advisor 6-topology cross-topology arc closed at `[VALIDATED]` — case_008 airfoil-TE auxiliary tab (incompressible-RANS-Lagrangian root)

| field | value |
|---|---|
| Surface | `ui/backend/services/geometry_ingest/thin_wall_advisor.detect_thin_wall_patches_at_risk` |
| Engineer symptom | case_008 D8 = 0.80 mm thick `trailing_edge_tab_thin` (axis-aligned 0.0008 m × 0.009 m × 0.427 m box from cadquery `Workplane.box`). At background_cell_size=0.020 m and refinement (1,2): `effective_cell_size=0.005 m`, `cells_per_thickness=0.160`, `severity='critical'`, `recommended_level_max=6`. Two auxiliary patches simultaneously evaluated: `root_mount_pad` (1.6 cells/thickness, 'warning') + `root_mount_strut` (2.8 cells/thickness, 'info'). Advisor consistent with prior cross-topology runs |
| Root cause | thin_wall_advisor uses bbox-min as thinness estimator (V10 lesson: exact for axis-aligned plate/beam, lower-bound for curved shells). trailing_edge_tab_thin is axis-aligned, so bbox-min=0.0008 m is exact. Effective cell at level 2 = 0.005 m → 6.25× thicker than the tab → cells_per_thickness=0.16 → critical. The recommended_level_max=6 implies effective cell ≈ 3.1×10⁻⁴ m globally; practically infeasible at chord-scale → refinementRegions slab approach preferred for v2 (per V10 lesson fix #2) |
| Fix | (1) **No code fix needed** — advisor behavior is correct and consistent with all prior cases. (2) **Status promotion**: combine with V10 (curved CATIA Frame 50 mm), V10 line 174 inheritance (case_002b CHT), V10 line 174 (case_003 0.80 mm planar aero), V23 (case_004 rotating-machinery 0.75 mm), V30 (case_006 0.18 mm transonic wing-tip sliver), V10 line 174 (case_007 ship transom 0.80 mm above WL), and **case_008 0.80 mm airfoil-TE auxiliary tab** to declare 6-topology cross-topology arc `[VALIDATED]` per `knowledge_status_convention.md`. (3) **Future-cases extend evidence but no longer change the conclusion** (per V23 lesson) — advisor's correctness arc is closed |
| Status | `[VALIDATED 2026-05-08]`. Originally partial after 3 cases (V23 line 343); intermediate "4-of-4 cross-topology validation closes this advisor's correctness arc" reached at V30 (case_006); now reinforced to **6-topology / 3-orders-of-magnitude-thickness span** with case_008 (V37). Status now: **confirmed (6-case cross-topology, 0.18 mm to 50 mm thickness, no behavioral divergence)** |
| Reference case | case_008_glc305_irt_lagrangian v1 advisor-validation 2026-05-08 (`~/Desktop/case_008_glc305_irt_lagrangian/evidence/v1/{thin_wall_advisor_output.json, d8_thin_wall_consistency.md}`); cross-topology roll-up table at `evidence/v1/d8_thin_wall_consistency.md` |
| Lesson | thin_wall_advisor's bbox-min algorithm is robust across the full industrial-CAD topology space accessible to the project: curved CATIA non-manifold + planar CadQuery aero + rotating-machinery aux + transonic wing-tip sliver + ship-hydro above-waterline + airfoil-TE auxiliary. **Pattern 6 closure**: same algorithm, same outcome, six distinct numerics classes (compressible-buoyant, CHT, incompressible-RANS, MRF, compressible-shock-density-based, multiphase-VOF, incompressible-RANS-Lagrangian). The advisor should be cited in M2.5 CAD-ingest extraction (DEC-V61-198) as a **[VALIDATED]**-tier capability, alongside the (still **[QUESTIONABLE]**) A2 capability. **Promotion-ready**: cross-topology arc closed; future cases produce evidence but no longer change conclusions |

### V38 · chemkinToFoam requires `THERMO ALL` header (bare `THERMO` fails parse) — case_009 (reacting-low-Mach root)

| field | value |
|---|---|
| Surface | OpenFOAM `chemkinToFoam` chemkinReader.lex(); thermo file header parser |
| Engineer symptom | GRI-3.0 `thermo30.dat` (downloaded from Berkeley combustion mirror) starts with `THERMO\n   300.000  1000.000  5000.000`. chemkinToFoam treats line 2 as the first species record and emits `expected <word><label><word><label> (4(2A1,I3)) but found '"0"0.000'` because the temperature-range line does not match the species-element-tuple regex. The bare `THERMO` keyword does not signal "next line is the global temperature range; species records start after that". |
| Root cause | OpenFOAM's chemkinReader expects `THERMO ALL` (chemkin-II convention) to recognize the header line as a temperature range delimiter. The kit-of-files convention varies between mech sources: Berkeley's GRI-3.0 mirror uses `THERMO ALL` (correct); their DRM-19 page links only to chemistry, no thermo, so users typically reuse GRI-3.0 thermo — but if the file gets stripped of the `ALL` suffix (e.g. by some preprocessors), chemkinToFoam fails parse |
| Fix | One-line patch in 08b_load_chemistry_mech.py: `sed 's/^THERMO$/THERMO ALL/' therm.dat`. Idempotent; runs only if needed |
| Status | `[VALIDATED 2026-05-08]` — single instance (case_009) but root-cause-traced and patched in main project's `chemkin_mechanism_loader.py` extraction candidate |
| Reference case | case_009_sandia_flame_d v1 baseline 2026-05-08 (`~/Desktop/case_009_sandia_flame_d/scripts/08b_load_chemistry_mech.py:patch_thermo_header`) |
| Lesson | Chemkin-format files come from many ecosystems (Cantera, ANSYS, in-house tools); chemkinToFoam is strict about the chemkin-II spec. A robust mech-loader must normalize 2-3 well-known header variations (THERMO / THERMO ALL / THERMODYNAMICS) before invoking the converter. The same pattern applies to V39 (END terminator on tran.dat) — these are all "input file format normalization" findings, complementary to V35 (transport-input dual-mode). Bundle V38+V39+V40+V41 as a single `chemkin_mechanism_loader.py` sub-DEC under DEC-V61-198 |

### V39 · chemkinToFoam transport file requires explicit `END` terminator — case_009 (reacting-low-Mach root)

| field | value |
|---|---|
| Surface | OpenFOAM `chemkinToFoam` primitiveEntry parser; transport file reader |
| Engineer symptom | GRI-3.0 `transport.dat` from Berkeley mirror has 110 lines of species transport data with no terminator. chemkinToFoam emits `ill defined primitiveEntry starting at keyword 'AR' on line 1 and ending at line 111` — it reads the entire file as a single dictionary entry expecting an `END` boundary that never arrives |
| Root cause | OpenFOAM's primitiveEntry reader treats the file body as a token stream that must close with a recognized terminator. The chemkin-II spec includes `END` after the transport block; some published mech files (including Berkeley's `transport.dat`) omit it, presumably because chemkin-II readers were lenient. OpenFOAM is strict |
| Fix | One-line patch: append `END\n` to tran.dat if missing. Idempotent (`patch_tran_end()` in 08b script) |
| Status | `[VALIDATED 2026-05-08]` — root-cause traced and patched. Same engineering category as V38 |
| Reference case | case_009_sandia_flame_d v1 baseline 2026-05-08 (`scripts/08b_load_chemistry_mech.py:patch_tran_end`) |
| Lesson | Treat downloaded chemkin files as "needs normalization before chemkinToFoam can ingest" — never as turn-key input. The mech-loader extraction candidate must encode all known patches (V38 header + V39 terminator + V41 Tlow header) as idempotent transformations. Future chem mechs (e.g. Westbrook-Dryer, Lu-Law reduced) will hit different format variants; the loader's interface should be `(chem_url, therm_url, tran_url) → constant/reactions + constant/thermo.compressibleGas` with the patches handled internally |

### V40 · chemkinToFoam transport-input is dual-mode: chemkin tran.dat OR OpenFOAM-format dict — case_009 / case_009 (reacting-low-Mach root)

| field | value |
|---|---|
| Surface | OpenFOAM `chemkinToFoam` argument 3 (transport file) |
| Engineer symptom | GRI tutorial (`tutorials/combustion/chemFoam/gri/Allrun`) passes an OpenFOAM dict file (`transportProperties` with regex `.*` and `As`/`Ts` sutherland coefficients) as the transport input — NOT a chemkin tran.dat. Both formats are accepted by chemkinToFoam; case_009 first attempted real GRI-3.0 chemkin tran.dat (which V38+V39 patches partially mitigate) but eventually used the OpenFOAM-dict path because (a) downloaded GRI-3.0 transport.dat has stricter format mismatch beyond V39 (entries with optional `! comment` mid-line confuse the parser; line 1 `AR  0  136.500  3.330 ...` parses but downstream species sometimes don't), (b) OpenFOAM-dict path with sutherland regex `.*` + air-like coefficients is "good enough" for v1 reacting baseline |
| Root cause | chemkinToFoam's transport-input is overloaded: it sniff-detects whether the file looks like a chemkin tran.dat (line-1 starts with a species name in 4(2A1,I3) format) vs an OpenFOAM dictionary (starts with `FoamFile { ... }` block). Both produce a `transportDict` consumable by reactingMixture. The OpenFOAM-dict mode uses regex-pattern matching (`.*` or per-species name patterns) to set `As`/`Ts` sutherland coefficients uniformly. The chemkin-tran-dat mode populates per-species coefficients from the polynomial fit |
| Fix | (1) For v1 reacting baseline: use OpenFOAM-dict path with air-like sutherland (`As 1.4584e-06; Ts 110.4;`) under regex `.*` — adequate for kEpsilon RANS where turbulent viscosity dominates. (2) For v2: write a Python preprocessor that converts chemkin tran.dat (Lennard-Jones σ + ε/k_B + dipole moment + polarizability) to OpenFOAM-format per-species sutherland by fitting (computed via Chapman-Enskog over T_low..T_high range, fit `mu = As·sqrt(T)/(1+Ts/T)`). Bundle as `chemkin_transport_to_sutherland.py` artifact |
| Status | `[VALIDATED 2026-05-08]` for OpenFOAM-dict mode (used by case_009 v1); per-species fit deferred to v2 |
| Reference case | case_009_sandia_flame_d v1 baseline 2026-05-08 (`constant/chemistry/DRM19/transportProperties`) |
| Lesson | This finding is a feature-not-bug discovery: chemkinToFoam supports a faster path to "viable transport" via the dict-format; case-thread sub-sessions should USE this for v1 reacting baselines (3% molecular viscosity error doesn't matter at Re=22400) and only invest in per-species fitting when v2 sensitivity studies show transport modeling is rate-limiting. Documents an asymmetry in the chemkin ecosystem: chemistry+thermo are well-standardized; transport varies wildly across mech sources |

### V41 · GRI-3.0 thermo header `300.000 1000.000 5000.000` clamps janafThermo Tlow=300 even though species records support Tlow=200; coflow inlet T=291K + buoyancy → cells <300 floods log + eats CPU — case_009 (reacting-low-Mach root)

| field | value |
|---|---|
| Surface | OpenFOAM `janafThermo<EquationOfState>::limit()` temperature-range check |
| Engineer symptom | After V38+V39 patches got chemkinToFoam to convert successfully, reactingFoam at `Time = 1e-05` (first timestep) emitted `attempt to use janafThermo<EquationOfState> out of temperature range 300 -> 3000; T = 299.93337` — repeated thousands of times per timestep (one warning per cell per species per inner iteration). The Sandia coflow physical T = 291 K, bumped to 300 K in 0/T to nominally avoid the limit. Buoyancy-driven flow + small numerical noise drops a fraction of coflow-region cells fractionally below 300 → limit fires repeatedly, flooding the log and adding ~10× wall-clock cost per timestep |
| Root cause | GRI-3.0 thermo30.dat has TWO temperature-range declarations: (1) global header line 2 = `300.000  1000.000  5000.000` (T_low=300, T_common=1000, T_high=5000); (2) per-species records (line 1 of each 4-line block) include their own T_low / T_high — for most GRI species these are `200 / 6000`, supporting Tlow=200K. chemkinToFoam reads the GLOBAL header values into the converted `thermo.compressibleGas` even though per-species records have wider ranges. The result: janafThermo limits at Tlow=300 for ALL species |
| Fix | Edit thermo30.dat header before chemkinToFoam: `sed 's/^   300.000  1000.000  5000.000/   200.000  1000.000  5000.000/'`. Idempotent; preserves per-species records (which already support Tlow=200). Verified by inspection of converted `constant/thermo.compressibleGas`: all species now show `Tlow 200; Thigh 3500;` |
| Status | `[VALIDATED 2026-05-08]` — root-cause traced and patched in 08b. After the patch, cold-flow runs cleanly with no warning flood; ignite stage's heat-release develops T_max from 1880 K (pilot bound) to 1970 K+ in 200 μs of physical time (chemistry initialization stable) |
| Reference case | case_009_sandia_flame_d v1 baseline 2026-05-08 (`scripts/08b_load_chemistry_mech.py:patch_thermo_header` — note: this function name covers both V38 (THERMO ALL) and V41 (Tlow header); rename to `patch_thermo_metadata` in artifact extraction) |
| Lesson | Two takeaways. (1) **Never assume downloaded chem mech files are configured for the temperature regime your case needs**. Sandia Flame D has T from 291K (coflow) to ~2070K (peak flame); that range demands Tlow=200K headers. Some mech repositories ship with Tlow=300 as a "safe default" assuming combustion users won't see <300K. Your case might. (2) **Warning floods are not free**. Each `attempt to use ... out of range ...` warning involves stderr formatting + I/O; on a 11.6k-cell case with 21 species and 3 inner PIMPLE iterations, a single timestep can emit 1M+ warnings, dominating wall-clock. The Tlow patch is not a cosmetic fix — it converts an "unrunnable" case into a "runnable" one. Bundle with V38+V39+V40 as the `chemkin_mechanism_loader.py` extraction (DEC-V61-198 sub-DEC) |

### V42 · A2 advisor `_run_shared` cross-topology PASS on combustion-burner exterior mount (case_009) — 6th algorithm-path PASS; gap-detection still pending V25 fix

| field | value |
|---|---|
| Surface | `ui/backend/services/geometry_ingest/virtual_interface_detector.detect_virtual_interfaces` (A2 advisor; landed 2026-05-08 commit `a09ae0a`) |
| Engineer symptom | case_009 D1 = 0.35 mm gap between `coflow_plenum_mount_bracket` (46×3×8 mm box) and `coflow_plenum_mount_shim` (34×3×4 mm box), both axis-aligned, Z-axis gap, exterior to flame domain. FreeCAD distToShape ground truth = 0.350000 mm exact (4 closest-point pairs). A2 `_run_shared` returns `matched=True` for both bracket-first and shim-first orderings; `bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`, `normal_dot=1.0` (all hardcoded placeholders per V25). 0.35 mm gap is invisible to the result schema |
| Root cause | Same as V25 / V33 / V36: `_run_shared` lines 200-201 hardcode `bbox_overlap_fraction = 1.0` and `area_diff_fraction = 0.0` regardless of actual face geometry. A2 has no API surface for gap-as-defect detection. case_009 is the **6th** algorithm-path PASS (003 + 004 + 005 v2 + 006 + 007 + 008 + 009 — counting 007 = V33, 008 = V36; case_009 = V42), confirming V25 placeholder semantic is **independent of numerics class** (4 fluid solver families now: compressible-RANS, MRF, density-based, multiphase-VOF, Lagrangian, reacting-low-Mach). The 6-of-6 confirmation overdetermines the V25 advisor-scope-expansion sub-DEC for landing |
| Fix | A2-v2 sub-DEC (drafted at `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`): add `inter_face_gap_mm: float \| None` to `DetectedInterface`; populate from face-plane perpendicular distance; add `should_have_been_shared_with_unintended_gap(detected, max_gap_mm)` classifier. case_009 confirms 6-of-6 → land next session |
| Status | `[QUESTIONABLE 2026-05-08]` per V25 chain — algorithm-path cross-topology consistency confirmed at 6-of-6; gap-detection capability awaits A2-v2 |
| Reference case | case_009_sandia_flame_d v1 baseline 2026-05-08 (`~/Desktop/case_009_sandia_flame_d/evidence/v1/d1_advisor_exercise.md`); spec orderings: `bracket_shim_interface_d1` `mode='shared'` |
| Lesson | The 6-case algorithm-path consistency is now overwhelming evidence on the side that V21 disambiguation closed. case_009 adds the **reacting-low-Mach** numerics class to the cross-topology arc, the most physically distinct from the original (compressible-buoyant-RANS, where A2 was first extracted). Pattern 6 corollary: A2's `find_face_facing_target` is fundamental geometry-plumbing — independent of fluid solver class. A2-v2 needs only to extend capability on top of a stable algorithm-path base. **Land A2-v2 next session**: 6 cases is overdetermined; further roster cases would produce a 7th, 8th, ... PASS but no new V-finding (per V23 lesson). The arc on the algorithm-path side is **closed**; the gap-detection-side arc is **open + drafted + ready-to-land** |

### V43 · A2 advisor `_run_shared` cross-topology PASS on vehicle-aero side-mirror trim (case_010) — 7th algorithm-path PASS; gap-detection still pending V25 fix

| field | value |
|---|---|
| Surface | `ui/backend/services/geometry_ingest/virtual_interface_detector.detect_virtual_interfaces` (A2 advisor; landed 2026-05-08 commit `a09ae0a`) |
| Engineer symptom | case_010 D1 = 0.35 mm lateral gap between `side_mirror_outboard` (310 × 95 × 155 mm rounded box at outboard-y trailing edge of mirror housing) and `mirror_edge_trim_strip` (135 × 8 × 48 mm box). Analytical ground truth from `build_cad.py` constants (FreeCAD unavailable on host; STEP byte-stable header normalization makes analytical and FreeCAD round-trip equivalent) = 0.350000 mm exact match. A2 `_run_shared` invoked via `detect_virtual_interfaces` on the (housing, trim) pair: `matched=True`, `body_owner='side_mirror_outboard'`, `face area = 4.8e+04 mm²`, `normal_dot = -1.0`, `bbox_overlap_fraction = 1.0` (synthetic placeholder), `area_diff_fraction = 0.0` (synthetic placeholder). 0.35 mm gap is invisible to the result schema |
| Root cause | Same as V25 / V33 / V36 / V42: `_run_shared` lines 200-201 hardcode `bbox_overlap_fraction = 1.0` and `area_diff_fraction = 0.0` regardless of actual face geometry. A2 has no API surface for gap-as-defect detection. case_010 is the **7th** algorithm-path PASS (003 + 004 + 005 v2 + 006 + 007 + 008 + 009 + 010 — counting 007 = V33, 008 = V36, 009 = V42, 010 = V43), confirming V25 placeholder semantic is **independent of numerics class** (now 8 fluid solver families: compressible-RANS, MRF, density-based, multiphase-VOF, Lagrangian, reacting-low-Mach, **incompressible-LES**). The 7-of-7 confirmation overdetermines the V25 advisor-scope-expansion sub-DEC for landing |
| Fix | A2-v2 sub-DEC (drafted at `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`): add `inter_face_gap_mm: float \| None` to `DetectedInterface`; populate from face-plane perpendicular distance; add `should_have_been_shared_with_unintended_gap(detected, max_gap_mm)` classifier. case_010 confirms 7-of-7 → land next session |
| Status | `[QUESTIONABLE 2026-05-08]` per V25 chain — algorithm-path cross-topology consistency confirmed at 7-of-7 (final case in 10-case roster); gap-detection capability awaits A2-v2 |
| Reference case | case_010_drivaer_fastback_les v1 baseline 2026-05-08 (`~/Desktop/case_010_drivaer_fastback_les/evidence/v1/a2_d1_falsification.json`); spec ordering: `side_mirror__mirror_trim_interface` `mode='shared'` |
| Lesson | The 7-case algorithm-path consistency is the cleanest piece of A1-A5 sediment in the project — the cross-topology arc is now **closed and overdetermined**. case_010 adds the **incompressible-LES** numerics class to the arc, the 8th distinct fluid-numerics family. **No further cross-topology cases are planned** (10-case roster complete); A2-v2 sub-DEC is the only remaining work to upgrade `[QUESTIONABLE]` → `[VALIDATED]`. Pattern 6 closure on the algorithm-path side: A2's `find_face_facing_target` is geometry-plumbing, demonstrably independent of fluid solver class across 8 numerics families. **Land A2-v2 next session**: per V42 lesson, "6 cases is overdetermined; further roster cases would produce a 7th, 8th, ... PASS but no new V-finding" — V43 is exactly that 7th PASS, confirming the prediction |

### V44 · thin_wall_advisor 7-topology cross-topology arc reinforces `[VALIDATED]` — case_010 vehicle-aero auxiliary underbody plate (incompressible-LES root)

| field | value |
|---|---|
| Surface | `ui/backend/services/geometry_ingest/thin_wall_advisor.detect_thin_wall_patches_at_risk` |
| Engineer symptom | case_010 D8 = 0.80 mm thick `underbody_sensor_cover_thin` (axis-aligned 0.420 m × 0.210 m × 0.0008 m box from cadquery `Workplane.box`). At background_cell_size=0.16 m and 3 refinement-level scenarios (1,2)/(2,3)/(3,4): all return `severity='critical'` with `cells_per_thickness=0.020/0.040/0.080`, all unanimous `recommended_level_max=9`. Advisor consistent across 3 level scenarios (escalating thinness ratio → escalating recommendation, monotonic) |
| Root cause | thin_wall_advisor uses bbox-min as thinness estimator (V10 lesson). underbody_sensor_cover_thin is axis-aligned, so bbox-min=0.0008 m is exact. Effective cell size at level 2 = 0.04 m → 50× thicker than the plate → cells_per_thickness=0.02 → critical. The recommended_level_max=9 implies effective cell size ≈ 0.3 mm → practically infeasible at vehicle-aero scale (would explode global cell count); refinementRegions slab approach preferred for v2 (per V10 lesson fix #2), or — since `underbody_sensor_cover_thin` is auxiliary defect-only body NOT in `parts_manifest.yaml.parts.<name>.include_in_force_coefficients` — drop the patch from sHM input STL as v1 simplification (V10 Pattern 5) |
| Fix | (1) **No code fix needed** — advisor behavior is correct and consistent with prior 6 cases. (2) **Status reinforcement**: case_010 vehicle-aero is the **7th** topology in the cross-topology arc (curved CATIA Frame 50 mm + planar CadQuery aero plate 0.80 mm + rotating-machinery aux yaw shim 0.75 mm + transonic wing-tip sliver 0.18 mm + ship-hydro transom plate 0.80 mm above WL + airfoil-TE auxiliary tab 0.80 mm + **vehicle-underbody auxiliary plate 0.80 mm**). V37 declared `[VALIDATED]` at 6 topologies; case_010 reinforces to **7 topologies / 3-orders-of-magnitude-thickness span** with **no behavioral divergence**. (3) **Future-cases extend evidence but no longer change the conclusion** (per V23 lesson) — advisor's correctness arc is closed |
| Status | `[VALIDATED 2026-05-08]` (reinforced from V37 6-topology to **7-topology** with case_010). Originally partial after 3 cases (V23); reached `[VALIDATED]` at V37 (case_008, 6 topologies); now reinforced at V44 with the **incompressible-LES** numerics class. Status now: **confirmed (7-case cross-topology, 0.18 mm to 50 mm thickness, no behavioral divergence)** — final case in the 10-case roster |
| Reference case | case_010_drivaer_fastback_les v1 advisor-validation 2026-05-08 (`~/Desktop/case_010_drivaer_fastback_les/evidence/v1/thin_wall_d8_falsification.json`); 3 refinement scenarios: levels (1,2)/(2,3)/(3,4) all `severity=critical` with `cells_per_thickness=0.020/0.040/0.080` |
| Lesson | thin_wall_advisor's bbox-min algorithm is robust across the **full** industrial-CAD topology space accessible to the project: curved CATIA non-manifold + planar CadQuery aero + rotating-machinery aux + transonic wing-tip sliver + ship-hydro above-waterline + airfoil-TE auxiliary + **vehicle-underbody auxiliary**. **Pattern 6 closure (final)**: same algorithm, same outcome, **8 distinct numerics classes** (compressible-buoyant + CHT + incompressible-RANS + MRF + compressible-shock-density-based + multiphase-VOF + incompressible-RANS-Lagrangian + **incompressible-LES**). The advisor should be cited in M2.5 CAD-ingest extraction (DEC-V61-198) as a **`[VALIDATED]`-tier capability**, alongside the (still **`[QUESTIONABLE]`**) A2 capability. **Cleanest piece of A1-A5 sediment in the project** — promotion-ready at the highest confidence tier the project has |

### V45 · First transient LES infrastructure (incompressible-LES root): pimpleFoam + WALE + nutUSpaldingWallFunction + cubeRootVol filter + fieldAverage/Q/Lambda2/yPlus FOs (case_010)

| field | value |
|---|---|
| Surface | OpenFOAM `pimpleFoam` LES infrastructure absent from main project before case_010; new artifact set required |
| Engineer symptom | case_010 v1 first transient LES for project; needs WALE LES model in `constant/turbulenceProperties` (with `delta cubeRootVol; cubeRootVolCoeffs { deltaCoeff 1; }` and `WALECoeffs { Ck 0.094; Ce 1.048; Cw 0.325; }`); `nutUSpaldingWallFunction` for wall-modeled regime y+=30-100 (NOT `nutLowReWallFunction` — that's only valid at y+ < 5); 0/{U,p,nut} fields with NO nuTilda/k/omega (LES has built-in subgrid via WALE filter); `system/fvSchemes` LES-friendly settings (`ddtSchemes: backward` 2nd-order; `divSchemes: linearUpwindV grad(U)` low-dissipation; `gradSchemes: Gauss linear`); `system/controlDict` PIMPLE controls (nOuterCorrectors=2, nCorrectors=2, nNonOrthogonalCorrectors=1) + 4 function objects (`forceCoeffs1` + `fieldAverage1` with `cleanRestart=true` + `Q` + `Lambda2` + `yPlus`); two-stage transient/averaging restart workflow (transient settle 0 → 2 L/U_inf, then averaging 2 → 7 L/U_inf with `fieldAverage` `timeStart=2*L/U_inf`) |
| Root cause | Pattern 6: case_010 inherits NO V-findings from V3-V42 (RANS / MRF / density-based / VOF / Lagrangian / reacting are all distinct numerics families). Transient LES introduces a numerics class with no prior anchor in the project. Hand-coded artifacts: `templates/turbulenceProperties_LES.j2`, `templates/fvSchemes_LES.j2`, `templates/fvSolution_LES.j2`, `templates/controlDict_LES.j2` (with field-averaging FO), `templates/0/{U,p,nut}.j2`, `scripts/08b_write_les_fvschemes.py`, `scripts/08c_write_les_turbulenceProperties.py`, `scripts/08d_write_wall_functions.py`, `scripts/08e_write_field_average_function_object.py` (composes transient AND averaging stages with stage flag) |
| Fix | (1) **case-local v1 implementation complete**: all templates + writers exist in case_010 sandbox; v1 ran scaffold → CAD → advisor → blockMesh → sHM (interrupted iter 2; see V46 if filed) end-to-end. (2) **Artifact extraction candidates** (per kickoff §6 step 5; all <250 LOC each): `les_fvschemes_writer.py` + `les_turbulence_properties_writer.py` + `field_average_function_object_writer.py` + `q_criterion_post_processor.py`. None block v1 sediment. (3) **Two-stage workflow contract** (S19 candidate): transient stage NEVER includes `fieldAverage` (or signal contaminated by initial transient); averaging stage uses `fieldAverage` with `cleanRestart=true` and `timeStart` set ≥ 2 L/U_inf to discard settling. (4) **WALE constants** are OpenFOAM defaults (`Ck=0.094, Ce=1.048, Cw=0.325`); `dynamicKEqn` available as v2 fallback if WALE under-resolves the rear-base separation |
| Status | partial (1 case · case_010 v1) — first LES anchor in project. Future LES cases (LES+CHT, hybrid LES-RANS, compressible-LES) inherit this via Pattern 6 |
| Reference case | case_010_drivaer_fastback_les v1 baseline 2026-05-08 (`~/Desktop/case_010_drivaer_fastback_les/{templates/*LES*.j2, scripts/08{b,c,d,e}_*.py, evidence/v1/REPORT.md}`); transient stage controlDict produced by `08e ... --stage transient`; averaging-stage variant by `08e ... --stage averaging` |
| Lesson | LES + RANS share `pimpleFoam` solver but have NO shared numerics class — separate fields (no nuTilda/k/omega in LES; no subgrid in RANS), separate wall-function semantics (Spalding works for both wall-modeled regimes but k/omega-driven RANS wall functions don't apply to LES), separate `fvSchemes` (LES wants 2nd-order in time + low-dissipation div; RANS often uses 1st-order Euler + upwind), separate function-object stack (LES needs `fieldAverage` + Q/Lambda2; RANS doesn't unless extracting unsteady signals). **Pattern 6 reinforcement (final)**: LES is the 9th numerics class for this advisor/playbook arc — Pattern 6 inheritance applies forward (case_010 establishes inheritance receivers for all future LES cases). **Promotion priority** for LES infrastructure: `field_average_function_object_writer.py` is highest priority because it has the most-cross-cutting two-stage restart contract; the others are template-renderers with localized scope |

### V46 · snappyHexMesh on 4.6M-bg-cell vehicle-aero half-domain interrupted at refinement iteration 2 with 6.5M cells (sHM scaling V-finding for incompressible-LES root)

| field | value |
|---|---|
| Surface | `snappyHexMesh -overwrite` on case_010 vehicle-aero half-domain (60 m × 14 m × 23 m at base cell 0.16 m) |
| Engineer symptom | sHM started cleanly after blockMesh + surfaceFeatureExtract. Made it through Shell refinement iteration 0 (4.6M → 4.86M cells) and iteration 1 (4.86M → 6.55M cells with 1.9M level-2 cells). Iteration 2 began edge-intersection-test on 60M edges + 46M edges-to-retest, was interrupted before completing (case-thread sandbox docker container killed mid-test by external process before iteration 2 finished). Wall-clock at interrupt: ≈ 5 min from start. polyMesh in `case/constant/polyMesh/` remains the original blockMesh (sHM `-overwrite` had not yet committed) |
| Root cause | base cell 0.16 m on (60 m × 14 m × 23 m) half-domain → 4.644M bg cells. With body refinement levels (4,5) + mirror (5,6) + wheels (4,5) + wake-box (3) and `nCellsBetweenLevels=3` buffer, projected total cells exceed 15-25M. Iteration 2 specifically hits 60M edges to test; on a single-process Mac docker container without parallel decomposition, edge-intersection scales superlinearly with cell count. Practical wall-clock for full sHM completion at this base cell: estimated 15-30 min |
| Fix | (1) **v2 v1-of-2 simplification (recommended)**: bump base cell from 0.16 m to 0.30 m → bg cell count drops to ≈ 0.55M; refinement levels can stay since they're relative; expected sHM total cells 5-10M with completion in 5-10 min. (2) **v2 v2-of-2 (parallel)**: decomposePar + parallel sHM (-parallel flag) — typical 4-8x speedup but introduces zero-edge load-balance edge cases not yet tested in project. (3) **Skip layer addition in v1**: `addLayers false` in snappyHexMeshDict — case_010 already does this. (4) **In sandbox `config/case.yaml.mesh.base_cell_m`**: change to 0.30 m for v2; document switch in v2 REPORT.md |
| Status | open (case_010 v2 not yet run) |
| Reference case | case_010_drivaer_fastback_les v1 baseline 2026-05-08 (`~/Desktop/case_010_drivaer_fastback_les/case/log/03_snappyHexMesh.log` 184 lines, ends mid-iter-2 edge-intersection-test) |
| Lesson | Vehicle-aero half-domain LES at base cell 0.16 m is at the boundary of single-process sHM capability on a Mac. Smaller base cell would push past 24M-cell limits in `castellatedMeshControls.maxGlobalCells`. **For first-LES-of-project shaking-down**, prefer coarser base cell (0.30 m) + relative refinement levels — same final near-body cell size, much shorter sHM wall-clock. **For production LES** (v3+), decompose + parallel sHM is the right tooling. Pattern 6 inheritance: this is an LES-specific finding (RANS/MRF cases didn't see it because typical RANS bg meshes are 100k-500k cells, not 4.6M). Future LES cases should default to 0.30 m base cell for first iteration |

### V47 · snappyHexMesh `minMedialAxisAngle` vs `minMedianAxisAngle` typo silently breaks layer addition (chtMR LES/CHT inheritance edge case)

| field | value |
|---|---|
| Surface | `snappyHexMesh -overwrite` on case_015 vattenfall T-junction (3-region cellZone setup); FOAM FATAL IO ERROR `Entry 'minMedialAxisAngle' not found in dictionary "/case/system/snappyHexMeshDict/addLayersControls"` after castellation + snap completed cleanly |
| Engineer symptom | sHM ran cleanly through castellatedMesh + snap, then died at `Adding layers` stage with the IO error above. Cells per refinement level + locationsInMesh + cellZones reports all showed sane numbers; conjugate baffle faces were correctly created (`region_branch_fluid_to_region_wall_solid` 36 640 faces). Failure is purely at dictionary-key parsing in `addLayersControls` |
| Root cause | OpenFOAM v2312 ESI requires `minMedialAxisAngle` (medial axis) — common typo `minMedianAxisAngle` (median statistic) is silently rejected by older OF versions but raises FATAL in v2312. Documentation across OF versions inconsistent. Project's case_011 chtMR template lacks layer addition (steady CHT skips it), so this typo never surfaced before; case_015 is the first chtMR variant with mandatory layer addition (LES wall-modeled regime needs prism layers for y+ targeting) |
| Fix | (1) Use `minMedialAxisAngle 90;` verbatim (medial). (2) Project-wide grep `grep -rn 'minMedianAxisAngle' .planning/ ~/Desktop/case_*/` to scrub stale templates inherited from older docs. (3) Future CHT+LES scaffolds inherit case_015's `02_scaffold_case.py::emit_snappyHexMesh` rather than retyping by hand |
| Status | partial (case_015 first appearance — but high-confidence fix; appears in OF v2312 ESI documentation under correct key) |
| Reference case | case_015_vattenfall_t_junction_thermal_striping (`~/Desktop/case_015_vattenfall_t_junction/scripts/02_scaffold_case.py::emit_snappyHexMesh` line ~110, fixed 2026-05-10) |
| Lesson | Pattern 4 (configuration-time checks) candidate: a dict-key sanity check (regex over snappyHexMeshDict against allowed-key whitelist) would catch this before docker spin-up. The cost of the wasted 5-min sHM run motivates a one-line precheck. **Inheritance**: case_015 is first chtMR variant with layer addition — case_011 (steady CHT) skipped layers, so this typo class wasn't surfaced until LES regime forced wall-prism resolution requirement |

### V48 · chtMultiRegionFoam top-level controlDict function objects require explicit `region` keyword for cross-region targeting (LES+CHT compound numerics root)

| field | value |
|---|---|
| Surface | `chtMultiRegionFoam` top-level `system/controlDict` function objects (probes, fieldAverage) — mid-step proof-of-concept finding from case_015 scaffold |
| Engineer symptom | Top-level `controlDict.functions { probes_T_main { ... } fieldAverage_main { ... } }` without explicit `region` keyword silently picks the first dispatched region (alphabetical order) instead of the intended region. For probes targeting wall-T at the main pipe outlet, the function-object writes data from `region_branch_fluid` cells (because branch is alphabetically first) and the resulting JSON looks plausible but reports the wrong physics |
| Root cause | chtMultiRegionFoam dispatches function objects per-region by default, iterating the `regions ( fluid (...) solid (...) );` list. Without explicit `region` keyword, the FO is registered in the first dispatched region. Per-region `controlDict` (in `system/<region>/controlDict`) avoids this but breaks the `top-level controls time loop` invariant of multi-region solvers |
| Fix | (1) **Always set `region <name>;` inside each function-object block in top-level controlDict** for chtMR. (2) For wall-T probes that should sample fluid-side T at fluid-solid interface, target `region_main_fluid` explicitly. (3) `fieldAverage` per-region: declare one fieldAverage block per fluid region in top-level controlDict with `region` set; alternatively use per-region `system/<region>/controlDict` with the same FO names. (4) **case_015 scaffold encodes this** in `02_scaffold_case.py::emit_top_controlDict` |
| Status | partial (case_015 first appearance — applies to all chtMR LES/transient variants) |
| Reference case | case_015_vattenfall_t_junction_thermal_striping (`02_scaffold_case.py::emit_top_controlDict` 2026-05-10) |
| Lesson | First compound numerics root (LES + CHT) surfaces a function-object dispatch nuance that single-region LES (case_010) and steady CHT (case_011) couldn't show: case_010 had only one fluid region, case_011 used per-region `system/<region>/controlDict`. Compound roots are useful for surfacing dispatch nuances that hide in either parent. **Pattern 6 reinforcement**: LES + CHT each inherits parts of its parents' V-history, but the COMBINATION surfaces new V-rows — this is the value of the compound-numerics-root methodology |

### V49 · Wall-modeled LES at conjugate fluid-solid baffle requires the compressible:: triplet (nut + alphat + k wall functions) for energy-equation coupling (LES+CHT compound root)

| field | value |
|---|---|
| Surface | `chtMultiRegionFoam` LES setup at `(.*_to_.*)` conjugate baffle patches — case_015 BC writer finding |
| Engineer symptom | Initially patches set with `nutUSpaldingWallFunction` only on `nut` field, no special treatment on `alphat`/`k` at the conjugate baffle. Solver runs cleanly but wall heat-flux reported by `wallHeatFlux` function-object diverges by 10-30% vs the expected nominal (computed from log-law assumption) — silent inconsistency that doesn't trip residuals |
| Root cause | chtMultiRegionFoam uses compressible thermo (heRhoThermo) internally even for incompressible-like water flows. The conjugate `compressible::turbulentTemperatureCoupledBaffleMixed` BC on T expects companion compressible:: variants on its sibling fields: `compressible::alphatJayatillekeWallFunction` on `alphat` (Jayatilleke wall function for thermal eddy diffusivity) AND `kqRWallFunction` on `k` (or compressible wall-treated equivalent). Mixing incompressible-style `nutUSpaldingWallFunction` with non-compressible alphat treatment produces internally consistent fields BUT the energy-equation coupling at the baffle gets the wrong Prt-weighted heat flux |
| Fix | (1) On every `(.*_to_.*)` patch, set ALL THREE: `nut: nutUSpaldingWallFunction`, `alphat: compressible::alphatJayatillekeWallFunction { Prt 0.85; }`, `k: kqRWallFunction`. (2) On every outer-wall (no-coupling) patch (`.*_outer_wall.*`), apply the same triplet — these are physical walls. (3) `case_015 02_scaffold_case.py` `emit_nut/emit_alphat/emit_k` encode this; pattern is replicable to any chtMR LES variant |
| Status | partial (case_015 first appearance) |
| Reference case | case_015_vattenfall_t_junction_thermal_striping (`02_scaffold_case.py::emit_nut/emit_alphat/emit_k` 2026-05-10) |
| Lesson | First compound LES + CHT root surfaces a wall-function compatibility gradient that single-LES (case_010 — no conjugate, just no-slip walls with Spalding) and steady CHT (case_011 — laminar, no wall function regime to choose) couldn't expose. **Inheritance receiver design**: future chtMR LES variants (case_016 compressible-DES if it goes wall-modeled, future case_017+ multi-region LES) can inherit case_015's BC writer pattern verbatim. **Pattern 4 candidate**: a `wall_function_compat_advisor` that checks alphat/nut/k triplet consistency at conjugate patches would catch the silent-divergence class of bugs |

### V50 · A2 advisor `_run_shared` cross-topology PASS on pipe-pipe weld-toe topology (case_015 D5) — 12th algorithm-path PASS; gap-detection still pending V25 fix

| field | value |
|---|---|
| Surface | `virtual_interface_detector.detect_virtual_interfaces` on case_015 D5 pipe-pipe weld misalignment (60 µm offset between main pipe outer wall and branch pipe outer wall at T-junction toe) |
| Engineer symptom | A2 v1 returned `matched=True` with diagnostic `shared face on 'main_outer_wall_at_toe' (area=800)`. The 12th cross-topology PASS in the V19→V21→V22→V23→V25→V33→V36→V42→V43→V44 chain. Algorithm correctly traverses the planar-slab approximation of the weld-toe arc |
| Root cause | Same as V25: `_run_shared` returns matched=True with hardcoded placeholder fields (`bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0`) regardless of the actual 60 µm offset. The algorithm exercises the planar-face-screening filter cleanly on the cylindrical-adjacency tangent-plane approximation, but does NOT field-validate the offset as a defect |
| Fix | (1) **No code change** — case_015 row reinforces the V25 chain at the 12th cross-topology data point. (2) A2-v2 sub-DEC remains the dependency for true field-validation (`patches/draft_a2_v2_gap_detection_2026-05-08.md`). (3) Knowledge-status convention compliance: case_015's `a2_falsification_d5.py` records `[QUESTIONABLE 2026-05-08]` marker explicitly in evidence JSON and case profile |
| Status | partial · still [QUESTIONABLE 2026-05-08] (12-case cross-topology — V25 chain unchanged; A2-v2 still pending) |
| Reference case | case_015_vattenfall_t_junction_thermal_striping (`scripts/a2_falsification_d5.py` + `evidence/v1/a2_d5.json` 2026-05-10) |
| Lesson | 12 cross-topology data points strengthens the case for A2-v2 land + injection re-test. The cylindrical-adjacency topology (pipe-pipe weld) is genuinely new — case_007 transom-WL was the closest prior planar-slab approximation of curved geometry, and case_015 demonstrates the same approximation pattern (degenerate-bbox planar-slab) is needed for cylindrical adjacencies. **A2-v2 design implication**: gap-detection must work on planar-slab-approximated cylindrical adjacencies, not just true planar plate-on-plate, since real industrial weld topologies are predominantly cylindrical. **Counter row**: this finding does NOT trigger STOP under v6.1 (autonomous_governance: false; A2 algorithm exists, only field-validation incomplete) |

### V51 · snappyHexMesh multi-region cellZone tagging on intersecting/overlapping fluid volumes silently degrades to single-region (chtMR T-junction inheritance edge case)

| field | value |
|---|---|
| Surface | `snappyHexMesh -overwrite` cellZone tagging for case_015 vattenfall T-junction (3 intersecting volumes: main_fluid pipe + branch_fluid pipe + wall_solid annulus). Three sHM iterations attempted across two cellZone-tagging strategies |
| Engineer symptom | **Strategy 1** (`locationsInMesh` seeds): sHM ran cleanly through castellation + snap + layer addition (3.3M cells, 0 quality errors). `splitMeshRegions -cellZones -overwrite` then created **only 2 of 3 expected regions** — `region_main_fluid` polyMesh was missing because the wall_solid seed was at radius 110 mm (outside the 76 mm pipe OD), so flood-fill from the wall_solid seed escaped into the open volume around the pipe and got pre-marked by the main_fluid seed walking from inside the pipe. **Strategy 1 retry** (seed moved to (0.4, 0.073, 0) and ordered wall_solid first): split now produced main_fluid + branch_fluid but lost wall_solid (the inverse problem). **Strategy 2** (`refinementSurfaces.<name>.{cellZone <name>; cellZoneInside inside}` per region with single discard-only locationInMesh): sHM ran 21 min (1257 s vs 322 s for strategy 1), reported "Found 3 closed, named surfaces. Assigning cells in/outside these surfaces to the corresponding cellZone." But `splitMeshRegions` then created `region_main_fluid` + two unnamed `domain0` + `domain2` regions — only main_fluid was correctly tagged; branch_fluid and wall_solid surfaces were treated as the same un-named "domain" region |
| Root cause | At the T-junction, the branch fluid volume **physically intersects** the main fluid volume (the branch comes down into the main pipe). Both STLs (main_fluid + branch_fluid) cover overlapping cells in the intersection zone. With `cellZoneInside inside` semantics, a cell inside BOTH surfaces gets tagged by whichever surface is processed first; cells inside one but not the other get the un-shared tag. The wall_solid STL is an annular shell with two surfaces (OD outer + ID inner) — sHM's surface-flood-fill treats the annulus as not-strictly-watertight at the tee inner-corner where the branch wall ID meets main wall ID. Combined effect: only one of the three intended cellZones gets reliably tagged across the full geometry. **Codex's CAD script (verbatim per brief — "Do NOT redesign") creates these intersecting+annular volumes by design** for the OECD/NEA Vattenfall benchmark; the V-finding is the sHM tagging behavior, not the CAD |
| Fix | **In-scope (sub-session)**: 5-min wall-time investigations attempted both strategies; strategy 2 closer to working but still degenerate. **Out-of-scope-for-Codex-brief (next iteration)**: (1) modify `build_cad.py` to **boolean-subtract the branch-tee intersection from one of the fluid volumes** so the two are strictly disjoint (this is the canonical OECD/NEA Vattenfall benchmark mesh prep — the "fluid domain" is one connected union, not two overlapping pipes); use a single fluid region with internal `faceSet`-based patch separation if branch-vs-main thermal histories must be tracked. (2) Use `topoSet` post-snap to manually carve cellZones from explicit cell coordinates (heavy lift but exhaustive). (3) Use **mergeBranchAndMainIntoOneFluidRegion** approach: case_002b uses 6 solid regions but only 1 fluid; same pattern fits Vattenfall T-junction since both fluids are water with same thermophysics — the only reason to keep them separate is BC bookkeeping at the inlets, which can be done via faceSet patch decomposition |
| Status | open (case_015 surfaces the finding; full fix requires Codex CAD revision OR adopt single-fluid-region topology — neither in single-session scope per brief boundaries) |
| Reference case | case_015_vattenfall_t_junction_thermal_striping (`scripts/02_scaffold_case.py::emit_snappyHexMesh` 3 iterations 2026-05-10 — locationsInMesh strategy 1 + 1-retry, refinementSurfaces strategy 2 — all degenerate to ≤ 2 of 3 regions split; case/log/03_snappyHexMesh.log + case/log/04_splitMeshRegions.log) |
| Lesson | First multi-region chtMR with **intersecting fluid volumes** (T-junction-class topology) surfaces a CAD-design assumption that case_011 (compact-HX with strictly disjoint hot/cold/solid box-packs) and case_002b (single fluid + 6 thin shell solids — no fluid-fluid intersection) couldn't expose. The Vattenfall benchmark is canonically meshed as **one connected fluid domain with internal mass-flow boundary conditions** at the branch-main inlet plane, not as two intersecting pipe volumes — Codex's verbatim CAD generates the latter. **Inheritance receiver design**: future T-junction-class cases must either (a) modify CAD to boolean-subtract the intersection or (b) adopt single-fluid-region + faceSet patches. **Pattern 4 candidate**: a `multi_region_cad_topology_check` advisor that detects fluid-volume intersections in the parts manifest and warns before sHM would short-circuit this 21-min wall-time investigation. **Counter row**: this finding does NOT trigger STOP under v6.1 (autonomous_governance: false; mesh strategy known, requires Codex round 2 for CAD revision per round-cap=3 budget) |

### V52 · `kOmegaSSTIDDES` turbulence-block registered under `simulationType LES`, not `RAS` (OpenFOAM-ESI 2312)

| field | value |
|---|---|
| Surface | case_016 `constant/turbulenceProperties` initial scaffold (Codex brief deliverable §4 + Codex CAD response): `simulationType RAS;` + `RAS { RASModel kOmegaSSTIDDES; ... }`. rhoPimpleFoam fatal error at runtime: `Unknown RASModel type kOmegaSSTIDDES`; valid RAS models listed; IDDES is absent because IDDES is a hybrid LES model in ESI |
| Engineer symptom | Codex brief verbatim says "kOmegaSSTIDDES preferred" + lists it under a `RAS { ... }` block. Sub-session followed brief verbatim → runtime error → looked up ESI source: `kOmegaSSTIDDES` is registered via `LESModel` template-class macro, not `RASModel`, even though the model implements a RAS-zone (wall layer) and LES-zone (interior) hybrid blending |
| Root cause | Codex case-design knowledge gap: `kOmegaSSTIDDES` is **functionally** a hybrid model that uses RAS in wall layer + LES away from wall, but is **administratively** registered under the LES type registry because the blending function inputs the LES filter width. Codex appears to have generalized from "k-ω-SST is RAS" + "IDDES uses k-ω-SST" → "kOmegaSSTIDDES goes in the RAS block" — incorrect for ESI. Same pattern as V29 (BC name fork mismatch ESI vs foam-extend) and V31 (defect→advisor mapping wrong). Compounded evidence: V26 + V29 + V31 + V52 = 4 distinct Codex case-design knowledge-gap categories surfaced in 3 cases (006, 010, 016) |
| Fix | (1) **Case-local**: rewrite turbulenceProperties as `simulationType LES; LES { LESModel kOmegaSSTIDDES; delta IDDESDelta; ... }` — runtime accepts and PIMPLE iteration proceeds. (2) **Cross-case sediment**: the `codex_case_design_protocol.md` revision (already overdetermined by V26+V29+V31 per V31's lesson) now needs a 4th declarative-and-verified column: **turbulence-model-registry-block** (LES vs RAS) for hybrid models. The protocol should auto-emit the correct block by querying `OpenFOAM-2312/etc/caseDicts/postProcessing/numerical/turbulenceFields` model lists. (3) **No advisor candidate** — this is a Codex output validation problem, not a CFD geometry/physics problem; belongs in case-design protocol not in advisor stack |
| Status | partial — case-local fix applied; protocol revision pending the V26+V29+V31+V52 sub-DEC. Confirmed across one case (case_016); will inherit to any future compressible-DES / compressible-LES case. Status now: `[QUESTIONABLE 2026-05-11]` whether SA-DDES (alternate per Codex brief) has the same registration; verification pending: run a duplicate case with SA-DDES and observe |
| Reference case | case_016_m219_cavity_des_acoustic (`scripts/02_scaffold_case.py::write_turbulenceProperties` 2026-05-11; case/log/solver_rhoPimpleFoam.txt initial fatal-error trace before V52 fix) |
| Lesson | Codex case-design knowledge gaps are now 4-distinct-categories deep (CAD formula V26, BC fork V29, advisor mapping V31, turbulence-block-registry V52). The `codex_case_design_protocol.md` revision sub-DEC stays open and grows. **Cross-cutting**: hybrid-model administrative registration (LES vs RAS) is a different axis from runtime semantics (RAS-zone + LES-zone); Codex's reasoning from semantics → registration was the failure. **Counter row**: autonomous_governance: true; sub-session caught + fixed under round-cap=1 (no Codex re-iteration needed); 4th piece of evidence overdetermines a Codex protocol revision but does not trigger stop |

### V53 · Compressible PIMPLE `transonic yes` makes p-matrix asymmetric → `PCG`/`DIC` invalid; need `PBiCGStab`/`DILU` (V28 inverse)

| field | value |
|---|---|
| Surface | case_016 `system/fvSolution`: solver `p { solver PCG; preconditioner DIC; }`. rhoPimpleFoam fatal: `Unknown asymmetric matrix solver type PCG; Valid: GAMG PBiCG PBiCGStab smoothSolver`. Same as V28 in form (preconditioner unavailable) but **inverse in cause** — V28 was DILU on symmetric (invalid); V53 is DIC on asymmetric (invalid) |
| Engineer symptom | Compressible PIMPLE with `transonic yes` (required for M=0.85 to handle subsonic→sonic transitions in the cavity shear layer) makes the pressure-correction matrix non-symmetric. PCG (preconditioned conjugate gradient) is a Krylov method that REQUIRES symmetric positive-definite matrices. DIC preconditioner is the diagonal-incomplete-Cholesky decomposition — also symmetric-only. Both fail at first solver call with asymmetric matrix |
| Root cause | `rhoPimpleFoam` + `transonic yes` adds a velocity-divergence term to the p-equation that breaks symmetry. Standard ESI tutorials in `tutorials/compressible/rhoPimpleFoam/` use `PBiCGStab` + `DILU` for this reason; Codex brief did not specify the solver block (left to sub-session) and the case_006 V28 lesson read as "use DIC + PCG" without the symmetric-vs-asymmetric qualifier |
| Fix | (1) Replace with `p { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.01; }`. (2) **Cross-cutting**: the V28/V53 pair establishes a **matrix-symmetry-class** dimension for fvSolution selection: V28 = symmetric (compressible buoyant); V53 = asymmetric (compressible transonic). Same model family, different symmetry class — the V-series should index this. Add to `solver_convergence_playbook.md` as S12 candidate |
| Status | partial — case-local fix applied; cross-cutting symmetry-class dimension is a methodology gap that should be added to the playbook |
| Reference case | case_016_m219_cavity_des_acoustic (`scripts/02_scaffold_case.py::write_fvSolution` 2026-05-11) |
| Lesson | V28 + V53 together establish: **preconditioner selection is a matrix-symmetry-class decision, not a solver-class decision**. The same compressible solver (`rhoPimpleFoam`) flips symmetry-class based on `transonic` flag. Inheritance pattern: any future case with `transonic yes` inherits V53's solver block; any case with `transonic no` (subsonic incompressible-class) can keep V28's symmetric block. **Counter row**: autonomous_governance: true; sub-session caught + fixed under round-cap=1; further compounds the case-design protocol revision queue (V26+V29+V31+V52+V53) but does not trigger stop |

### V54 · Probe coordinates at literal CAD-surface values fall inside patch-tag helper solids, not in fluid mesh

| field | value |
|---|---|
| Surface | case_016 `system/controlDict` probes block: `Kulite_05 (0.2794, 0.0, -0.1020)` and `Kulite_09 (0.4826, 0.0, -0.1020)`. First-step probe output showed `# Probe 0 (...) # Not Found` and pressure values of `-1e+300` (uninitialized) — both probes fell outside the fluid mesh |
| Engineer symptom | Codex brief specifies probe coordinates at the literal cavity-floor z = -0.102 m. After sHM completed, region_air's cavity-floor patch face actually sat at z = -0.1015 m (the patch_tag helper solid for `cavity_floor` is 0.5 mm thick at z ∈ [-0.102, -0.1015]). A probe at z = -0.102 m therefore falls inside the patch-tag METADATA solid, which is below the fluid region, not on the fluid-cavity floor |
| Root cause | The CAD pattern from Codex brief deliverable §2 uses thin (0.5 mm) helper solids as patch tags for STEP-export naming convenience (`build_cad.py::build_patch_tags`). These helper solids exist in the STEP file and get extracted as per-patch STLs, but they are NOT meshed as part of region_air — sHM treats them as the boundary surface and stops fluid cells at their fluid-facing face (z = -0.1015 m, not z = -0.102 m). Probe coordinates must therefore be lifted by ≥ patch_tag_thickness mm above any nominal CAD surface |
| Fix | (1) **Case-local**: lifted both probes 1 mm above the cavity-floor face (z = -0.1005 m). Probes now bind correctly to fluid cells. (2) **Cross-cutting**: any CAD pattern that uses helper-solid-as-patch-name (a documented case_005/case_006-era convention) needs a probe-snap-margin equal to or larger than the helper thickness. Add to `case_kickoff_prompt_template.md` as: "probe coordinates must be offset from any nominal CAD surface by ≥ PATCH_TAG_THICKNESS_MM (default 0.5 mm); if the brief specifies floor-flush probes, lift them by 1 mm and note the deviation in the case profile" |
| Status | partial — case-local fix; cross-cutting kickoff-prompt amendment is a methodology gap |
| Reference case | case_016_m219_cavity_des_acoustic (`scripts/_lib.py::PROBE_KULITE_05_M` 2026-05-11) |
| Lesson | Patch-tag helper solids (a CAD pattern for STEP-export friendliness) introduce a **CAD-surface-vs-mesh-face offset** that is invisible at brief-writing time but lethal at probe-binding time. **Inheritance**: any case using helper-solid patch tags + probes on patch surfaces inherits V54; case_011/case_012/case_013/case_014/case_015 used helper tags but their probes were on internal-volume coords (no surface-flush bias), which is why this didn't surface earlier. **Counter row**: autonomous_governance: true; no Codex re-consult needed; sub-session ran post-V54-fix re-init within round-cap=1 |

### V55 · First D6 injection — `extra_body_in_fluid` advisor gap surfaced (no detector landed)

| field | value |
|---|---|
| Surface | case_016 D6: 10 mm debris cube at (320.0, 18.0, -79.0) mm inside cavity. `defect_manifest.yaml` `expected_advisor_to_catch: none_landed`; manual FreeCAD-class verification by `scripts/00_check_region.py` confirmed cube exists as separate solid with documented clearances (18 mm to floor, 28 mm to starboard wall, 183 mm to TE, 315 mm to LE) |
| Engineer symptom | No advisor in the harness detects "there is an extra body inside the fluid volume". A2 detects shared interfaces (case_004/005); thin_wall_advisor detects extreme-thinness; geometry_surgery decimates faces. None of these flag a fully-disjoint internal solid as a defect — sHM happily meshes around it as a no-slip wall, and the engineer sees no surfaced warning |
| Root cause | The advisor stack was designed around assembled-product defects (welds, gaps, sliver fillets, fuselage-frame thinness). A "loose part inside the assembly" is a different defect class — closer to FOD (foreign object debris) inspection than CAD-quality inspection. No advisor module covers this class |
| Fix | (1) **Case-local**: manual body-count + bbox + clearance check via `00_check_region.py::check_d6_debris` documents D6 explicitly; sub-session does NOT skip verification (Hard Guardrail #3). (2) **Advisor candidate (next iteration)**: `extra_body_in_fluid_advisor` — given parts manifest + CAD, list any solid that (a) is fully enclosed by region_air's bounding surfaces and (b) is not declared in the manifest as `bc_role: internal_wall`. Two-case validation required before promoting to confirmed. (3) **harvest 003 candidate** — flag for evaluation in next harvest cycle |
| Status | `[QUESTIONABLE 2026-05-11]` — claim "no advisor catches D6" is verified for advisor-set as of 2026-05-11; future advisor landing would supersede. Verification pending: extra_body_in_fluid_advisor lands AND ≥ 2 cases exercise it on D6-class defects |
| Reference case | case_016_m219_cavity_des_acoustic (`scripts/00_check_region.py::check_d6_debris` 2026-05-11; evidence/00_region_v1.json `D6` block) |
| Lesson | First **fluid-body-inventory** defect class surfaces an advisor-stack scope gap. **Counter row**: autonomous_governance: false (no automated detection means STOP gate inapplicable; manual verification was the gate per Guardrail #3) |

### V56 · First D9 injection — `curved_surface_tessellation_accuracy` advisor gap surfaced (no detector landed)

| field | value |
|---|---|
| Surface | case_016 D9: 8 mm baseline LE+TE lip fillet radii intentionally faceted with 16 straight segments per 90°. `00_check_region.py::check_d9_facets` confirmed: 16 facets, per-segment angle 5.625°, max chord deviation from smooth arc = 0.0096 mm |
| Engineer symptom | No advisor detects "this curved surface is approximated too coarsely for the tonal-noise application". thin_wall_advisor flags thinness; geometry_surgery decimates excess faces (helps OVER-tessellation); none flag UNDER-tessellation that an acoustic application would care about. For a 142 Hz Rossiter mode capture, the relevant scale is the LE/TE lip curvature radius — 16 facets/90° at 8 mm radius gives 0.78 mm arc-length steps, comparable to but coarser than the cavity-shear-layer cell size (sHM level-4 at 5 mm here, lift fillets only resolved by ~10 cells around the arc). Engineer would not know to flag this without the advisor |
| Root cause | The advisor stack treats curvature as a meshing-quality concern (sHM `resolveFeatureAngle` handles edge-snap), not as a physics-fidelity concern (acoustic-source representation). Cross-domain transfer gap |
| Fix | (1) **Case-local**: documented in evidence JSON; no fix needed for v1 since per-segment angle 5.625° at radius 8 mm is still well-resolved by the level-4 sHM cells. (2) **Advisor candidate (next iteration)**: `curved_surface_tessellation_accuracy_advisor` — given curved patches in the parts manifest + their tessellation parameters, flag if `max_chord_deviation_mm > target_resolution / 4` (acoustic-source-rep heuristic). Two-case validation required. (3) **harvest 003 candidate** |
| Status | `[QUESTIONABLE 2026-05-11]` — claim "no advisor catches D9" is verified for advisor-set as of 2026-05-11. Verification pending: curved_surface_tessellation_accuracy_advisor lands AND ≥ 2 curved-surface cases exercise it |
| Reference case | case_016_m219_cavity_des_acoustic (`scripts/00_check_region.py::check_d9_facets` 2026-05-11; evidence/00_region_v1.json `D9` block) |
| Lesson | Curvature-fidelity is the second advisor-stack scope gap surfaced in this case (paired with V55). Both are first-injections per Codex brief — neither has the ≥ 2-case-evidence threshold yet. Pattern: this case is the **advisor-stack-scope-audit case** — by design, it exercises two defects whose advisors don't exist. **Counter row**: autonomous_governance: false (same as V55) |

### V57 · First compound-DES root validated — transient-compressible-DES + FW-H sandbox runs end-to-end (case_016 anchor for numerics-class `compressible-DES-acoustic`)

| field | value |
|---|---|
| Surface | case_016 `~/Desktop/case_016_m219_cavity_des_acoustic/` proof-of-concept run: `build_cad` → `01_extract_surfaces` (STEP → 17 STLs, mm → m rescale) → `02_scaffold_case` (273 k-cell sHM after blockMesh + sHM + feature extraction) → `08_run_solver.sh STAGE=potential` (potentialFoam init, Phi solver added to fvSolution after first fatal) → `STAGE=solver END=0.0005` (rhoPimpleFoam transient compressible IDDES, 6 timesteps, dt=6.85e-5 s after CFL auto-adjust) → probes + forces FOs both writing data |
| Engineer symptom | Pipeline completed cleanly only after V52 (LES vs RAS block), V53 (PBiCGStab/DILU), V54 (probe offset), and minor scheme additions (`div(phiv,p)`, `div(phi,Ekp)`, `Phi`/`rho` solver entries) were applied. None of these are documented in case_006 V26-V32 or case_010 V45-V46 — they are **new** to the compressible-DES root. Mesh quality acceptable (max non-orthogonality 47°, max skewness 0.94, 8 concave faces from sHM corner artifacts — all non-fatal). FW-H FO loaded but no observer data accumulated (proof-of-concept window too short; HPC scope for full capture) |
| Root cause | Compressible-DES + acoustic-source-resolution is a fundamentally new numerics class — case_006 was steady-state (rhoCentralFoam shock-density); case_010 was incompressible-LES; case_016 is the **first** transient-compressible-DES. Inheritance from case_006 covered BC names (V29) and CAD-formula (V26), but not turbulence-block (V52), solver-symmetry (V53), or probe-offset (V54). Inheritance from case_010 covered transient infrastructure (V45) and sHM scaling (V46), but not compressible-specific scheme entries (`div(phid,p)` vs `div(phiv,p)`) |
| Fix | (1) **Sandbox is the anchor** — `~/Desktop/case_016_m219_cavity_des_acoustic/` is the reference end-to-end pipeline. Future compressible-DES cases (M219 deep cavity variant; supersonic cavity; lip-blowing AIP) inherit this scaffold. (2) **Production capture scope**: full 0.75 s Rossiter convergence window requires HPC (estimated ≥ days at 273k cells; production cell counts ~10-50M would be week-scale); out-of-session per Codex brief deliverable boundaries |
| Status | partial — proof-of-concept validates pipeline; production Rossiter capture pending HPC run. Confirmed across 1 case (case_016 itself); status promotes to `confirmed` after a second compressible-DES case runs |
| Reference case | case_016_m219_cavity_des_acoustic (full sandbox; `evidence/{00..11}_*.json`; `case/log/{blockMesh,surfaceFeatureExtract,snappyHexMesh,checkMesh,potentialFoam,solver_rhoPimpleFoam}.txt`) |
| Lesson | **First compound-DES root** is now anchored. Inheritance index entries: numerics_class = `compressible-DES-acoustic`. Inherits-from: V26+V27(rhoCentralFoam-specific, N/A here)+V28+V29+V30(N/A)+V31+V32 (case_006 compressible-shock-density) + V45+V46 (case_010 incompressible-LES). Receives: V52+V53+V54+V55+V56 (case_016 specific). **S-series candidates** (next playbook update): S15 "tonal noise weak → check cavity LE refinement ≥5 cells across shear layer"; S16 "FW-H spectrum noisy → move porous surface inside resolved turbulence region"; S17 "low Rossiter mode missing → extend time window to 0.75 s for 100-cycle FFT"; S18 "acoustic reflection contamination → verify waveTransmissive coefficient + far-field box ≥ 30L". All S15-S18 are candidates pending v2 HPC run evidence — none promoted to playbook yet. **Counter row**: autonomous_governance: true; sub-session round-cap=1 captured pipeline successfully |

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

### Pattern 6 — V-findings inherit across solver families when fluid-internal numerics are shared (added V15 · 2026-05-07)

V15 demonstrates that V5, V6, V7 (originally surfaced under
buoyantSimpleFoam) reappear unchanged in chtMultiRegionSimpleFoam,
because both solvers wrap the same compressible-buoyant-RANS
fluid-side numerics. Going forward:

- Index V-findings by **fluid-internal numerics class**
  (compressible-buoyant-RANS, incompressible-RANS, compressible-
  shock-density-based, multiphase-VOF, etc.), not by solver name
- A new industrial case in solver class X should pre-emptively
  inherit all V-findings whose `numerics_class` matches X's
  fluid-side numerics
- Genuinely new V-findings emerge only from surfaces that **did
  not exist** in the parent class — e.g. multi-region pairing,
  cellZone definition, periodic boundaries — not from fluid
  internals

The corpus loader (M6 prerequisite) should expose this inheritance
explicitly so AI Diagnose can suggest "your case is class
compressible-buoyant-RANS, here are the 6 V-findings that apply
even though you're using a different solver family".

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
