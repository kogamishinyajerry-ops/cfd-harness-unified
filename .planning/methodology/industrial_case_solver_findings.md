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
| Reference cases | APU bay `apu_intake` (body_2 ↔ body_4, curved CATIA non-manifold); case_003 root_mount_pad ↔ root_mount_cover (planar CadQuery boxes, Z-axis gap) |
| Lesson | Industrial CAD exports are noisy. Geometric heuristics are more robust than topological equality on real-world data. V2 lesson explicitly preserved in advisor docstring: do NOT add `isSame()` fast-path (reintroduces the bug). **Cross-topology validity confirmed 2026-05-08**: same advisor handles curved CATIA exports (case_002a) and planar CadQuery boxes with axial gap (case_003). The `_run_shared` algorithm's normal-direction-only matching is the right primitive — bbox overlap volume is a no-op on zero-volume planar face bboxes |

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
| Status | **closed · field-validated** (advisor landed; cross-topology consistency confirmed) — pre-meshing path warns; case-local accept remains legitimate once warned. case_003 sub-session 2026-05-08 first cross-topology validation: planar CadQuery `thin_access_plate` (0.80 mm thinnest dim, 27 m × 3.4 m × 0.80 mm) flagged `severity=critical` with `cells_per_thickness=0.013`, `recommended_level_max=13`. Both curved CATIA frame (case_002a APU body) and planar plate (case_003 D8) trigger correctly — bbox-min thinness estimator generalizes |
| Reference cases | case_002a V10 (original, curved Frame patches); case_002b CHT v1 (inherited unchanged → triggered advisor extraction); case_003 D8 (first planar-plate validation 2026-05-08) |
| Lesson | Refinement-level selection on thin walls is a pre-meshing decision that cannot be recovered post-meshing without re-running sHM. **Pillar 2 example**: a finding that recurred across two case threads on the same physical geometry is a signal to land a main-project advisor, not just to document. Advisor uses bbox-min heuristic (exact for axis-aligned plate/beam; lower-bound for curved shells) — case_003 confirmed both regimes flag correctly |

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
| Status | **open** — A2 first industrial falsification surfaces the gap. Compounded with V17 (A3 scope gap) → main-project sub-DEC under DEC-V61-198 recommended for "advisor-scope-expansion" arc covering both A2 (D1 pattern) and A3 (D2 redundancy pattern) |
| Reference case | case_005_rae_m2129_sduct A2 falsification (2026-05-08, evidence/v1_a2_falsification.json) |
| Lesson | When the kickoff prompt described A2 as "pending" but the codebase shows A2 has been landed, **always verify the codebase before acting on the kickoff narrative**. The kickoff text was stale — A2 is landed for the V2 pattern. case_005 then surfaces the *next* gap in A2's scope: D1's gap-as-defect signature is a different scope axis from V2's shared-interface signature. Two industrial falsifications in one case-thread (A2 + A3), both PARTIAL, both surfacing scope-narrowness bias in different ways. Per Pattern 5, this is a legitimate industrial case outcome — toy-case bias hides in advisor *scope* even after parameter-value bias is fixed |

### V18 · Compressible-RANS pseudo-steady mass imbalance under SIMPLE + totalPressure inlet + coarse mesh

| field | value |
|---|---|
| Surface | rhoSimpleFoam compressible SIMPLE algorithm; totalPressure inlet ↔ fixedValue/waveTransmissive outlet coupling; coarse-mesh BC settling |
| Engineer symptom | Solver runs 0-500 iter without crashing. Tmin/Tmax bounded (255/389 K), no NaN, no SIGFPE, no V3-V7 patterns. **But**: residuals oscillate (Ux initial residual ~0.1-0.3 throughout, p ~0.005 throughout, no monotonic decrease). Cumulative continuity error grows (130,957 by iter 500). `surfaceFieldValue` reports phi_inlet = -1.51 kg/s, phi_outlet = +4.36 kg/s — **3× asymmetric mass flow**. Engineering metrics also off (AIP Mach 0.18 vs 0.40-0.60 target; PR=0.955 vs 0.839 nominal; DC60=0.351 vs ~0.10-0.20 typical) |
| Root cause | SIMPLE algorithm with totalPressure inlet + fixedValue p outlet, started from non-zero but rough initial U (case_005: 100 m/s axial), struggles to establish the inlet→outlet pressure ratio in a single relaxation pass per iteration. Compressible momentum equation lags the pressure update (URF p=0.20, U=0.50, e=0.20), and the coarse mesh (52k cells, no prism layers, 1,688 concave cells in the S-curve transition) does not have enough resolution to enforce wall-bounded boundary layer. Mass conservation does not lock in within 500 iter — the BC chain is in transient balance, not steady. Pattern 6: this is **compressible-RANS specific** (case_005 numerics-class root); not inherited from V13 (compressible-buoyant-RANS pseudo-steady) because the mechanism is different — V13's loop is p ↔ ρ ↔ U ↔ T (buoyancy-driven feedback), V18's loop is just p ↔ ρ ↔ U with the totalPressure-inlet enforcement struggling against the resistance of the unconverged interior |
| Fix | See playbook S13. Three options: (1) `potentialFoam -writePhi -initialiseUBCs` warm start (cheap); (2) lower URF further (p=0.10, U=0.30) + longer iter budget (2000-5000); (3) switch to rhoPimpleFoam transient (Codex's v2 fallback). For all three: refine mesh + add prism layers to give the BCs a properly-resolved interior to settle against. v1 case_005 chose path (2) only partially (URF already at 0.20, iter budget capped at 500) — V13-pattern v1 simplification, accept and document |
| Status | **playbook** (S13) |
| Reference case | case_005_rae_m2129_sduct v1 (2026-05-08) |
| Lesson | Compressible-RANS pseudo-steady oscillation has the same coarse symptom as compressible-buoyant-RANS V13 (residuals oscillate, continuity error doesn't reach zero) but a different mechanism (BC-chain transient instead of buoyancy-coupled feedback). The S-family decision tree should NOT collapse "compressible pseudo-steady" into one entry; document the distinct entry point per numerics class. v1 simplification (Pattern 5) is legitimate — case_005 v1 baseline is the case_002a v13 analogue for compressible-RANS root |

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
| Status | **open** — main-session cross-case investigation needed (compounded evidence: case_003 sub-session validates A2 on Z-axis gap; case_005 V19 documents A2 fails on X-axis gap; mechanism difference unclear) |
| Reference cases | case_003 (PASS, planar-box Z-axis gap, 2026-05-08); case_005 (FAIL per V19, flange-ring X-axis gap, 2026-05-08) |
| Lesson | When two industrial cases produce contradictory advisor outcomes on structurally similar defects, **the advisor's actual code path matters more than its conceptual scope**. V19's diagnosis of "bbox-overlap fails on thin-extent bboxes" applies to `faces_match_shared` but NOT to `_run_shared` (the public API surface). Sub-sessions should specify in their V-finding which entry-point was invoked. Main session should add to advisor docs: "for D1-class sub-mm-gap detection, prefer `_run_shared` over `faces_match_shared` — the latter has the bbox-volume-zero edge case on planar geometry" |

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
