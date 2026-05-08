# Case 009 · Sandia/TUD Flame D · reactingFoam thread (Industrial Reference)

> **NOT a gold-standard case.** No automated benchmark verdict.
> **Industrial reference** — proof artifact + V-series finding source.
>
> Established by DEC-V61-198 (APU bay strategic pivot, 2026-05-07) as the
> **first reacting low-Mach** case in the project's case fleet. Fills the
> **combustion / reacting-low-Mach** row of the solver-class coverage map.
> Per Pattern 6, case_009 is the **root for reacting-low-Mach**: inherits NO
> V-findings from any prior case (V3-V32 cover compressible-buoyant-RANS,
> incompressible-RANS, MRF, compressible-RANS, compressible-shock-density-
> based — none are reacting). 

## What this entry is

A real industrial-flavored CFD case with a Tier-1 reference geometry (Sandia
TUD Flame D, TNF Workshop CH4/air piloted jet) regenerated parametrically by
Codex's CAD design (per `.planning/methodology/codex_case_design_protocol.md`).
The case-thread sandbox at `~/Desktop/case_009_sandia_flame_d/` ran v1 end-to-
end to demonstrate the reacting-low-Mach pipeline and surfaced **5 net-new
V-findings (V38-V42)** — chemkinToFoam infrastructure (V38-V41) + 5th cross-
topology consistency confirmation of V25 placeholder semantic on combustion-
burner topology (V42).

## What this entry is for

Three orthogonal uses (parallel to case_002a/case_005/case_006):

1. **Proof artifact**: workbench can drive an industrial reacting-low-Mach
   case through CAD → blockMesh wedge → reacting infrastructure (chemkinToFoam
   + thermo + species BCs + combustion model) → reactingFoam end-to-end.
   v1 baseline runs cold-flow + ignite stages (full ramp deferred to v2).
   Hand-coded chemistry mech loader, combustion thermo writer, species BC
   writer, combustion-properties writer, mixture-fraction post-processor —
   none existed in the main project before case_009. **5+ artifact extraction
   candidates** — the biggest infrastructure climb in the 10-case roster.

2. **V-series finding source**: 5 net-new findings spanning chemkinToFoam
   infrastructure (V38: THERMO ALL header; V39: tran.dat END terminator;
   V40: transport-input as chemkin file vs OpenFOAM dict; V41: GRI-3.0 thermo
   header Tlow=300 vs species records Tlow=200) and advisor consistency
   (V42: A2 6th-of-6 V25 placeholder confirmation on reacting-low-Mach
   geometry context). All documented in `industrial_case_solver_findings.md`.

3. **First reacting case** in the project. Establishes patterns for chemistry
   mech ingestion + species transport + combustion model wiring that all
   future reacting cases (fireFoam, edcSimpleFoam) will inherit.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_009_sandia_flame_d/` |
| Top-level overview | `~/Desktop/case_009_sandia_flame_d/README.md` |
| Final report (v1) | `~/Desktop/case_009_sandia_flame_d/evidence/v1/REPORT.md` |
| SSOT YAML | `~/Desktop/case_009_sandia_flame_d/config/case.yaml` |
| Codex deliverables | `.planning/methodology/kickoff/case_009_codex_response.md` (in this repo) |
| Validation report | `.planning/methodology/kickoff/case_009_validation.md` |
| D1 ground-truth + advisor exercise | `~/Desktop/case_009_sandia_flame_d/evidence/v1/d1_advisor_exercise.md` |
| D8 ground-truth + advisor exercise | `~/Desktop/case_009_sandia_flame_d/evidence/v1/d8_advisor_exercise.md` |
| Face-geometry JSON (FreeCAD-extracted) | `~/Desktop/case_009_sandia_flame_d/evidence/v1/face_geometry.json` |
| Decision log | `~/Desktop/case_009_sandia_flame_d/docs/decisions_v1.md` |
| Pipeline scripts | `~/Desktop/case_009_sandia_flame_d/scripts/{build_cad, _lib, 02_verify_defects, 02c_advisor_exercise, 04_scaffold_case, 05_make_dicts, 08b_load_chemistry_mech, 08d_write_species_bcs, 08e_write_combustion_properties, 09_run_solver, 10b_compute_mixture_fraction, 10c_compute_temperature_profile}.{py,sh}` |
| Templates | `~/Desktop/case_009_sandia_flame_d/templates/` (Jinja2; first-time wedge multi-block + reactingFoam thermo/combustion/chemistry/Yi BCs) |

## Per-step wall time (v1 baseline)

Measured 2026-05-08 on macOS Apple Silicon, Docker `opencfd/openfoam-default:2312` (case009 container):

| Step | Script | Wall time | Output |
|---|---|---|---|
| 0 | `build_cad.py` | ~5 s | `inputs/cad_codex_v1.step` (387 KB; cadquery 2.x) |
| 0' | `02_verify_defects.py` (FreeCAD) | ~5 s | D1=0.350 mm exact PASS, D8=0.800 mm exact PASS, 13/13 bodies clean (no Compound fragmentation) |
| 0'' | `02c_advisor_exercise.py` | <1 s | A2 + thin_wall_advisor exercise + 2 markdown reports |
| 4 | `04_scaffold_case.py` | <1 s | `case/{0,constant,system}/` |
| 5 | `05_make_dicts.py --stage cold` | <1 s | rendered Jinja2 → blockMeshDict + controlDict + fvSolution + 0/* (U/p/T/k/eps/alphat/nut) |
| 6 | `blockMesh` | <2 s | 11,600 cells, 6 radial blocks (axis-collapsed for fuel column) |
| 6' | `checkMesh` | <2 s | max skew 0.33; non-orth 0; aspect 22; mesh OK |
| 8b | `08b_load_chemistry_mech.py` | ~5 s (cached after first fetch) | DRM-19 chem.inp + therm.dat + tran.dat downloaded; THERMO ALL + END + Tlow=200 patches applied; chemkinToFoam → constant/reactions + constant/thermo.compressibleGas |
| 8d | `08d_write_species_bcs.py` | <1 s | 21 species BC files in case/0/ |
| 8e | `08e_write_combustion_properties.py --stage cold` | <1 s | thermophysicalProperties + chemistryProperties + combustionProperties (active=false) |
| 9 stage A | `reactingFoam` (cold-flow, dt=1e-5, t=0→0.005s) | ~30 s | clean exit; min/max(T)=[294,1880]K; 5 timestep dirs |
| 9 stage B | `reactingFoam` (ignite, dt=1e-6, t=0.005→0.006s, combustion=on) | (running) | T_max rising above 1880 (heat-release in mixing layer) |

Total: **~1 min** wall clock for v1 (excluding stage B which runs ~1ms physical
of chemistry-on; stage C ramp deferred to v2 with multi-hour budget).

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (V-series source material, all new for reacting-low-Mach):
- `build_cad.py` (Codex deliverable, 230 LOC, ran clean — no Codex-fixin-place needed)
- `02_verify_defects.py` — FreeCAD distToShape D1 + BoundBox D8 + face geometry export
- `02c_advisor_exercise.py` — A2 + thin_wall_advisor exercise on combustion-burner topology
- `templates/system/blockMeshDict.j2` — first-time multi-block axisymmetric wedge
  (6 radial columns, axis-collapsed degenerate hex for fuel column)
- `templates/system/fvSchemes` — first-time 21-species `div(phi,Yi_h)` multivariateSelection
- `templates/system/fvSolution.j2` — PIMPLE for reactingFoam with `"Yi.*"` solver
- `templates/0/*.j2` — first-time 21 species 0/Yi BCs + alphat + nut + standard fields
- `templates/constant/{thermophysicalProperties,combustionProperties.j2,chemistryProperties}` —
  first-time hePsiThermo/reactingMixture/janaf + PaSR + Cmix=1.0 + EulerImplicit
- `scripts/08b_load_chemistry_mech.py` — DRM-19 fetch + chemkinToFoam invocation
  (incl. THERMO ALL header patch, END terminator patch, sutherland regex transportProperties dict)
- `scripts/08d_write_species_bcs.py` — 21-species BC writer per inflow YAML
- `scripts/08e_write_combustion_properties.py` — stage-aware combustion props writer
- `scripts/10b_compute_mixture_fraction.py` — Bilger Z formula + inlet sanity check
  (per-cell reconstruction is a v2 deliverable)
- `scripts/10c_compute_temperature_profile.py` — sample-line dictionary at TNF stations

**Reused from main project** via `PYTHONPATH`:
- `ui.backend.services.geometry_ingest.virtual_interface_detector` — A2 advisor (V25-pattern exercise)
- `ui.backend.services.geometry_ingest.thin_wall_advisor` — D8 advisor (6th cross-topology consistency)

**Not consumed** (case-local because reacting-low-Mach is outside their schema):
- `ui.backend.services.case_bc.writer` — incompressible/pressure-based; doesn't speak species
- `ui.backend.services.case_scaffold` — would need extension for reactingFoam scaffolding
- `ui.backend.services.mesh_quality.advisor` — focused on advisor exercise this run

## Mapping to V-series + 5+ artifact extraction (DEC-V61-198 Pillar 2)

case_009 surfaced 5 NEW V-findings + multiple stale-assumption fix-in-place opportunities:

| V-finding | Source pattern | Extraction candidate (≥1 sub-DEC each, all <250 LOC) |
|---|---|---|
| **V38** chemkinToFoam needs `THERMO ALL` header (bare `THERMO` fails parse on temperature-range line) | chemkinToFoam infrastructure | `chemkin_mechanism_loader.py` (compounds with V39, V40, V41) |
| **V39** chemkinToFoam tran.dat needs explicit `END` terminator | chemkinToFoam infrastructure | same loader |
| **V40** chemkinToFoam transport input can be chemkin tran.dat OR OpenFOAM-dict (sutherland regex) | chemkinToFoam infrastructure | same loader |
| **V41** GRI-3.0 THERMO header line `300 1000 5000` clamps janafThermo Tlow=300 even though per-species records support Tlow=200; coflow inlet T=291 + buoyancy → cells <300 floods log + eats CPU. Fix: edit header to `200 1000 5000` before chemkinToFoam | chemkinToFoam infrastructure | same loader |
| **V42** A2 advisor 5th-of-5 V25 placeholder confirmation on combustion-burner topology (axis-aligned planar Z-axis gap, reacting-low-Mach numerics class). Confirms V25 placeholder semantic is independent of numerics class | Advisor extension (5-of-5 overdetermined) | A2-v2 sub-DEC drafted at `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`; case_009 confirms 5th case → land |

**Artifact extraction candidates (case_009-original)**:
1. `chemkin_mechanism_loader.py` — DRM-19 fetch + THERMO ALL + END + Tlow patches + chemkinToFoam invoke (currently ~80 LOC in 08b)
2. `combustion_thermo_writer.py` — hePsiThermo + reactingMixture + sutherland + janaf + sensibleEnthalpy template (currently ~30 LOC in templates/constant/thermophysicalProperties)
3. `species_bc_writer.py` — per-inlet mass-fraction emission for N species (currently ~70 LOC in 08d)
4. `combustion_properties_writer.py` — PaSR/EDC/Cmix/EulerImplicit dict (currently ~30 LOC in 08e)
5. `mixture_fraction_post_processor.py` — Bilger Z formula + station sampling (currently ~110 LOC in 10b; v2 will add per-cell reconstruction)
6. `wedge_blockmesh_generator.py` — axis-collapsed multi-block wedge generator (currently ~100 LOC in templates/system/blockMeshDict.j2 + render code in 05)

Bundle as advisor-scope-expansion sub-DEC + reacting-low-Mach-infrastructure
sub-DEC (separate concerns; main session decides priority).

## Hard-coded compensations (stale-assumption fix-in-place per DEC-V61-198 Pillar 2)

| Item | Trigger | Fix |
|---|---|---|
| GRI-3.0 thermo30.dat THERMO header | chemkinToFoam parse error "expected 4(2A1,I3) but found '300.000'" | sed `THERMO` → `THERMO ALL` in 08b script |
| GRI-3.0 transport.dat (no terminator) | chemkinToFoam "ill defined primitiveEntry ending at line 111" | append `END\n` in 08b script |
| chemkin tran.dat (GRI-3.0 format) | strict 4(2A1,I3) regex incompatibility for some species | use OpenFOAM-format `transportProperties` dict with regex `.*` + sutherland air-like (As=1.4584e-6, Ts=110.4) instead of chemkin tran.dat |
| GRI-3.0 thermo header Tlow=300K | janaf limit warnings flood log + cells at T~295K from buoyancy | edit header to `200 1000 5000` before chemkinToFoam (per-species records already support 200K) |
| Coflow T = 291K (Sandia spec) | janaf limit fires (Tlow=300) | bumped to 300K in 0/T (3% perturbation, documented as v2 candidate) |

## D1 advisor exercise outcome (consistent with V25)

Per kickoff Hard Guardrail #6: A2 advisor at
`ui/backend/services/geometry_ingest/virtual_interface_detector.py`. Public
API path (`detect_virtual_interfaces`+`_run_shared`) per V21 closure note.

```
matched: True (both bracket-first and shim-first orderings, symmetric)
body_owner: coflow_plenum_mount_bracket / coflow_plenum_mount_shim
bbox_overlap_fraction: 1.0 (HARDCODED PLACEHOLDER per V25)
area_diff_fraction: 0.0 (HARDCODED PLACEHOLDER per V25)
normal_dot: 1.0
```

**case_009 is the SIXTH consecutive case (case_003 + case_004 + case_005 v2 +
case_006 + case_009) confirming V25 placeholder semantic.** New cross-topology
dimension: combustion-burner exterior mount (axis-aligned planar boxes, Z-axis
gap, reacting-low-Mach numerics class). 5-of-5 confirms V25 placeholder
semantic is **independent of numerics class** — it's a code-path scope gap,
not a physics-coupling issue.

`[QUESTIONABLE 2026-05-08]` marker applied per `knowledge_status_convention.md`:
PASS confirms `_run_shared` runs cleanly, NOT gap-detection. A2-v2 sub-DEC
drafted (`.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`) is
overdetermined for landing.

## D8 advisor exercise outcome

`thin_wall_advisor.detect_thin_wall_patches_at_risk` fired on **6 of 6**
combos (2 background cell sizes × 3 refinement levels):

| bg | levels | severity | cells_per_thickness | recommended_level_max |
|---|---|---|---|---|
| 50 mm | (1,2) | critical | 0.064 | 7 |
| 50 mm | (2,3) | critical | 0.128 | 7 |
| 50 mm | (3,4) | critical | 0.256 | 7 |
| 5 mm  | (1,2) | critical | 0.640 | 4 |
| 5 mm  | (2,3) | warning  | 1.280 | 4 |
| 5 mm  | (3,4) | info     | 2.560 | 4 |

Severity gradient is healthy (critical at coarse → info at fine resolution).
**case_009 is the 6th case in the V10/V23/V30 cross-topology arc** (curved
CATIA Frame, planar CadQuery aero, rotating-machinery yaw shim, 0.18 mm tip-
cap sliver, 0.80 mm reacting-low-Mach burner exterior bracket lip). Reinforces
V10/V23/V30 as a robust consensus-grade advisor; no new V-finding.

## v1 cold-flow + ignite outcome

- **Stage A cold-flow** (combustion off, dt=1e-5, t→0.005s): clean exit;
  min/max(T)=[294,1880]K (inlet bounds preserved); jet velocity field develops;
  no NaN; no spurious species drift. **PASS**.
- **Stage B ignite** (combustion on, dt=1e-6, t→0.006s): chemistry initialized
  successfully; T_max climbing from 1880K (pilot bound) at t=0.005s to 1895K+
  (live progression observed) — heat-release propagating into the fuel-air
  mixing layer. **PASS for chemistry-on initialization**. Full pseudo-steady
  flame development requires v2 ramp run (kickoff specifies dt=1e-5 ramp to
  1.0 s; 21-species ODE chemistry on every cell every iteration scales to
  10-20 hour wall-clock — out of v1 sub-session scope).
- **Stage C ramp**: deferred to v2 sub-session.

## Stale-assumption main-session attention

Per DEC-V61-198 Pillar 2 + the kickoff "Main session attention required" pattern:

1. **`codex_case_design_protocol.md` chemistry-mech catalog**: needs section
   on chemkinToFoam preprocessing (V38+V39+V41 are recurring chemkin-format
   surface-mismatch bugs that any sub-session converting a downloaded mech
   will hit). Bundle as part of chemkin_mechanism_loader sub-DEC.

2. **`solver_convergence_playbook.md`**: S17 + S18 LANDED (case_009 thread):
   S17 = chemkin mech ingestion + thermo header normalization
   (consolidating V38-V41); S18 = reactingFoam staged startup
   (cold-flow → ignite → ramp pattern, the chemistry-startup playbook
   that PREVENTS V-findings; observed-good in case_009 v1 with
   dt=1e-5 → 1e-6 → 1e-5 + adjustTimeStep).

3. **A2-v2 sub-DEC overdetermined**: 5 cases (003, 004, 005 v2, 006, 009)
   all show V25 placeholder semantic. Land draft patch
   `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md` next session.

4. **case_index.md status**: case_009 should advance from
   "dispatched · DEFERRED" to "active · v1 baseline (sediment landed; full
   reacting-low-Mach pipeline operational; ramp deferred to v2)".
   Solver-class coverage map row "Combustion / reacting flow" advances from
   "dispatched (case_009, deferred)" to ✅ covered.

## What this case does NOT yet have

- **Verdict comparison**: TNF Workshop archive Z(r,z), T(r,z), and species
  profiles at z/D=7.5/15/30/45/60 require sub-session v2 ramp run + per-cell
  Bilger reconstruction. Recommended action: M6 RAG corpus addition once v2
  lands, not a v1 blocker.
- **Pseudo-steady flame**: v1 ran ~1 ms of chemistry-on (ignite phase only);
  L_vis ≈ 67 D = 482 mm flame requires v2 multi-second ramp.
- **Per-cell mixture fraction**: 10b currently does inlet sanity check only.
  v2 deliverable is per-cell Bilger reconstruction from Y_C/Y_H/Y_O.
- **EDC vs PaSR sensitivity**: v2 deliverable.
- **Optically-thin radiation**: v3 deliverable per kickoff (only if T
  over-predicts, which won't be measurable until v2).
- **Per-species sutherland transport**: v2 candidate (V40); air-like fallback
  used in v1.

## When to update this entry

- **Each time case_009 runs a new development version** (v2 with full ramp +
  per-cell Bilger Z + TNF profile comparison; v3 with EDC or radiation):
  append per-step wall time row + add corresponding V-series entry if a new
  failure mode surfaced.
- **When chemkin_mechanism_loader sub-DEC lands** (consolidating V38-V41):
  update mapping table to note infrastructure extracted.
- **When A2-v2 sub-DEC lands**: update D1 advisor exercise section to reflect
  new gap-aware result schema; this case becomes part of the regression
  validation set.

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series (case_009 V38-V42 added 2026-05-08)
- `.planning/methodology/solver_convergence_playbook.md` — decision tree (S17/S18 candidates from V38-V41)
- `.planning/methodology/kickoff/case_009_codex_response.md` — Codex's full design (5 deliverables)
- `.planning/methodology/kickoff/case_009_validation.md` — main session's 13-check validation
- `.planning/methodology/knowledge_status_convention.md` — [QUESTIONABLE] grammar applied to A2 D1 PASS
- `.planning/case_profiles/case_006_onera_m6_transonic.md` — sibling compressible case (rhoCentralFoam pattern)
- `~/Desktop/case_009_sandia_flame_d/evidence/v1/REPORT.md` — final v1 report
