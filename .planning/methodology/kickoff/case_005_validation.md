# case_005 · Codex Output Validation Report

> **Round 1** · 2026-05-07 evening / 2026-05-08 — main session
>
> **Verdict: PASS WITH NOTES** — no revision request. Sub-session
> dispatches with documented caveats.
>
> **Notable**: case_005 is the **first case to exercise a LANDED
> advisor** (D2 → `geometry_surgery.decimate_to_tier`). Prior cases
> (003/004) all surface A2-pending. Net signal value HIGH.

## Codex output overview

- **Case ID**: `case_005_rae_m2129_sduct`
- **Component**: RAE M2129 circular S-duct intake diffuser, full
  360° internal flow path with outlet plenum and explicit AIP
  post-processing plane
- **Source tier**: Tier-1 (T1.I1, NASA Glenn `WWW/wind/valid`
  validation archive — AGARD AR-303 / AR-270 reference)
- **Source URLs**:
  - `https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.html`
  - Tarball: `https://www.grc.nasa.gov/WWW/wind/valid/sduct/sduct02/sduct02.tar.gz`
  - Tutorial: `https://www.grc.nasa.gov/WWW/wind/valid/M2129tutorial/tutorial.html`
  - NTRS reference: `https://ntrs.nasa.gov/citations/20040021333`
- **CAD tool**: CadQuery (parametric S-duct centerline + radius
  profile, AIP cutting-plane marker, defect bodies, canonicalized
  STEP header)
- **Defects**: D1 (0.35 mm gap on external inlet flange) + D2
  (102,400-triangle over-dense throat-wall overlay)
- **Solver**: rhoSimpleFoam (steady compressible), kOmegaSST,
  perfectGas + Sutherland-equivalent (Cp=1004.5, μ=1.79e-5),
  p_total_inlet=101325 Pa, T_total_inlet=288 K, p_back=85000 Pa
  (PR=0.839), AIP Mach target 0.40-0.60, throat Mach target
  0.70-0.78 (subsonic-transonic, **NO strong shocks**)
- **Estimated effort**: 5-8 hours, ~3 versions

## Six-check (extended) validation results

### Check 1 · CadQuery script syntax-clean

✅ **PASS** — `python3 -m py_compile /tmp/case_005_build_cad.py`
returns clean. 425 LOC.

### Check 2 · cadquery installable

⚠️ **NOTE** — same as case_003/004: not in main project venv.
Sub-session sandbox installs locally:

```bash
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
```

### Check 3 · Tier-1 source reachable

⚠️ **NOTE** — All four `grc.nasa.gov` URLs return **HTTP 500
Internal Server Error** at validation time:

```
HTTP/1.1 500 Internal Server Error
content-type: text/html
```

Likely transient NASA Glenn web-archive issue (these archives
have intermittent uptime; `WWW/wind/valid/` has been a stable
public reference for 20+ years). Codex's URL form is canonical;
NTRS reference (citations/20040021333) is the durable source of
truth and uses a separate NASA system.

**Sub-session impact**: minimal. CAD generation is **fully
parametric** (analytic centerline + radius profile from published
M2129 station tables baked into script constants). The script
does NOT actually fetch the source tarball — it only references
URLs in metadata. Sub-session can:
1. Proceed without fetching anything (script generates STEP from
   constants alone)
2. Manually retrieve the tarball or NTRS report later for
   reference checking

### Check 4 · Patch names match OpenFOAM regex

✅ **PASS** — All 9 named bodies + 1 cutting plane match
`^[A-Za-z][A-Za-z0-9_]*$`:
- `stationary_domain`, `duct_wall_reference`, `inlet`, `outlet`,
  `aip_plane_marker`, `inlet_flange_ring`, `inlet_flange_cover`,
  `throat_liner_overdense`
- Cutting plane: `AIP` (uppercase OK — regex permits
  `^[A-Za-z][A-Za-z0-9_]*$` and `AIP` is all letters)

No duplicates. `patch_naming_check` block in manifest validates
the regex contract.

**Convention note**: uppercase `AIP` is unusual in OpenFOAM (lowercase
preferred), but it's the engineering convention for "Aerodynamic
Interface Plane" in turbomachinery/intake CFD. Acceptable.

### Check 5 · Compressible inlet BC role explicit

✅ **PASS** — `inlet` declared with `role:
compressible_total_pressure_inlet`, `bc.p: totalPressure`,
`bc.T: totalTemperature`, `bc.U: pressureInletOutletVelocity`.
Reference values `p_total_inlet_pa: 101325.0` and
`T_total_inlet_k: 288.0` explicit.

### Check 6 · Compressible outlet BC role explicit

✅ **PASS** — `outlet` declared with `role:
compressible_wave_transmissive_outlet`, `bc.p: waveTransmissive`,
`bc.T: inletOutlet`. Fallback `fixedValue p` documented for cases
where waveTransmissive is unstable. `p_back_pa: 85000.0` explicit.

### Check 7 · AIP plane declared

✅ **PASS** — declared TWO ways:
- `cutting_planes:` block with `name: AIP`, `role: aip_plane`,
  origin (489.458, 0.0, 137.16) mm, normal (1,0,0), radius 76.2 mm
- `aip_plane_marker` patch as physical exterior annular marker
  (separate from cutting plane to avoid blocking flow volume)

DC60 distortion coefficient definition explicit:
`(areaAvg_p0_AIP - worst_60deg_sector_avg_p0) / areaAvg_dynamic_pressure_AIP`

### Check 8 · T BC declared on each patch

✅ **PASS** — every wall and BC patch has explicit T BC:
- Walls: `T: zeroGradient` (adiabatic)
- Inlet: `T: totalTemperature`
- Outlet: `T: inletOutlet`
- Plus `mut: mutkWallFunction` and `alphat:
  compressible::alphatWallFunction` for compressible turbulence
  treatment

### Check 9 · Reference total p + total T specified

✅ **PASS** — `reference_conditions:` block:
- `p_total_inlet_pa: 101325.0`
- `T_total_inlet_k: 288.0`
- `p_back_pa: 85000.0`
- `pressure_ratio_p_back_over_p0: 0.839`
- `target_throat_mach: "0.70 to 0.78"`
- `target_aip_mach: "0.40 to 0.60"`
- `strong_shock_limit_mach: 1.3` (case_005 ceiling — case_006
  territory above)

Plus `thermophysics:` block with γ=1.4, R=287.05, Cp=1004.5,
Pr=0.72, μ_ref=1.79e-5, T_ref=288 K, kOmegaSST.

### Check 10 · Defects measurable

✅ **PASS** — both defects programmatically injected with
deterministic constants:
- D1 (0.35 mm gap): `DEFECT_GAP_MM = 0.35` constant; gap created
  by box translation
- D2 (over-dense triangulation): `expected_face_count: 102400`
  (Codex generates the throat-liner overlay with explicit
  high-density triangulation, e.g., 320×320 face subdivision on a
  cylindrical sleeve segment)

FreeCAD verification commands provided in defect manifest for both.

### Check 11 · AIP and centerline defect-free

✅ **PASS** — explicit `protected_reference_zones:` block:
- `centerline_pressure_line`: "No defect body intersects the duct
  centerline y=0, z=centerline_z(x)."
- `AIP`: x_mm=489.458, "No defect body lies within the AIP
  measurement disk or within ±5 mm of the AIP station."

D1 location: external inlet flange, x≈-90 mm (upstream of throat,
nowhere near AIP at x=489 mm). D2 location: x=8-42 mm at radius
64.4 mm (near throat wall, NOT on centerline, NOT at AIP). ✓

### Check 12 · Defect ↔ advisor mapping

**D1 (sub-mm gap)**: ✅ **PASS** — `expected_advisor_to_catch:
virtual_interface_detector` references **A2 LANDED 2026-05-08**
(commit `a09ae0a`). The advisor lives at
`ui/backend/services/geometry_ingest/virtual_interface_detector.py`
with 11 tests green.

**Backfill note**: this row originally read
`virtual_interface_detector_pending_A2`; backfilled to the landed
advisor name as part of harvest 001 directive after compounded
evidence (8-of-8 across cases 003-010) triggered Pillar 2
extraction.

**D2 (over-dense triangulation)**: ✅ **PASS — first case to
exercise a LANDED advisor**.

`expected_advisor_to_catch: geometry_surgery.decimate_to_tier`.
This advisor IS landed at
`ui/backend/services/geometry_ingest/geometry_surgery.py`
(extracted as A3 in 2026-05-07 morning batch).

Sub-session imports it and exercises decimation against a
**102,400-triangle overlay** — that's an industrial-flavored
over-dense input, NOT a toy fixture. This will be the first real
falsification of A3 against case-thread CAD. If A3 fails to
produce a reasonable decimated mesh OR fails to flag the overlay
as redundant, that's a real V-finding pointing to "A3 advisor
toy-case bias" — exactly the Pillar 2 stale-assumption fix
pattern.

**This is the highest signal-to-noise check in the case_005
roster.**

### Check 13 · Brief targets compressible-RANS + Mach ceiling

✅ **PASS** — Brief explicitly states:
- numerics class: `compressible_RANS_internal_diffuser`
- Solver v1: `rhoSimpleFoam`
- Solver v2: `rhoPimpleFoam` only if force monitor or residual
  oscillation
- Throat Mach target 0.70-0.78 (subsonic-transonic transition
  with weak normal shock acceptable)
- AIP Mach target 0.40-0.60
- Strong shock limit M=1.3 — case_006 ceiling, NOT case_005
- DC60 + recovery PR + AIP Mach map + centerline static p as
  metrics

Codex correctly avoided pushing into case_006 territory
(rhoCentralFoam / strong shock / density-based numerics).

## Additional notes (non-blocking)

### N1 · First compressible BC-writer infrastructure

The harness has NO prior compressible BC writer. case_005 forces
new infrastructure:
- `totalPressure` writer (with `p0` reference)
- `totalTemperature` writer (with `T0` reference)
- `waveTransmissive` writer (with `psi`, `fieldInf`, `lInf`,
  `gamma` parameters)
- `inletOutlet` for T at compressible outlet
- `mutkWallFunction` / `compressible::alphatWallFunction` for
  compressible wall treatment

Sub-session hand-crafts these case-locally first. Most likely
artifact extraction candidates (each <250 LOC): a
`compressible_bc_writer.py` and a `compressible_thermophysical_writer.py`
in `ui/backend/services/case_bc/`. After case_006 (also
compressible), priority for promotion to shared service rises.

### N2 · DC60 post-processor brand new

DC60 distortion coefficient at AIP is the engineering metric.
Definition is well-known but no current OpenFOAM utility computes
it directly. Sub-session writes `10b_compute_dc60.py` consuming
ParaView slice data at AIP. Strong artifact extraction candidate
for M5 (post-processing milestone).

### N3 · Throat over-dense overlay generation strategy

Codex's CadQuery script generates the 102,400-triangle overlay
via "many small box subtractions" or "high-resolution
revolution" — exact mechanism is in script lines that produce
`build_throat_liner_overdense()`. Sub-session should verify the
face count actually lands at the claimed 102,400 (FreeCAD
`len(Shape.Faces)`). If mismatch, flag as defect-injection-precision
V-finding.

### N4 · NTRS as durable URL fallback

If NASA Glenn `WWW/wind/valid` archive stays down, NTRS
`citations/20040021333` (USGA SST Sym­ Inlet Distortion paper, AIAA
2004-something) is the long-term reference. Sub-session can use
NTRS-hosted PDFs for measurement plane data if needed. CAD
geometry baked into the script does not require live URLs.

## Rounds budget

Round 1 of 2 used. **No revision request issued** — all three
A2-pending findings are documented as Pillar 2 force-extraction
signals; URL HTTP 500 is environmental and non-fatal; first-case-
exercising-landed-advisor (D2 → A3) is a feature, not a bug.

If sub-session reports unrecoverable issues (e.g., over-dense
overlay generation fails, AIP cutting-plane marker collides with
flow volume after meshing, totalPressure inlet diverges), main
session may invoke round 2.

## Approval to write kickoff

✅ proceed to format `kickoff/case_005_rae_m2129_sduct.md`
combining `case_kickoff_prompt_template.md` + Codex deliverables.

## Files

- `kickoff/case_005_codex_request.md` — what we sent
- `kickoff/case_005_codex_response.md` — Codex's full response
  (saved verbatim from `/tmp/codex_005_final.txt`)
- `kickoff/case_005_validation.md` — this file
- `kickoff/case_005_rae_m2129_sduct.md` — sub-session kickoff
  (to be written next)
