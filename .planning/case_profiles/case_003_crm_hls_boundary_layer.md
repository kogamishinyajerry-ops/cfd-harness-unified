# Case 003 · CRM-HLS External High-Re Boundary Layer (Industrial Reference)

> **NOT a gold-standard case.** No verdict-pass criterion against HLPW6
> wind-tunnel data; reference data is partial (auxiliary defect bodies
> not in original measurement zones). This is an **industrial reference**
> — proof artifact, V-series finding source, advisor field-validator.
>
> Established by DEC-V61-198 (APU bay strategic pivot, 2026-05-07);
> first 003-series sub-session executed 2026-05-08. **Status: v1 paused
> at advisor field-validation; CFD pipeline deferred pending V20 unit-scale
> resolution.**

## What this entry is

A pointer to the industrial sandbox at
`~/Desktop/case_003_crm_hls_boundary_layer/`, dispatched per
`case_proposal_queue.md` to fill the **external high-Re + boundary
layer / incompressible-RANS** coverage row. The case-thread executed
its v1 milestone (CAD generation + defect verification + advisor
field-validation) and paused before CFD pipeline.

## What this case validated

**First industrial cross-topology field-validation for two landed
advisors:**

1. **A2 (`virtual_interface_detector`)** — landed 2026-05-08 commit
   `a09ae0a`. case_003 D1 (0.35 mm Z-axis gap between two CadQuery
   planar boxes) detected with `bbox_overlap_fraction=1.0`,
   `area_diff_fraction=0.0`, `normal_dot=1.0`, matched face area
   3.48e+07 mm². Confirms `_run_shared` design holds on planar geometry
   (case_002a was curved-CATIA topology; case_003 closes the second
   geometry class).
2. **`thin_wall_advisor`** — landed 2026-05-07. case_003 D8 (0.80 mm
   thin plate, 27 m × 3.4 m × 0.80 mm) flagged severity=`critical` with
   `cells_per_thickness=0.013`. Confirms bbox-min thinness estimator
   generalizes from APU bay curved Frame patches to planar plate
   geometry.

These are status upgrades for V2 (advisor → field-validated) and V10
(advisor → cross-topology consistent) in
`industrial_case_solver_findings.md`.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_003_crm_hls_boundary_layer/` |
| Top-level overview | `~/Desktop/case_003_crm_hls_boundary_layer/README.md` |
| v1 report | `~/Desktop/case_003_crm_hls_boundary_layer/evidence/v1_20260508T010754_advisor_validation/REPORT.md` |
| Codex brief | `cfd-harness-unified/.planning/methodology/kickoff/case_003_codex_response.md` |
| Codex validation | `kickoff/case_003_validation.md` |
| Sub-session kickoff | `kickoff/case_003_crm_hls_boundary_layer.md` |
| Tier-1 source | https://aiaa-hlpw.org/assets/HLPW6/CRM_HLS_HLPW6_TC1.stp (sha256 `0055d0f8…aa596f`, pinned 2026-05-08) |
| 5-deliverable Codex output | `inputs/cache/`, `inputs/cad_codex_v1.step`, `inputs/parts_manifest.yaml`, `inputs/defect_manifest.yaml`, `scripts/build_cad.py` |

## Solver-class capability axis

| field | value |
|---|---|
| Coverage row | External high-Re + boundary layer |
| Numerics class (Pattern 6 root) | `incompressible-RANS` |
| Inheritance from prior cases | **none** — case_002a/b are compressible-buoyant-RANS; case_003 is the first incompressible-RANS root in the project's V-series ledger |
| Solver target v1 | `simpleFoam` (deferred; not yet executed) |
| Solver fallback v2 | `pimpleFoam` if force monitors oscillate (deferred) |
| Turbulence model v1 | kOmegaSST (per kickoff) |
| Freestream | air @ 288 K, ν=1.5e-5 m²/s, U_inf=55 m/s, α=8°, M≈0.16, Re≈3.7e6/m |

## Per-step wall time (v1 milestone only)

Measured 2026-05-08 on macOS Apple Silicon, in-place case-local venv
(no Docker invoked at v1):

| Step | Script | Wall time | Output |
|---|---|---|---|
| Bootstrap | manual | < 1 min | sandbox tree |
| Codex deliverables → sandbox | manual | < 1 min | parts_manifest.yaml + defect_manifest.yaml + build_cad.py |
| venv setup | `python3 -m venv .venv && pip install` | ~ 90 s | cadquery 2.7.0 + numpy + pyyaml + jinja2 + trimesh |
| 01 build_cad.py (download + assemble) | `python scripts/build_cad.py` | ~ 30 s | inputs/cad_codex_v1.step (1.96 MB), 10 named bodies |
| 02 face extraction | `freecadcmd scripts/_extract_faces_freecad.py` | ~ 4 s | inputs/face_geometry.json (91 faces) |
| 02 verify_defects.py | `python scripts/02_verify_defects.py` | < 1 s | evidence/v1_…/advisor_field_validation.json |
| **Total v1 milestone** | | **~ 3 min** | (excluding initial pip download) |

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (the V-series source material at
v1):
- HLPW6 STEP download + canonicalization (Codex-generated `build_cad.py`)
- D1 + D8 defect injection at absolute mm into a Tier-1 source at
  unknown unit (V20 candidate)
- FreeCAD face-geometry bridge (`_extract_faces_freecad.py`) — this
  exists because case-local advisor validation needed face data; once
  A1 lands in main project, this kind of bridge can be promoted

**Reused from main project** via `sys.path.insert`:
- `ui.backend.services.geometry_ingest.virtual_interface_detector`
  (`detect_virtual_interfaces`, `BodyGeometry`, `FaceGeometry`,
  `InterfaceSpec`)
- `ui.backend.services.geometry_ingest.thin_wall_advisor`
  (`detect_thin_wall_patches_at_risk`, `PatchGeometry`)

## Mapping to V-series

| Case_003 work | V-series finding | Status |
|---|---|---|
| A2 successful match on D1 planar-box Z-axis gap | V2 | **status upgraded** to "field-validated, cross-topology" 2026-05-08 |
| thin_wall_advisor severity=critical on D8 0.80 mm plate | V10 | **status upgraded** to "field-validated, cross-topology (curved + planar)" 2026-05-08 |
| HLPW6 airframe loaded at 91 m semi-span ≈ 25.4× over expected | V20 (NEW) | open — main-session attention required |
| A2 case_003 PASS contradicts case_005 V19 FAIL | V21 (NEW) | open — main-session cross-case investigation |

## What's deferred (vs original Codex brief 5-8h estimate)

The CFD pipeline (sHM mesh, simpleFoam baseline, sectional Cp + y+
histogram + force coefficients + wake viz) is **paused** pending V20
resolution. Loaded geometry has airframe semi-span ≈ 91 m, ~25.4× the
real CRM-HLS half-span (≈ 30 m), strongly suggesting source STEP unit
is INCH treated as MM somewhere in the cadquery / FreeCAD chain.

Without unit rationalization, sHM on the as-loaded geometry would
either produce ≈ 10⁹ cells (at sane mm-scale background sizing) or
under-resolve the airframe to < 1 cell per chord (at coarse bg
sizing). Either path produces non-physical CFD; running it would not
strengthen the advisor field-validation outcomes (which are
unit-independent) and would burn sub-session compute.

## When to update this entry

- **When v2 runs** (after V20 unit-scale resolution): append v2 wall
  time, update solver convergence trail, add new V-series rows for any
  CFD-side death modes
- **When V20 resolution lands** as sub-DEC: cross-link in this profile
- **When V21 cross-case investigation completes**: update V21 status
  reference here; if V19 turns out to be mis-diagnosed, this profile's
  V21 cross-link will be the canonical "case_003 confirmed PASS"
  evidence
- **When A1 (`cad_ingest_freecad.py`) extraction lands** in main
  project: replace `_extract_faces_freecad.py` mention with reference
  to extracted module

## What this case does NOT yet have (and may never)

- **Verdict comparison vs HLPW6 wind-tunnel data**: deferred indefinitely.
  Codex's defect manifest already documented `reference_data_validity:
  partial` because auxiliary fixtures add wetted area outside published
  measurement zones. Even after CFD runs, integrated Cl/Cd will not be
  comparable to HLPW6 reference (sectional Cp on wing/slat/flap might be,
  if scale-resolved)
- **Multiple components per patch**: per kickoff N1, Codex's
  `import_reference_shape()` flattens the imported CRM-HLS multi-solid
  STEP into one `airframe_reference` body. v2 may split if
  per-component force breakdown is needed; v1 was acceptable given the
  paused state

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series
  (V2, V10 status upgrades; V20, V21 new rows)
- `.planning/methodology/solver_convergence_playbook.md` — decision tree
  (no S-series additions from v1; CFD-side V/S findings deferred to v2)
- `.planning/methodology/kickoff/case_003_*.md` — original briefing chain
- Sister industrial case (compounded V20 evidence): `case_002a_apu_bay_buoyant_simple.md`
- Sister industrial case (V21 cross-case partner): `case_005_rae_m2129_sduct.md`
