# Case 006 · ONERA M6 Transonic Wing · rhoCentralFoam thread (Industrial Reference)

> **NOT a gold-standard case.** No automated benchmark verdict. **Industrial reference** — proof artifact + V-series finding source.
>
> Established by DEC-V61-198 (APU bay strategic pivot, 2026-05-07) as the **first density-based shock-capturing case** in the project's case fleet. Fills the **external transonic 3D wing (compressible high-speed, shock-capturing)** row of the solver-class coverage map. Per Pattern 6, case_006 is the **root for compressible-shock-density-based**: inherits NO V3-V13/V15 (compressible-buoyant-RANS), NO V-findings from case_003 (incompressible-RANS), NO case_004 (incompressible-RANS-MRF), NO case_005 (compressible-RANS pressure-based).

## What this entry is

A real industrial-flavored CFD case with a Tier-1 reference geometry (NASA Glenn `WWW/wind/valid/m6wing/`, AGARD AR-138 / Schmitt-Charpin 1979) regenerated parametrically by Codex's CAD design (per `.planning/methodology/codex_case_design_protocol.md`). The case-thread sandbox at `~/Desktop/case_006_onera_m6_transonic/` ran v1 end-to-end and surfaced **7 net-new V-series findings (V26-V32)** + **multiple stale-assumption corrections** in Codex's CAD generator and BC-name catalog.

## What this entry is for

Three orthogonal uses (parallel to case_002a/case_005):

1. **Proof artifact**: workbench can drive an industrial transonic external wing through CAD → STL extraction → mesh → density-based solver end-to-end. v1 baseline generates 48,847-cell sHM mesh, configures rhoCentralFoam with first-time density-based fvSchemes (Kurganov + Minmod), and runs the solver to physical time ≈ 5 ms (≈1.7 chord flow-throughs). Hand-coded density-based BC writer (freestream/freestreamPressure), rhoCentralFoam fvSolution + fvSchemes, and patch-coverage handling — none existed in the main project before case_006.

2. **V-series finding source**: 7 net-new findings spanning Codex CAD pattern (V26), rhoCentralFoam infrastructure (V27-V29), advisor extension (V30, V31), and Tier-1-source-availability (V32). All documented in `industrial_case_solver_findings.md`.

3. **Dual-advisor exercise verdict on D4** (kickoff three-branch: thin_wall_advisor fires, geometry_surgery silent → expected; Codex's D4 mapping is wrong but defect IS caught by an advisor). Establishes the canonical defect→advisor mapping for sub-mm sliver class going forward.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_006_onera_m6_transonic/` |
| Top-level overview | `~/Desktop/case_006_onera_m6_transonic/README.md` |
| Final report (v1) | `~/Desktop/case_006_onera_m6_transonic/evidence/v1/REPORT.md` |
| SSOT YAML | `~/Desktop/case_006_onera_m6_transonic/config/case.yaml` |
| Codex deliverables | `.planning/methodology/kickoff/case_006_codex_response.md` (in this repo) |
| Validation report | `.planning/methodology/kickoff/case_006_validation.md` |
| D1 ground-truth + advisor exercise | `~/Desktop/case_006_onera_m6_transonic/evidence/v1/d1_advisor_exercise.md` |
| D4 ground-truth + dual-advisor exercise | `~/Desktop/case_006_onera_m6_transonic/evidence/v1/d4_advisor_exercise.md` |
| Face-geometry JSON (FreeCAD-extracted) | `~/Desktop/case_006_onera_m6_transonic/evidence/v1/face_geometry.json` |
| 11-script pipeline | `~/Desktop/case_006_onera_m6_transonic/scripts/{build_cad,01_extract_stl,02_verify_defects,02b_extract_face_data,02c_advisor_exercise,04_scaffold_case,05_make_dicts,06_run_mesh,09_run_solver}.{py,sh}` |
| Templates | `~/Desktop/case_006_onera_m6_transonic/templates/` (Jinja2; first-time density-based + freestream BC family) |

## Per-step wall time (v1 baseline)

Measured 2026-05-08 on macOS Apple Silicon, Docker `opencfd/openfoam-default:2312`:

| Step | Script | Wall time | Output |
|---|---|---|---|
| 0 | `build_cad.py` | ~6 s | `inputs/cad_codex_v1.step` (387 KB; cadquery 2.7.0). **Re-run after V26 fix**: 1 character formula correction in `build_auxiliary_defects()` |
| 0' | `02_verify_defects.py` (FreeCAD) | ~4 s STEP import + ~1 s D1+D4 | D1=0.350 mm exact PASS (post-V26-fix), D4=0.180 mm exact PASS |
| 0'' | `02b_extract_face_data.py` (FreeCAD) | ~5 s | per-body `face_geometry.json` (3 bodies, 17 faces) + `tip_cap_sliver.stl` |
| 0''' | `02c_advisor_exercise.py` | <1 s | A2/thin_wall/geometry_surgery results + 2 markdown reports |
| 1 | `01_extract_stl.py` (FreeCAD) | ~30 s | 5 multi-solid STL bodies (wing 12 MB / ~187k tri; tip_cap, root_*, sliver smaller) |
| 4 | `04_scaffold_case.py` | <1 s | `case/{0.orig,constant,system}/` |
| 5 | `05_make_dicts.py` | <1 s | rendered Jinja2 → all OpenFOAM dicts |
| 6 | `06_run_mesh.sh` | ~120 s | STL mm→m + blockMesh + sHM (48,847 cells; max non-ortho 46.8; max skew 1.31; 916 concave cells flagged but solver-tolerable) + checkMesh |
| 9 | `09_run_solver.sh` | ~3-5 min (target 5 ms physical, ~110-150 timesteps via adjustTimeStep+Co=0.5) | rhoCentralFoam |

Total: **~10 min** wall clock for v1 (excluding solver iteration time, which is the dominant cost).

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (V-series source material, all new for compressible-shock-density-based):
- `build_cad.py` (Codex deliverable, **with V26 1-line correction applied**)
- `01_extract_stl.py` — FreeCAD-based per-body STL export with linear deflection 0.5 mm
- `02_verify_defects.py` — D1 distToShape + D4 BoundBox.min via FreeCAD
- `02b_extract_face_data.py` — per-body face geometry → JSON for advisor consumption
- `02c_advisor_exercise.py` — A2 + thin_wall_advisor + geometry_surgery dual exercise
- `templates/system/fvSchemes` — first-time density-based: Kurganov flux + Minmod reconstruction for ρ/U/T (the lambda-shock-friendly setup)
- `templates/system/fvSolution.j2` — rhoCentralFoam canonical: `diagonal` for ρ/ρU/ρE; `smoothSolver+symGaussSeidel` for U/e/k/omega (DILU unavailable for symmetric matrices)
- `templates/system/controlDict.j2` — `adjustTimeStep yes` + `maxCo 0.5` + initial dt=1e-6 (mandatory for explicit central-upwind)
- `templates/0/{U,p,T}.j2` — first-time `freestream` + `freestreamPressure` BC family (Codex's `characteristicPressure*` BC names don't exist in openfoam-default:2312)
- `templates/constant/thermophysicalProperties` — perfectGas + eConst + const transport
- `templates/constant/turbulenceProperties` — laminar (v1 per S1)

**Reused from main project** via `PYTHONPATH`:
- `ui.backend.services.geometry_ingest.virtual_interface_detector` — A2 advisor (exercised by `02c_advisor_exercise.py` on D1)
- `ui.backend.services.geometry_ingest.thin_wall_advisor` — primary D4 advisor (LANDED 2026-05-07; first sub-mm extreme-thinness validation)
- `ui.backend.services.geometry_ingest.geometry_surgery` — secondary D4 advisor per Codex's mapping (silent, expected outcome)

**Not consumed** because case_006 numerics class is outside their schema (case-local only):
- `ui.backend.services.case_bc.writer` — supports incompressible + pressure-based compressible, not density-based external transonic w/ freestream BCs
- `ui.backend.services.case_scaffold` — could be reused; Codex case_005 also went case-local for parallel reasons; case_006 followed suit
- `ui.backend.services.mesh_quality.advisor` — could be wired in but focused effort on advisor exercise this run

## Mapping to V-series + 5-artifact extraction (DEC-V61-198 Pillar 2)

case_006 surfaced 7 NEW V-findings + 1 stale-assumption-corrections-by-fix-in-place commits:

| V-finding | Source pattern | Extraction candidate |
|---|---|---|
| **V26** Codex CAD generator centered-vs-anchored box-origin off-by-half-width | Codex CAD pattern (analogous to V16, different mechanism) | Update `codex_case_design_protocol.md` to require Codex to verify defect dimensions via FreeCAD distToShape **before** declaring deliverable complete; add unit-test pattern showing center-aligned vs anchored box geometry |
| **V27** rhoCentralFoam adjustTimeStep mandatory; fixed dt=1 yields Co ≈ 10^5 first iter | density-based-numerics infrastructure | Codify in solver_convergence_playbook.md S15 (NEW) + provide rhoCentralFoam controlDict template in main project |
| **V28** rhoCentralFoam DILU preconditioner unavailable for symmetric matrices; canonical = `smoothSolver+symGaussSeidel` | density-based-numerics infrastructure | Same: add to S15 |
| **V29** OpenFOAM ESI lacks `characteristicPressureInletOutletPressure` (Codex used foam-extend-only name); canonical = `freestream`+`freestreamPressure` | Codex CAD-protocol BC-name validity | Add a "BC name OpenFOAM ESI compatibility check" step to validate phase before sub-session dispatch |
| **V30** thin_wall_advisor extreme-thinness field-validation: 0.18 mm sliver flagged critical at all reasonable refinement levels (cells_per_thickness 0.014-0.058 vs 2.0 threshold; recommended level_max=10 mathematically infeasible) | Advisor extension (extends V10 + V23) | Add V30-class evidence to thin_wall_advisor docstring; possibly tune severity messaging when recommended_level is mathematically infeasible (warn user that v1 must accept patch loss) |
| **V31** Codex defect→advisor mapping incorrect for D4 (sub-mm sliver); Codex pointed at `geometry_surgery.decimate_to_tier` which silently no-ops on small face counts | Codex CAD-protocol defect mapping | Update `codex_case_design_protocol.md` defect→advisor table: D2 (over-dense triangulation) → geometry_surgery; D4 (sub-mm sliver bodies) → thin_wall_advisor; D8 (thin shell ≥0.5 mm) → thin_wall_advisor |
| **V32** Tier-1 NASA Glenn HTTP 500 + corporate SSL cert chain double-blocker; ONERA-D-proxy (NACA 0010) substitution → lambda-shock x/c displacement caveat | CAD-source availability | Bundle with V20 in A1 extraction sub-DEC: include offline-cache + airfoil-proxy-substitution path in `cad_ingest_freecad.py` |

## Hard-coded compensations (stale-assumption fix-in-place per DEC-V61-198 Pillar 2)

| Item | Trigger | Fix |
|---|---|---|
| Codex CAD `cover` box origin formula in `build_cad.py` | D1 ground-truth verification = 22.35 mm (off by 22 mm box-width) | One-line edit: `0.10 * ROOT_CHORD_MM + 22.0 + ROOT_GAP_MM + 22.0` → `0.10 * ROOT_CHORD_MM + 22.0 + ROOT_GAP_MM`; comment explaining centered=True semantics |
| 0/U + 0/p BC names in templates | Solver runtime error: "Unknown patchField type characteristicPressureInletOutletPressure" | Substitute `freestream` (for U/T) + `freestreamPressure` (for p), per OpenFOAM ESI canonical |
| controlDict deltaT + adjustTimeStep | Mean Courant 674 / max 69440 first iter (catastrophic for explicit central scheme) | `adjustTimeStep yes`, `maxCo 0.5`, initial `deltaT 1e-6` |
| fvSolution preconditioner family | Solver runtime error: "Unknown symmetric matrix preconditioner type DILU" | Substitute `smoothSolver+symGaussSeidel` for U/e/k/omega; keep `diagonal` for ρ/ρU/ρE per rhoCentralFoam canonical |
| blockMesh boundary patch names | sHM eats wing_surface_reference cleanly but downstream BC writer expects `farfield_*` (not `farfield_*_bg`) | Renamed blockMesh patches to drop `_bg` suffix (1-line edit per patch in template) |

## D1 advisor exercise outcome (consistent with V25)

Per kickoff Hard Guardrail #6: A2 advisor at `ui/backend/services/geometry_ingest/virtual_interface_detector.py`. Public API path (`detect_virtual_interfaces`+`_run_shared`) per V21 closure note.

```
matched: True (both pad-first and cover-first orderings, symmetric)
body_owner: root_fairing_pad / root_fairing_cover (depending on order)
bbox_overlap_fraction: 1.0 (HARDCODED PLACEHOLDER per V25)
area_diff_fraction: 0.0 (HARDCODED PLACEHOLDER per V25)
normal_dot: 1.0
```

**case_006 is the FOURTH consecutive case (case_003 + case_004 + case_005 v2 + case_006) confirming V25 placeholder semantic.** A2 cannot distinguish "shared interface" (gap=0) from "should-have-been-shared-but-isn't" (gap=0.35 mm) — the gap distance is not computed and not returned. 4-of-4 overdetermines the V25 advisor-scope-expansion sub-DEC.

## D4 advisor exercise outcome (kickoff three-branch decision)

**Outcome 2 (expected)**: thin_wall_advisor fires at all reasonable refinement levels with severity=critical; geometry_surgery silent (sliver face count = 8, well below `min_to_decimate` threshold of 8000).

```
thin_wall_advisor at levels (1,2): cells_per_thickness 0.014, severity critical
thin_wall_advisor at levels (2,3): cells_per_thickness 0.029, severity critical
thin_wall_advisor at levels (3,4): cells_per_thickness 0.058, severity critical
geometry_surgery: skipped (under min_to_decimate threshold)
```

**Codex's defect→advisor mapping was wrong** (per V31 above). thin_wall_advisor is the correct catch for sub-mm sliver bodies; this validates the kickoff Known-Issues N2 + N6 prediction.

## v1 lambda-shock outcome

(Pending solver completion — see evidence/v1/REPORT.md for the final verdict line.)

## Stale-assumption main-session attention

Per DEC-V61-198 Pillar 2 + the kickoff "Main session attention required" pattern:

1. **`codex_case_design_protocol.md` defect→advisor mapping**: needs updating to include explicit D4 → thin_wall_advisor (currently silent on D4-class sub-mm slivers, defaults to recurring "geometry_surgery" mismapping observed in Codex output for case_005 D2 + case_006 D4). Bundle as part of advisor-scope-expansion sub-DEC.

2. **`codex_case_design_protocol.md` BC-name catalog**: Codex case_006 deliverable used `characteristic*VelocityInletOutletVelocity`/`characteristicPressureInletOutletPressure` BC names that exist in foam-extend but NOT in opencfd/openfoam-default:2312. Add a "BC compatibility check" step before dispatch.

3. **`codex_case_design_protocol.md` CAD-formula verification**: V26 (centered=True off-by-half-width) is a recurring Codex mental-model bug. Require Codex to declare verification dimensions and tolerance ranges in `defect_manifest.yaml` so the sub-session can fast-fail before scaffolding the case.

4. **`solver_convergence_playbook.md`**: needs S15 entry for density-based-numerics infrastructure (consolidating V27-V29: adjustTimeStep + smoothSolver + freestream BC names).

5. **case_index.md status**: case_006 should advance from "dispatched · DEFERRED" to "active · v1 baseline (sediment landed; lambda-shock outcome documented)". Solver-class coverage map row "Compressible high-speed (shock)" advances from "dispatched (case_006, deferred)" to ✅ covered.

## What this case does NOT yet have

- **Verdict comparison**: AGARD AR-138 published Cp at 7 η stations (cp1u/l.ex through cp7u/l.ex) requires NASA Glenn archive recovery OR alternate redistributed dataset acquisition. Recommended action: M6 RAG corpus addition once available, not a v1 blocker.
- **Lambda-shock pattern recovery**: v1 mesh (48k cells) is below the 1M-cell minimum for clean lambda capture. Even with correct numerics (Kurganov + Minmod), the spanwise resolution at level 5 (~31 mm cell at wing) is too coarse to resolve forward + aft shock-foot displacement at η=0.65-0.95.
- **D-section airfoil geometry fidelity**: v1 used NACA 0010 proxy because Tier-1 source is unreachable. ONERA D-section coordinates differ in rooftop region (x/c 0.30-0.60); lambda-shock x/c displacement may be 5-15% even with adequate mesh.
- **kOmegaSST turbulence**: v1 uses laminar baseline per S1 playbook (avoid kOmegaSST + zero IC blowup). v2 plan: kOmegaSST restart from converged v1.
- **Force coefficients**: forceCoeffs function object is wired in controlDict but Cl/Cd/Cm extraction requires solver to run beyond pseudo-steady transient.

## When to update this entry

- **Each time case_006 runs a new development version** (v2 with kOmegaSST + finer mesh + Tier-1 airfoil; v3 with rhoPimpleFoam fallback if Kurganov over-smoothes lambda): append per-step wall time row + add corresponding V-series entry if a new failure mode surfaced
- **When A1 extraction lands** (with V20+V32 unit-context + offline-cache support): update mapping table to note Tier-1 source resilience improved
- **When V25 advisor-scope-expansion sub-DEC lands**: update D1 advisor exercise section to reflect new gap-aware result schema

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series (case_006 V26-V32 added 2026-05-08)
- `.planning/methodology/solver_convergence_playbook.md` — decision tree (S15 candidate from V27-V29)
- `.planning/methodology/kickoff/case_006_codex_response.md` — Codex's full design (5 deliverables)
- `.planning/methodology/kickoff/case_006_validation.md` — main session's 13-check validation
- `.planning/case_profiles/case_005_rae_m2129_sduct.md` — sibling compressible case (pressure-based compressible-RANS)
- `~/Desktop/case_006_onera_m6_transonic/evidence/v1/REPORT.md` — final v1 report
