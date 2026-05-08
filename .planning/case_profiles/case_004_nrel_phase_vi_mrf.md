# case_004 · NREL Phase VI rotor + MRF (Industrial Reference)

> **NOT a gold-standard case.** No NASA Ames blade pressure parity is
> claimed in v1 — the engineering question is **harness ingestion +
> rotating_cellzone preservation + MRFProperties correctness**, not
> wind-tunnel validation. Defects on stationary nacelle hardware
> downstream of rotor disk preserve blade pressure-tap regions.
>
> Established 2026-05-08 by sub-session under DEC-V61-198 case-fleet
> protocol (queue dispatch from `case_proposal_queue.md`). First
> rotating-machinery case in the project — solver-class coverage map
> advances by one axis (incompressible-RANS-MRF root).
>
> **Sibling thread**: none (case_004b future = v2 AMI sliding-mesh if
> v1 force monitors stay oscillatory; case_004c future = high inflow
> sweep U_inf=15 m/s under stall regime).

## What this entry is

Tier-1 NREL/DOE public technical report (NREL/TP-500-29955) used as
the reference rotor geometry. CAD regenerated parametrically by
Codex's case-design protocol (cadquery + S809 64-pt + 26-station
chord/twist schedule + 180° rotation for second blade). 12-body
parts manifest with explicit `rotating_cellzone` cylindrical volume
for MRF.

## What this entry is for

Three orthogonal uses:

1. **Solver-class coverage**: First incompressible-RANS-MRF case in
   the fleet. Pattern 6 root — no inheritance from case_002a/b
   (compressible-buoyant) nor case_003 (external incompressible-RANS).
   Future rotating-machinery cases (compressors, fans, mixers)
   inherit V22-V24 from this case.

2. **A2 + thin_wall_advisor field-validation source**: 3rd cross-topology
   industrial validation of both advisors. Compounded with case_002a/b
   + case_003, the cross-topology consistency now spans 3 distinct
   topologies for both advisors:
   - thin_wall_advisor: curved CATIA Frame + planar CadQuery aero plate +
     planar rotating-machinery aux instrumentation. **No scope gap.**
   - A2 `_run_shared`: curved CATIA non-manifold + planar CadQuery
     Z-axis gap + planar CadQuery Y-axis gap. **Scope gap is
     curved-geometry-specific** (case_005 V19 FAIL on flange ring),
     refined by V22.

3. **MRF infrastructure proof artifact**: case-local MRFProperties.j2
   + 08b_write_mrf.py + 07b_audit_mrf.py demonstrate the canonical
   rotating-machinery flow. Main project has no equivalent — these
   are extraction candidates after 1-2 more rotating cases share the
   pattern.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_004_nrel_phase_vi_mrf/` |
| Top-level overview | `~/Desktop/case_004_nrel_phase_vi_mrf/README.md` |
| v1 pause report | `~/Desktop/case_004_nrel_phase_vi_mrf/evidence/v1_<ts>/REPORT.md` |
| SSOT YAML | `~/Desktop/case_004_nrel_phase_vi_mrf/config/case.yaml` |
| Defect verification | `~/Desktop/case_004_nrel_phase_vi_mrf/evidence/v1_<ts>/defect_verification.json` |
| CAD generation script | `~/Desktop/case_004_nrel_phase_vi_mrf/scripts/build_cad.py` (Codex deliverable 2) |
| Parts manifest | `~/Desktop/case_004_nrel_phase_vi_mrf/inputs/parts_manifest.yaml` (Codex deliverable 4) |
| Defect manifest | `~/Desktop/case_004_nrel_phase_vi_mrf/inputs/defect_manifest.yaml` (Codex deliverable 5) |
| MRF infrastructure (NEW) | `templates/constant/MRFProperties.j2` + `scripts/08b_write_mrf.py` + `scripts/07b_audit_mrf.py` |

## Solver-class capability axis

| axis | value |
|---|---|
| solver_class | rotating machinery (MRF / sliding mesh) |
| numerics_class | incompressible-RANS-MRF |
| pattern_6_inheritance | NONE (root); no V-finding inheritance from case_002a/b nor case_003 |
| solver_v1 | simpleFoam + MRF (steady, frozen-rotor) |
| solver_v2_fallback | pimpleFoam + AMI sliding mesh (only if v1 force monitors stay oscillatory) |
| turbulence | kOmegaSST |
| fluid | air, ν = 1.5e-5 m²/s, ρ_ref = 1.225 kg/m³ |
| omega | 7.539822369 rad/s = 72 rpm |
| rotation_axis | (1, 0, 0) (rotor disk in YZ plane, axis along x) |
| inflow | U_inf baseline 7 m/s; sweep [7, 10, 15] m/s |
| Re | ≈ 0.9 - 1.1e6 at 80% span |
| Mach | < 0.13 (incompressible valid) |

## Per-step wall time (v1 sub-session, executed portion only)

Measured 2026-05-08 on macOS Apple Silicon.

| Step | Script | Wall time | Output |
|---|---|---|---|
| build_cad | `scripts/build_cad.py` | ~30 s | 1.96 MB STEP, 7.89 MB Tier-1 PDF cache |
| _freecad_extract | `scripts/_freecad_extract.py` (via FreeCADCmd) | ~15 s | 265 KB JSON with 40 bodies (12 expected + 8 fragments + 21 datum frames + 1 parent assembly) |
| 02_verify_defects | `scripts/02_verify_defects.py` | <2 s | defect_verification.json with A2 + thin_wall results + V-finding candidates |
| 08b_write_mrf | `scripts/08b_write_mrf.py` | <1 s | constant/MRFProperties (1 zone, axis=(1,0,0), omega=7.539822369) |

**Total v1-executed pipeline wall time**: ~50 s.

**Pending v2 sub-session steps** (deferred):
- 01_extract_stl (cadquery STEP → multi-solid STL); est. 1 min
- 04_scaffold_case + 05_make_dicts (Jinja2 → OpenFOAM dicts); est. <30 s
- 06_run_mesh (Docker blockMesh + sHM with cellZone extraction); est. 5-10 min
- 07_check_mesh + 07b_audit_mrf (post-mesh advisor); est. <5 s
- 08_write_bcs (`0.orig/`); est. <5 s
- 09_run_solver (Docker simpleFoam 500 iter with forceCoeffs); est. 7-15 min single-core
- 10_post (slices + thrust/torque coeffs); est. 30 s
- 11_audit (signed evidence pack); est. <5 s

**Estimated total v2 wall time**: 15-30 min for first end-to-end run.

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (the V-series source material):
- Codex's `scripts/build_cad.py` parametric blade (S809 + 26-station schedule)
- `scripts/_freecad_extract.py` STEP → JSON face/bbox extractor (Phase 1, FreeCADCmd)
- `scripts/02_verify_defects.py` defect ground-truth + advisor invocation (Phase 2, case venv)
- `templates/constant/MRFProperties.j2` (NEW — main project has no MRFProperties writer)
- `scripts/08b_write_mrf.py` (NEW — manifest → MRFProperties)
- `scripts/07b_audit_mrf.py` (NEW — post-mesh cellZone + rotating-wall + omega audit)
- `config/case.yaml` SSOT with `mrf:` block (NEW schema axis)

**Reused from main project** via `PYTHONPATH`:
- `ui.backend.services.geometry_ingest.virtual_interface_detector` (A2 advisor) — invoked
  via public `detect_virtual_interfaces` API on (nacelle_body, nacelle_service_cover) pair
- `ui.backend.services.geometry_ingest.thin_wall_advisor` (thin_wall) — invoked at 3
  refinement-level scenarios

**Pending reuse for v2** (case-local first, extraction TBD):
- main project STL loader / patch detector / case scaffolder / BC writer
  (apu-bay reuse pattern; case-local until v2 sub-session run)

## Mapping to V-series and 5-artifact extraction

| Hand-coded item | V-series | Artifact extraction (DEC-V61-198) |
|---|---|---|
| MRFProperties.j2 + 08b_write_mrf.py | (new infrastructure) | candidate A6 (after 1-2 more rotating-machinery cases) `case_solve/mrf_writer.py` |
| 07b_audit_mrf.py | (new infrastructure) | candidate A7 (after 1-2 more) `mesh_quality/mrf_audit.py` |
| FreeCAD body-datum-frame filtering | V24 | extends A1 (`cad_ingest_freecad.py`) sentinel-bbox + datum-frame post-filter |
| Compound fragmentation handling | V24 (compounds V16) | extends A1 with parent-compound-vs-fragment detection |

## V-series sourced

| ID | Status | Topic |
|---|---|---|
| V2 (upgrade) | closed · field-validated (3rd PASS) | A2 cross-topology consistency: now includes case_004 Y-axis axis-aligned planar |
| V10 (upgrade) | closed · field-validated (3-case consistency) | thin_wall_advisor cross-topology consistency: case_002a + case_003 + case_004 all flag at consistent severity progression |
| V22 | closed · field-validated | A2 advisor field-validation on rotating-machinery topology (case_004); 3rd PASS refines V21 hypothesis toward case_005-failure-is-curved-geometry-specific |
| V23 | closed · field-validated | thin_wall_advisor field-validation on rotating-machinery aux hardware (case_004); cleanest A1-A5 sediment piece — no scope gap surfaces |
| V24 | partial | V16 fragmentation reproduction in case_004 + new finding: FreeCAD body-construction frames preserved through STEP with sentinel-bbox ≈ 1e92 mm |

## Playbook entries sourced

(none from v1; v2 sub-session may add S15+ for MRF-specific patterns
when force monitors are observed)

## Rotating-machinery-specific potential failure modes (for v2 sub-session)

Per kickoff brief and Codex hypothesis, expect to surface (or rule
out) the following on v2 mesh + solver run:
- `rotating_cellzone` name mismatch in MRFProperties → false stationary run with near-zero torque
- Rotating zone too short axially (1.8 m vs blade chord 0.355-0.737 m) → blade leading/trailing edges leak outside rotating source region
- ω sign or axis error → reverses torque sign while residuals look healthy
- Steady MRF inadequate for tower/nacelle interaction → force monitor oscillation (v2 AMI trigger)
- Tunnel-wall blockage (1.25 D half-width per N3 of validation) → may need 5-10 D expansion
- y+ regime (tip speed 37.9 m/s, no prism layers in v1) → wall function range check

## What this case does NOT yet have

- **Mesh generation**: v2 scope; sHM template with cellZone extraction is
  still TBD
- **Solver run**: v2 scope; forceCoeffs FO + 500-iter simpleFoam not yet
  exercised
- **Verdict comparison**: NREL Phase VI has wind-tunnel data (3,4,5,6 m
  blade pressure-tap stations) BUT v1 defect injection on stationary
  nacelle precludes strict parity claim; v2-v3 may target qualitative
  thrust/torque sweep behavior instead
- **AMI sliding mesh fallback**: v2 path; manifest declares
  `future_sliding_mesh_interface_names_if_v2: [rotor_ami_inner, stator_ami_outer]`
  but v1 does not need them
- **PDF parsing of NREL/TP-500-29955**: cached at
  `inputs/cache/tier1_nrel_phase_vi_nrel_tp_500_29955.pdf` (7.89 MB)
  but contents not parsed; v3 sub-session may extract per-station Cp
  comparison data if needed

## Main session attention required (post-v1 pause)

Items the v1 sub-session surfaced that warrant main-session decision:

1. **V21 hypothesis refinement**: V21 was "open" with case_003 PASS vs
   case_005 V19 FAIL on D1-class. case_004 v22 adds 3rd PASS in axis-aligned
   planar regime. Three-case evidence now suggests **case_005 V19 FAIL is
   curved-geometry-specific** (flange ring), not all D1-class. Propose:
   refactor V21 entry to mark case_003+case_004 path correct; mark
   case_005 as "curved-geometry scope gap" with `_run_shared_curved`
   sub-DEC under advisor-scope-expansion arc.

2. **V16/V24 Codex CAD pattern revision**: 2 cases now confirm
   `cq.Compound.makeCompound([Solid_a, Solid_b])` produces fragmented
   output. Recommend `codex_case_design_protocol.md` revision: prefer
   `cq.Solid.fuse([...])` (boolean fuse) for "one logical body" or
   keep separate names for "actually distinct patches". Datum-frame
   sentinel-bbox finding (V24) extends A1 extraction scope.

3. **MRF infrastructure extraction priority**: case_004 provides
   first reference point for `mrf_properties_writer.py` (08b) +
   `mrf_audit.py` (07b). After 1-2 more rotating cases share the
   pattern (e.g., a fan or compressor case), extract under
   DEC-V61-198 sub-DEC scope.

## When to update this entry

- **Each time `~/Desktop/case_004_nrel_phase_vi_mrf/` runs a new
  development version** (v2 mesh, v3 solver, v4 sweep): append to
  per-step wall time table and add corresponding V-series entry if
  a new failure mode surfaced
- **When a rotating-machinery sibling case is added** (case_004b AMI,
  or case_NNN compressor/fan): cross-reference here and inherit
  V22-V24 unless the new case's geometry is curved-flange-class
  (then extra V-finding likely)
- **When MRF infrastructure (A6/A7) lands in main project**: update
  the mapping table to note "extracted, see `<path-to-extracted-module>`"

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision; case-fleet protocol)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series (V2/V10 upgraded; V22/V23/V24 added)
- `.planning/methodology/solver_convergence_playbook.md` — decision tree (no S-additions from v1; v2 may add)
- `.planning/methodology/kickoff/case_004_nrel_phase_vi_mrf.md` — sub-session kickoff
- `.planning/methodology/kickoff/case_004_codex_response.md` — Codex case-design output (5 deliverables)
- `.planning/methodology/kickoff/case_004_validation.md` — main-session 6-check validation report
- `.planning/case_index.md` — multi-case tracker (case_004 row updated to active · v1 paused)
- `.planning/case_proposal_queue.md` — dispatch queue (case_004 row updated to IN-FLIGHT v1 PAUSED)
- `.planning/cross_cuts/v_series_2026-05-08.md` — V-series snapshot (compounded-evidence rows updated)
